"""
Live check: pausing a playing notice silences the ESP32 at once and clears its sound buffer (no looping
"broken record" noise), it stays silent while paused, and resuming plays it again to the end
(.agents/rules/testing.md §4-5). Pause and resume are sent exactly as the app sends them.

The serial log proves the clearing ran; only a listener can confirm the speaker is truly silent.

    python backend/scripts/live_speaker_pause.py      (close any other serial monitor on COM7 first)
"""
import sys
import time

from live_support import ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, speaker_busy

LONG_TEXT = (
    "This is a longer speaker test notice for the pause check. It keeps playing for a while so that it can be "
    "paused in the middle. When it is paused the speaker must go silent at once and stay silent."
)


def action(session, nid, act):
    return session.post(f"/hardware/queue/{nid}/action?action={act}&target=announcement")


def main() -> None:
    session = LiveSession.login()
    busy = speaker_busy(session.get("/hardware/queue"))
    assert not busy, f"speaker is busy ({len(busy)} item(s) playing or due soon); not interrupting real notices"

    with Esp32Serial() as esp, LiveNotices(session) as notices:
      try:
          mark = esp.mark()
          ann = notices.create("Pause check", LONG_TEXT, speaker_node_id=ESP32_NODE_ID)
          nid = ann["id"]
          stream = rf"Streaming from URL: .*/announcements/{nid}/audio/stream"
          _, t = esp.wait_for(stream, timeout=15, since=mark)
          print(f"PASS notice #{nid} {notices.tag} streaming after {t:.2f}s")
          time.sleep(3)  # into the middle of playback (setup, not a proof step)

          before = esp.mark()
          action(session, nid, "pause")
          _, t = esp.wait_for(r"Stop received during playback|Stream stopped early", timeout=5, since=before)
          print(f"PASS stream stopped {t:.2f}s after pause")
          assert t <= 1.5, f"pause took {t:.2f}s to stop the stream"
          _, t = esp.wait_for(r"Output silenced and sound buffer cleared", timeout=3, since=before)
          print(f"PASS speaker output silenced and buffer cleared ({t:.2f}s after pause)")

          held = esp.mark()
          try:
              esp.wait_for(stream, timeout=8, since=held)
          except AssertionError:
              print("PASS stayed paused for 8s (no restart)")
          else:
              raise AssertionError("the paused notice started playing again by itself")

          before_resume = esp.mark()
          action(session, nid, "play")
          _, t = esp.wait_for(stream, timeout=15, since=before_resume)
          print(f"PASS resume restarted the notice after {t:.2f}s")
          _, t = esp.wait_for(r"Notice speech playback completed successfully", timeout=90, since=esp.after_last_match())
          print(f"PASS resumed notice played to the end after {t:.2f}s")
      except AssertionError:
        time.sleep(20)  # keep recording what the speaker does after a failed step, for diagnosis
        raise
      finally:
        import tempfile, os
        log = esp.save_log(os.path.join(tempfile.gettempdir(), "echosphere_live_speaker_pause_serial.log"))
        print(f"serial log: {log}")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
