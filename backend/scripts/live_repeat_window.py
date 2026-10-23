"""
Live check: a custom repeat window (set as the app sets it) keeps rotating on the ESP32 by itself: rounds follow
each other after the normal gap with nobody pressing play, each round is counted once, and when the window is over
the notice leaves the queue and its schedule ends (owner, 2026-10-23) (.agents/rules/testing.md §4-5).
Takes about 4 minutes.

    python backend/scripts/live_repeat_window.py      (close any other serial monitor on COM7 first)
"""
import sys
from datetime import datetime, timedelta, timezone

from live_support import ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, speaker_busy, wait_until

ROUNDS = 3
DONE = r"Notice speech playback completed successfully"


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    utc = datetime.now(timezone.utc)
    ist = utc + timedelta(hours=5, minutes=30)
    schedule = {  # what the app's repeat dialog sends for a custom time window
        "is_active": True, "repeat_mode": "BREAK_SLOTS", "interval_minutes": 0, "max_repeats": 6,
        "play_on_publish": False, "selected_slots": ["CUSTOM_WINDOW"], "target_scope": "COLLEGE_WIDE",
        "custom_start_time": (ist - timedelta(minutes=1)).strftime("%H:%M"),
        "custom_end_time": (ist + timedelta(minutes=3)).strftime("%H:%M"),
        "start_date": (utc - timedelta(minutes=5)).isoformat(), "end_date": (utc + timedelta(hours=48)).isoformat(),
        "force_enable_speaker": True,
    }

    with Esp32Serial() as esp, LiveNotices(session) as notices:
        mark = esp.mark()
        ann = notices.create("Repeat window check", "Short repeating window test notice.", speaker_node_id=ESP32_NODE_ID)
        nid = ann["id"]
        session.put(f"/announcements/{nid}/repeat-schedule", json=schedule)
        stream = rf"Streaming from URL: .*/announcements/{nid}/audio/stream"
        print(f"published notice #{nid} {notices.tag}, window {schedule['custom_start_time']}-{schedule['custom_end_time']} IST")

        _, t = esp.wait_for(stream, timeout=20, since=mark)
        print(f"PASS round 1 started after {t:.2f}s")
        for n in range(1, ROUNDS + 1):
            _, t = esp.wait_for(DONE, timeout=90, since=esp.after_last_match())
            print(f"PASS round {n} finished after {t:.2f}s")
            if n < ROUNDS:
                _, t = esp.wait_for(stream, timeout=20, since=esp.after_last_match())
                print(f"PASS round {n + 1} started by itself {t:.2f}s after round {n} finished")

        # The speaker reports a round finished just after logging it; a round is counted once finished
        def counted():
            return session.get(f"/announcements/{nid}/repeat-schedule").get("total_played_count")
        _, t = wait_until(lambda: counted() == ROUNDS, timeout=5, what=f"schedule to count {ROUNDS} rounds")
        count = counted()
        assert count == ROUNDS, f"schedule counted {count} rounds, the speaker finished {ROUNDS}"
        print(f"PASS each round counted once ({count})")

        def finished():
            in_queue = [q for q in session.get("/hardware/queue") if q["announcement_id"] == nid]
            sched = session.get(f"/announcements/{nid}/repeat-schedule") or {}
            return not in_queue and sched.get("is_active") is False
        _, t = wait_until(finished, timeout=240, interval=2, what="notice to leave the queue after its window")
        print(f"PASS window over: notice left the queue and its schedule ended ({t:.0f}s later)")
        after = esp.mark()
        try:
            esp.wait_for(stream, timeout=20, since=after)
        except AssertionError:
            print("PASS no round after the window")
        else:
            raise AssertionError("a round played after the window had finished")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
