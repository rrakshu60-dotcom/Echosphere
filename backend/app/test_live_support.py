"""Unit tests for the live-test helper (backend/scripts/live_support.py), using a fake serial port and backend."""
import time

import pytest

from scripts.live_support import Esp32Serial, LiveNotices, wait_until


class FakePort:
    """Stands in for serial.Serial: hands out queued lines, then times out like a real port."""

    def __init__(self, lines, delay=0.0):
        self._lines = list(lines)
        self._delay = delay
        self.closed = False

    def readline(self):
        if self._delay:
            time.sleep(self._delay)
        if self._lines:
            return self._lines.pop(0)
        time.sleep(0.01)
        return b""

    def close(self):
        self.closed = True


def test_wait_until_returns_value_and_elapsed():
    calls = iter([None, None, {"status": "Playing"}])
    value, elapsed = wait_until(lambda: next(calls), timeout=2, interval=0.01, what="queue item playing")
    assert value == {"status": "Playing"}
    assert 0 <= elapsed < 2


def test_wait_until_fails_with_what_it_waited_for():
    with pytest.raises(AssertionError, match="queue item playing.*0.2s"):
        wait_until(lambda: None, timeout=0.2, interval=0.01, what="queue item playing")


def test_serial_matches_lines_after_the_mark_only():
    port = FakePort(
        [
            "✅ [I2S STREAM] Notice speech playback completed successfully!\r\n".encode(),
            b"",
            "⚡ [PUSH] Play command received for notice #42\r\n".encode(),
        ],
        delay=0.05,
    )
    with Esp32Serial(port_factory=lambda: port) as esp:
        time.sleep(0.08)  # the first (old) line arrives before the mark
        mark = esp.mark()
        line, elapsed = esp.wait_for(r"Play command received for notice #42", timeout=2, since=mark)
        assert "#42" in line
        assert elapsed >= 0
        with pytest.raises(AssertionError, match="playback completed"):
            esp.wait_for(r"playback completed", timeout=0.3, since=mark)
    assert port.closed


def test_serial_timeout_message_shows_recent_lines():
    port = FakePort([b"[WIFI] Connected!\r\n"])
    with Esp32Serial(port_factory=lambda: port) as esp:
        with pytest.raises(AssertionError) as exc:
            esp.wait_for(r"EMERGENCY", timeout=0.3)
    assert "[WIFI] Connected!" in str(exc.value)


def test_serial_skips_undecodable_bytes():
    port = FakePort([b"\xff\xfe garbage \x80 [PUSH] Connected\r\n"])
    with Esp32Serial(port_factory=lambda: port) as esp:
        line, _ = esp.wait_for(r"\[PUSH\] Connected", timeout=1)
    assert "[PUSH] Connected" in line


class FakeBackend:
    """Minimal stand-in for LiveSession: records created notices and answers list/delete."""

    def __init__(self, keep_after_delete=False):
        self.notices = {}
        self.next_id = 900
        self.keep_after_delete = keep_after_delete

    def post(self, path, json):
        assert path == "/announcements"
        self.next_id += 1
        self.notices[self.next_id] = {"id": self.next_id, **json}
        return {"id": self.next_id, **json}

    def delete(self, path):
        nid = int(path.rsplit("/", 1)[1])
        if not self.keep_after_delete:
            self.notices.pop(nid, None)

    def get(self, path):
        if path == "/hardware/queue":
            return [{"id": 1, "announcement_id": n["id"], "title": n["title"]} for n in self.notices.values()]
        return list(self.notices.values())


def test_notices_are_tagged_quiet_and_cleaned_up():
    backend = FakeBackend()
    with LiveNotices(backend) as notices:
        created = notices.create("Speaker check", "Body text", speaker_node_id=13)
        assert created["title"].startswith(f"[ES-TEST {notices.run_id}]")
        assert created["deliver_push"] is False
        assert created["deliver_in_app"] is False
        assert created["deliver_speaker"] is True
        assert created["speaker_node_id"] == 13
    assert backend.notices == {}


def test_cleanup_runs_after_a_failure_and_reports_leftovers():
    backend = FakeBackend(keep_after_delete=True)
    with pytest.raises(AssertionError, match="left behind"):
        with LiveNotices(backend) as notices:
            notices.create("Speaker check", "Body text")
            raise RuntimeError("the check itself failed")


def test_opening_the_real_port_does_not_reset_the_esp32(monkeypatch):
    # On this board DTR/RTS drive EN/BOOT: opening the port with them asserted reboots the ESP32.
    import serial

    events = []

    class RecordingSerial:
        def __init__(self, *args, **kwargs):
            events.append(("init", args, kwargs))

        def __setattr__(self, name, value):
            events.append(("set", name, value))
            object.__setattr__(self, name, value)

        def open(self):
            events.append(("open",))

        def readline(self):
            time.sleep(0.01)
            return b""

        def close(self):
            pass

    monkeypatch.setattr(serial, "Serial", RecordingSerial)
    with Esp32Serial(port="COM99"):
        pass
    init = events[0]
    assert init[1] == () and "port" not in init[2], "port must not be opened in the constructor"
    opened = events.index(("open",))
    assert ("set", "dtr", False) in events[:opened]
    assert ("set", "rts", False) in events[:opened]
    assert ("set", "port", "COM99") in events[:opened]


def test_timeout_message_is_printable_on_any_console():
    port = FakePort(["✅ [WIFI] Connected! 🚀\r\n".encode()])
    with Esp32Serial(port_factory=lambda: port) as esp:
        with pytest.raises(AssertionError) as exc:
            esp.wait_for(r"never", timeout=0.2)
    str(exc.value).encode("cp1252")  # Windows console encoding must not choke
    assert "[WIFI] Connected!" in str(exc.value)


def test_position_after_last_match_and_lines_since():
    port = FakePort([b"A start\r\n", b"B stopped early\r\n", b"C next\r\n"])
    with Esp32Serial(port_factory=lambda: port) as esp:
        esp.wait_for(r"C next", timeout=1)
        start = 0
        esp.wait_for(r"A start", timeout=1, since=start)
        after_a = esp.after_last_match()
        assert esp.lines_since(after_a) == ["B stopped early", "C next"]
        line, _ = esp.wait_for(r"next", timeout=1, since=after_a)
        assert line == "C next"
        assert esp.lines_since(esp.after_last_match()) == []


def test_speaker_is_busy_only_with_something_playing_or_due_soon():
    from datetime import datetime, timedelta, timezone

    from scripts.live_support import speaker_busy

    now = datetime(2026, 10, 22, 16, 0, tzinfo=timezone.utc)

    def item(status, minutes_from_now=None):
        when = None if minutes_from_now is None else (now + timedelta(minutes=minutes_from_now)).isoformat()
        return {"id": 1, "status": status, "scheduled_time": when, "title": "x"}

    assert speaker_busy([], now) == []
    assert speaker_busy([item("Completed")], now) == []
    assert speaker_busy([item("Queued", minutes_from_now=60 * 20)], now) == []  # tomorrow's notice
    assert speaker_busy([item("Playing")], now)
    assert speaker_busy([item("Held")], now)
    assert speaker_busy([item("Paused")], now)
    assert speaker_busy([item("Queued", minutes_from_now=5)], now)  # would play during the check
    assert speaker_busy([item("Queued")], now)  # no time means "now"
