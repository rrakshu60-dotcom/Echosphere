"""
Live check: two notices published back to back play one after the other on the ESP32; the second never
interrupts the first (.agents/rules/testing.md §4-5). Replaces test_live_homotemporal_queue.py.

    python backend/scripts/live_queue_order.py      (close any other serial monitor on COM7 first)
"""
import sys

from live_support import speaker_busy, ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession

STOPPED_EARLY = ("Stream stopped early", "Stop received during playback", "Server ended this notice early")


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
        mark = esp.mark()
        first = notices.create("Queue order check one", "First of two short speaker test notices.", speaker_node_id=ESP32_NODE_ID)
        second = notices.create("Queue order check two", "Second of two short speaker test notices.", speaker_node_id=ESP32_NODE_ID)
        print(f"published #{first['id']} and #{second['id']} {notices.tag}")

        _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{first['id']}/audio/stream", timeout=15, since=mark)
        print(f"PASS first notice started streaming after {t:.2f}s")
        during_first = esp.after_last_match()

        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=during_first)
        print(f"PASS first notice played to the end after {t:.2f}s")
        first_lines = esp.lines_since(during_first)
        assert not any(s in line for line in first_lines for s in STOPPED_EARLY), "first notice was cut short"
        assert not any(f"/announcements/{second['id']}/" in line for line in first_lines[:-1]), \
            "second notice started while the first was still playing"

        _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{second['id']}/audio/stream", timeout=20, since=esp.after_last_match())
        print(f"PASS second notice started {t:.2f}s after the first finished")

        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=esp.after_last_match())
        print(f"PASS second notice played to the end after {t:.2f}s")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
