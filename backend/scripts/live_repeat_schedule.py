"""
Live check: an INTERVAL repeat (every 1 min, 2 rounds) plays on the ESP32 on time and stops after its last
round (.agents/rules/testing.md §4-5). Replaces live_fullstack_queue_test.py and live_verify_user_repeat_fix.py.
Takes about 3.5 minutes.

    python backend/scripts/live_repeat_schedule.py      (close any other serial monitor on COM7 first)
"""
import sys

from live_support import speaker_busy, ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, wait_until

SCHEDULE = {"repeat_mode": "INTERVAL", "interval_minutes": 1, "max_repeats": 2, "play_on_publish": True}


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
        mark = esp.mark()
        ann = notices.create("Repeat check", "Short repeating speaker test notice.", speaker_node_id=ESP32_NODE_ID, repeat_schedule=SCHEDULE)
        nid = ann["id"]
        session.put(f"/announcements/{nid}/repeat-schedule", json=SCHEDULE)  # same call the app makes
        stream = rf"Streaming from URL: .*/announcements/{nid}/audio/stream"
        print(f"published repeating notice #{nid} {notices.tag}")

        _, t = esp.wait_for(stream, timeout=15, since=mark)
        print(f"PASS round 1 started after {t:.2f}s")
        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=esp.after_last_match())
        print(f"PASS round 1 finished after {t:.2f}s")

        _, t = esp.wait_for(stream, timeout=90, since=esp.after_last_match())
        print(f"PASS round 2 started {t:.2f}s after round 1 finished")
        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=esp.after_last_match())
        print(f"PASS round 2 finished after {t:.2f}s")
        after_last_round = esp.after_last_match()

        def inactive():
            sched = session.get(f"/announcements/{nid}/repeat-schedule")
            return sched is not None and sched.get("is_active") is False

        _, t = wait_until(inactive, timeout=15, what="repeat schedule to deactivate after max_repeats")
        print(f"PASS schedule deactivated after its last round ({t:.2f}s)")

        try:
            esp.wait_for(stream, timeout=75, since=after_last_round)
        except AssertionError:
            print("PASS no third round within 75s")
        else:
            raise AssertionError("a third round played although max_repeats is 2")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
