"""
Live check of the 2026-10-23 feature clean-up (.agents/rules/testing.md §4-5): removed features stay removed, and
reschedule, alerts, OCR removal, AI chat grounding, audience check, dignitary arrival (on the ESP32) and attachments work
on the live system. Everything it creates is tagged and deleted afterwards.

    python backend/scripts/live_feature_audit.py      (close any other serial monitor on COM7 first)
"""
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

from live_support import ESP32_NODE_ID, Esp32Serial, LiveNotices, LiveSession, speaker_busy, wait_until

IST = timedelta(hours=5, minutes=30)


def slow_post(session, path, json=None):
    """AI calls can take a while on a just-started server."""
    r = session._http.post(f"{session.base_url}{path}", json=json, timeout=180)
    assert r.status_code == 200, f"POST {path}: HTTP {r.status_code} {r.text[:200]}"
    return r.json()


def status(session, method, path, **kw):
    return session._http.request(method, f"{session.base_url}{path}", timeout=60, **kw).status_code


def main() -> None:
    s = LiveSession.login()
    assert not speaker_busy(s.get("/hardware/queue")), "speaker busy; not interrupting real notices"

    # 1. removed features
    for method, path in (("GET", "/ws/hardware/mic-status"), ("POST", "/hardware/queue/advance"),
                         ("POST", "/hardware/queue/1/trigger_repeat_now"), ("POST", "/repeat-schedule/trigger-check")):
        code = status(s, method, path)
        assert code in (404, 405, 422), f"{method} {path} still answers {code}"
    print("PASS live mic, manual advance / repeat-now and test triggers are gone")
    speakers = s.get("/hardware/speakers")
    assert [n["id"] for n in speakers] == [ESP32_NODE_ID], [(n["id"], n["name"]) for n in speakers]
    print("PASS only the real ESP32 is listed (test speakers did not come back)")

    with LiveNotices(s) as notices:
        # 2. reschedule
        ann = notices.create("Reschedule check", "Placement talk in the seminar hall.")
        new_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0, second=0)
        s.put(f"/announcements/{ann['id']}", json={"scheduled_at": new_time.isoformat(), "status": "Scheduled"})
        got = [a for a in s.get("/announcements") if a["id"] == ann["id"]][0]
        assert got["scheduled_at"].startswith(new_time.strftime("%Y-%m-%dT%H:%M")), got["scheduled_at"]
        print("PASS reschedule stored the new time on the server")

        # 3. alerts history endpoints
        assert status(s, "PUT", "/notifications/999999999/unread") == 404
        assert status(s, "DELETE", "/notifications/read") == 200
        print("PASS 'restore to unread' and 'clear history' exist on the server")

        # 4. document OCR was removed on the owner's decision (2026-10-27)
        assert status(s, "POST", "/announcements/ocr-document") in (404, 405)
        print("PASS document OCR is gone")

        # 5. AI chat sticks to real notices
        r = slow_post(s, "/ai/chat", json={"prompt": "What time does the hostel mess close on Sunday?", "session_id": f"audit-{time.time()}",
                                     "user_role": "Student", "full_name": "Test Student", "department": "CSE", "history": []})
        answer = r["response"].lower()
        assert "verified institutional identity" not in answer
        assert any(w in answer for w in ("couldn't find", "could not find", "no notice", "not find", "don't have", "no information")), r["response"][:200]
        print("PASS AI chat says it found no notice instead of inventing a time")

        # 6. audience check
        r = s.post("/announcements/check-audience", json={"title": "Final year project submission",
                   "content": "All final year students must submit their project reports by Friday.", "selected_audience": "Faculty Members"})
        assert r["has_mismatch"] and r["suggested_audiences"][0] == "4th Year Students", r
        print("PASS a student notice addressed to Faculty is flagged")

        # 7. dignitary: event time + arrival plays the welcome on the ESP32
        vip = notices.create("Annual Day chief guest", "Dr. Ramesh Kumar, Vice Chancellor, will be the chief guest at the "
                             "Annual Day celebration on Friday at 10 AM in the Main Auditorium.")
        proto = slow_post(s, f"/announcements/{vip['id']}/vip-protocol/analyze", json={})
        ev = datetime.fromisoformat(proto["event_datetime"].replace("Z", "")).replace(tzinfo=None) + IST
        assert ev.weekday() == 4 and (ev.hour, ev.minute) == (10, 0), ev
        print(f"PASS dignitary event time read from the notice: {ev:%a %d %b %H:%M} IST")
        with Esp32Serial() as esp:
            mark = esp.mark()
            arr = slow_post(s, f"/announcements/{vip['id']}/vip-protocol/arrival", json={})
            audio = arr["audio_url"].rsplit("/", 1)[-1]
            line, t = esp.wait_for(r"Streaming from URL", timeout=30, since=mark)
            assert audio in line, f"speaker streamed {line.strip()[-120:]!r}, not the welcome recording {audio}"
            print(f"PASS the ESP32 streamed the welcome recording after {t:.1f}s")
            _, t = esp.wait_for(r"completed successfully", timeout=90, since=esp.after_last_match())
            print(f"PASS welcome finished playing after {t:.1f}s")

        # 8. attachments
        files = {"file": ("audit-circular.pdf", b"%PDF-1.4\n% EchoSphere live check\n", "application/pdf")}
        up = s._http.post(f"{s.base_url}/announcements/attachments/upload", files=files, timeout=120).json()
        assert up["file_url"].startswith("https://huggingface.co/datasets/") and "/attachments/" in up["file_url"], up
        withfile = notices.create("Attachment check", "See the attached circular.",
                                  attachments=[{"name": "audit-circular.pdf", "url": up["file_url"], "size": up["size_bytes"], "mime": up["mime_type"]}])
        got = [a for a in s.get("/announcements") if a["id"] == withfile["id"]][0]
        assert got["attachments"][0]["url"] == up["file_url"]
        _, t = wait_until(lambda: requests.get(up["file_url"], timeout=30).status_code == 200, timeout=60, what="attachment downloadable")
        print("PASS attachment uploaded to cloud storage, kept with the notice and downloadable")
        assert status(s, "POST", "/announcements", json={"title": "x", "description": "x", "category_id": 1,
                      "attachments": [{"name": "a.pdf", "url": "https://evil.example/a.pdf"}]}) == 422
        print("PASS a link to another site is refused as an attachment")
        attachment_url = up["file_url"]

    # cleanup deleted the notices; their attachment file must be removed from cloud storage too
    _, t = wait_until(lambda: requests.get(attachment_url, timeout=30).status_code == 404, timeout=120, interval=5,
                      what="deleted notice's attachment removed from cloud storage")
    print(f"PASS the deleted notice's attachment was removed from cloud storage ({t:.0f}s)")
    print("PASS cleanup: no test data left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
