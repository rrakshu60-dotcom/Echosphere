"""
Live check: an emergency notice interrupts a playing notice on the ESP32 within 1s, plays with the siren,
and the interrupted notice plays again afterwards (.agents/rules/testing.md §4-5).
Replaces test_live_emergency_override.py.

The test emergency uses emergency_level "Emergency" with High priority: priority EMERGENCY would force a
real push notification to every phone, which a test must never do.

    python backend/scripts/live_emergency_override.py      (close any other serial monitor on COM7 first)
"""
import sys
import time

from live_support import speaker_busy, ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession

LONG_TEXT = (
    "This is a longer speaker test notice. It keeps playing for a while so that an emergency test notice "
    "can interrupt it in the middle. After the emergency finishes, this notice should play again from the start."
)


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
      try:
          mark = esp.mark()
          normal = notices.create("Emergency check normal notice", LONG_TEXT, speaker_node_id=ESP32_NODE_ID)
          _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{normal['id']}/audio/stream", timeout=15, since=mark)
          print(f"PASS normal notice #{normal['id']} streaming after {t:.2f}s")
          time.sleep(3)  # let it get into the middle of playback (setup, not a proof step)

          before = esp.mark()
          sent = time.monotonic()
          emergency = notices.create(
              "Emergency check alert",
              "This is a test emergency alert.",
              speaker_node_id=ESP32_NODE_ID,
              priority="High",
              emergency_level="Emergency",
          )
          accepted = time.monotonic() - sent
          print(f"published test emergency #{emergency['id']} (backend accepted in {accepted:.2f}s)")

          _, t = esp.wait_for(r"Stop received during playback|Stream stopped early|Server ended this notice early", timeout=5, since=before)
          print(f"PASS normal notice interrupted {t:.2f}s after the backend accepted the emergency")
          assert t <= 1.0, f"interruption took {t:.2f}s, rule is under 1s"

          _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{emergency['id']}/audio/stream", timeout=15, since=before)
          print(f"PASS emergency audio streaming after {t:.2f}s")
          _, t = esp.wait_for(r"Emergency Siren", timeout=15, since=before)
          print(f"PASS emergency siren played ({t:.2f}s)")
          _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=60, since=esp.after_last_match())
          print(f"PASS emergency finished after {t:.2f}s")

          _, t = esp.wait_for(rf"Streaming from URL: .*/announcements/{normal['id']}/audio/stream", timeout=30, since=esp.after_last_match())
          print(f"PASS interrupted notice resumed {t:.2f}s after the emergency")
          _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=90, since=esp.after_last_match())
          print(f"PASS interrupted notice played to the end after {t:.2f}s")
      finally:
        import os, tempfile
        print(f"serial log: {esp.save_log(os.path.join(tempfile.gettempdir(), 'echosphere_live_emergency_serial.log'))}")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
