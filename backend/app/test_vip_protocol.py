"""Dignitary (VIP) protocol: the event time comes from the notice text, and the arrival announcement reaches the
speaker as a command it understands, carrying the welcome recording (it used to play the notice instead)."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.speaker_node import SpeakerNode

client = TestClient(app)
ADMIN = bearer("ESDev01")
IST = timedelta(hours=5, minutes=30)
TEXT = "Dr. Ramesh Kumar, Vice Chancellor, will be the chief guest at the Annual Day celebration on Friday at 10 AM in the Main Auditorium."


def _vip_notice() -> int:
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Annual Day chief guest", "description": TEXT, "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def test_the_event_time_is_read_from_the_notice():
    nid = _vip_notice()
    res = client.post(f"/api/v1/announcements/{nid}/vip-protocol/analyze", headers=ADMIN)
    assert res.status_code == 200, res.text
    event_utc = datetime.fromisoformat(res.json()["event_datetime"].replace("Z", "")).replace(tzinfo=None)
    event_ist = event_utc + IST
    now_ist = datetime.now(timezone.utc).replace(tzinfo=None) + IST
    assert event_ist.weekday() == 4 and (event_ist.hour, event_ist.minute) == (10, 0), event_ist  # Friday 10:00
    assert now_ist < event_ist <= now_ist + timedelta(days=7)


def test_the_arrival_reaches_the_speaker_with_the_welcome_recording():
    nid = _vip_notice()
    client.post(f"/api/v1/announcements/{nid}/vip-protocol/analyze", headers=ADMIN)
    res = client.post(f"/api/v1/announcements/{nid}/vip-protocol/arrival", headers=ADMIN, json={})
    assert res.status_code == 200, res.text
    welcome_audio = res.json()["audio_url"]
    with SessionLocal() as db:
        mac = db.query(SpeakerNode).first().mac_address
    hb = client.post("/api/v1/hardware/speakers/heartbeat", json={"mac_address": mac, "status": "ONLINE"}).json()
    plays = [c for c in hb.get("pending_commands") or [] if c.get("announcement_id") == nid and str(c.get("command", "")).startswith("PLAY")]
    assert plays, hb.get("pending_commands")
    assert all(c["command"] in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY") for c in plays), [c["command"] for c in plays]
    assert len(plays) == 1 and plays[0]["audio_url"] == welcome_audio, plays


def test_event_time_reader_handles_common_phrasings():
    from app.services.vip_announcement_service import event_time_from_text as read
    now = datetime(2026, 10, 23, 14, 0)  # Friday 2 PM, campus time
    assert read("Annual Day on Friday at 10 AM", now) == datetime(2026, 10, 30, 10, 0)  # this Friday's 10 AM has passed
    assert read("Annual Day on Friday at 6 PM", now) == datetime(2026, 10, 23, 18, 0)
    assert read("Convocation on 24 October at 4:30 pm", now) == datetime(2026, 10, 24, 16, 30)
    assert read("Guest lecture tomorrow at 9.15 a.m.", now) == datetime(2026, 10, 24, 9, 15)
    assert read("Guest lecture on Monday", now) is None  # no clock time
