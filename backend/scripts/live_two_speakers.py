"""
Live check with TWO ESP32 speakers (COM7 = node 13, COM9 = node 23), each acting as its own department
(.agents/rules/testing.md §4-5): a speaker notice reaches only the speaker it was sent to, and a notice for all
nodes reaches both. The proof is each board's own serial log.

    python backend/scripts/live_two_speakers.py      (close any other serial monitor on COM7 and COM9 first)
"""
import os
import sys
import time

from live_support import Esp32Serial, LiveNotices, LiveSession, speaker_busy

NODE_1, NODE_2 = 13, 23
PORT_1, PORT_2 = os.environ.get("ES_ESP32_PORT", "COM7"), os.environ.get("ES_ESP32_PORT_2", "COM9")
DONE = r"Notice speech playback completed successfully"


def main() -> None:
    session = LiveSession.login()
    nodes = {n["id"]: n for n in session.get("/hardware/speakers")}
    assert NODE_1 in nodes and NODE_2 in nodes, f"both speakers must be registered, found {sorted(nodes)}"
    assert nodes[NODE_1]["status"] == "ONLINE" and nodes[NODE_2]["status"] == "ONLINE", \
        {i: n["status"] for i, n in nodes.items()}
    assert not speaker_busy(session.get("/hardware/queue")), "a speaker is busy; not interrupting real notices"

    with Esp32Serial(port=PORT_1) as esp1, Esp32Serial(port=PORT_2) as esp2, LiveNotices(session) as notices:
        def run_case(label, node_id, expect1, expect2):
            m1, m2 = esp1.mark(), esp2.mark()
            ann = notices.create(label, f"Targeting check: {label}.", speaker_node_id=node_id)
            stream = rf"Streaming from URL: .*/announcements/{ann['id']}/audio/stream"
            for name, esp, mark, expected in (("speaker 1", esp1, m1, expect1), ("speaker 2", esp2, m2, expect2)):
                if expected:
                    _, t = esp.wait_for(stream, timeout=25, since=mark)
                    print(f"PASS {label}: {name} played it ({t:.1f}s)")
            for name, esp, mark, expected in (("speaker 1", esp1, m1, expect1), ("speaker 2", esp2, m2, expect2)):
                if expected:
                    esp.wait_for(DONE, timeout=90, since=mark)
            time.sleep(6)  # a speaker that must NOT play it has had every chance to
            for name, esp, mark, expected in (("speaker 1", esp1, m1, expect1), ("speaker 2", esp2, m2, expect2)):
                if not expected:
                    lines = esp.lines_since(mark)
                    heard = [l for l in lines if f"/announcements/{ann['id']}/audio/stream" in l]
                    assert not heard, f"{label}: {name} played a notice that was not for it: {heard[0][:100]}"
                    print(f"PASS {label}: {name} did not play it")
            session.delete(f"/announcements/{ann['id']}")
            notices.created_ids.remove(ann["id"])

        run_case("Only speaker 1", NODE_1, True, False)
        run_case("Only speaker 2", NODE_2, False, True)
        run_case("All speakers", None, True, True)
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
