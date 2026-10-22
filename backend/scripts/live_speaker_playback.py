"""
Live check: a published speaker notice plays on the physical ESP32 and completes (.agents/rules/testing.md §4-5).

Publishes one quiet [ES-TEST] notice to the ESP32 (no push, not in the feed), then asserts on the speaker's own
serial log: play command received, audio streaming, playback completed, completion acknowledged by the backend.
Always deletes the notice and fails on leftovers. Refuses to run while something is playing or due within 10 minutes.

    python backend/scripts/live_speaker_playback.py      (close any other serial monitor on COM7 first)
"""
import sys

from live_support import speaker_busy, ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, wait_until


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
        mark = esp.mark()
        ann = notices.create("Speaker playback check", "This is a short speaker test.", speaker_node_id=ESP32_NODE_ID)
        nid = ann["id"]
        print(f"published test notice #{nid} {notices.tag}")

        _, t = esp.wait_for(rf"Play command received for notice #{nid}\b", timeout=10, since=mark)
        print(f"PASS ESP32 received play command in {t:.2f}s")

        _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{nid}/audio/stream", timeout=15, since=mark)
        print(f"PASS ESP32 started streaming the notice audio after {t:.2f}s")

        _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=mark)
        print(f"PASS ESP32 finished playback after {t:.2f}s")

        _, t = esp.wait_for(r"\[QUEUE AUTO-ADVANCE\] Server acknowledged completion", timeout=15, since=mark)
        print(f"PASS backend acknowledged completion after {t:.2f}s")

        def done():
            items = [q for q in session.get("/hardware/queue") if q.get("announcement_id") == nid]
            return all(q.get("status") == "Completed" for q in items) or not items

        _, t = wait_until(done, timeout=10, what=f"notice #{nid} to leave the active queue")
        print(f"PASS notice left the active queue ({t:.2f}s)")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
