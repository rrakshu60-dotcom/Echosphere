"""
Live check: the Speaker Queue page names the speaker each notice is for (full name, no clipping).
Publishes one notice for speaker 2 (plays on COM9) and one for speaker 1 (waits behind it), reads the open
agent-browser page, then deletes both. Open the Smart Speaker page in agent-browser (signed in) first.

    python backend/scripts/live_queue_target_speaker.py
"""
import os
import subprocess
import sys
import time

from live_support import Esp32Serial, LiveNotices, LiveSession, speaker_busy

NODE_1, NODE_2 = 13, 23
PORT_2 = os.environ.get("ES_ESP32_PORT_2", "COM9")


def page_text() -> str:
    return subprocess.run(["agent-browser", "snapshot"], capture_output=True, text=True, encoding="utf-8", timeout=60, shell=True).stdout


def main() -> None:
    session = LiveSession.login()
    nodes = {n["id"]: n for n in session.get("/hardware/speakers")}
    assert nodes[NODE_2]["status"] == "ONLINE", nodes[NODE_2]["status"]
    assert not speaker_busy(session.get("/hardware/queue")), "a speaker is busy; not interrupting real notices"
    name1, name2 = nodes[NODE_1]["name"], nodes[NODE_2]["name"]
    print(f"speakers: 1={name1!r} 2={name2!r}")

    with Esp32Serial(port=PORT_2) as esp2, LiveNotices(session) as notices:
        mark = esp2.mark()
        a = notices.create("Queue target check A", "Queue target check for speaker two.", speaker_node_id=NODE_2)
        b = notices.create("Queue target check B", "Queue target check for speaker one.", speaker_node_id=NODE_1)
        esp2.wait_for(rf"Streaming from URL: .*/announcements/{a['id']}/audio/stream", timeout=25, since=mark)
        print("PASS speaker 2 is playing notice A")
        deadline, text = time.time() + 20, ""
        while time.time() < deadline:
            text = page_text()
            if "Queue target check B" in text and "Queue target check A" in text:
                break
            time.sleep(1)
        print("\n".join(l for l in text.splitlines() if "Queue target check" in l or "ONLINE" in l or "OFFLINE" in l)[:1500])
        assert f"{name2} \u2022 ONLINE" in text, f"page does not show speaker 2 as {name2!r}"
        assert f"{name1} \u2022 ONLINE" in text, f"page does not show speaker 1 as {name1!r}"
        print("PASS queue shows both full speaker names with ONLINE status")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
