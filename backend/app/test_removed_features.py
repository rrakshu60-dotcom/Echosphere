"""Features removed on the owner's decision (2026-10-23) stay removed."""
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")


def test_manual_queue_advance_and_repeat_now_are_gone():
    # The queue and repeat rounds move by themselves; these were also callable without a login.
    assert client.post("/api/v1/hardware/queue/advance", headers=ADMIN).status_code in (404, 405)
    assert client.post("/api/v1/hardware/queue/1/trigger_repeat_now", headers=ADMIN).status_code in (404, 405)


def test_repeat_test_triggers_with_a_made_up_clock_are_gone():
    # Any signed-in user could run the repeat dispatcher at a simulated time; the daemon does this itself.
    assert client.post("/api/v1/repeat-schedules/evaluate-dispatch?simulated_time=11:05", headers=ADMIN).status_code in (404, 405, 422)
    assert client.post("/api/v1/repeat-schedule/trigger-check?simulated_time=11:05", headers=ADMIN).status_code in (404, 405, 422)


def test_listing_speakers_never_adds_renames_or_deletes_speakers():
    from app.db.database import SessionLocal
    from app.models.speaker_node import SpeakerNode

    with SessionLocal() as db:
        real = db.query(SpeakerNode).order_by(SpeakerNode.id).first()
        real_mac = real.mac_address
        real.name = "Main Corridor Speaker"  # an admin renamed it
        db.add(SpeakerNode(name="New Hall Speaker", mac_address="AA:BB:CC:DD:EE:01", zone="Hall", status="OFFLINE",
                           volume=80, is_active=True, last_heartbeat=None))  # added by an admin, no heartbeat yet
        db.commit()
        for fake in db.query(SpeakerNode).filter(SpeakerNode.mac_address.in_(
                ["D4:F3:2D:22:2A:CB", "D4:F3:2D:22:2A:CC", "24:0A:C4:00:01:10"])):
            db.delete(fake)
        db.commit()

    res = client.get("/api/v1/hardware/speakers", headers=ADMIN)
    assert res.status_code == 200, res.text
    by_mac = {n["mac_address"]: n["name"] for n in res.json()}
    assert by_mac.get(real_mac) == "Main Corridor Speaker", "the rename was undone"
    assert "AA:BB:CC:DD:EE:01" in by_mac, "a newly added speaker was deleted before its first heartbeat"
    for fake in ("D4:F3:2D:22:2A:CB", "D4:F3:2D:22:2A:CC", "24:0A:C4:00:01:10"):
        assert fake not in by_mac, f"deleted test speaker {fake} came back"


def test_speaker_commands_do_not_probe_a_message_broker(monkeypatch):
    """Speakers get commands over their push socket and heartbeat; there is no MQTT broker."""
    import socket

    probes = []
    real_connect_ex = socket.socket.connect_ex

    def recording_connect_ex(self, address):
        probes.append(address)
        return real_connect_ex(self, address)

    monkeypatch.setattr(socket.socket, "connect_ex", recording_connect_ex)
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Broker check", "description": "Plays on the speaker.", "category_id": 1,
        "target_audience": "Entire College", "deliver_push": False, "deliver_in_app": False, "deliver_speaker": True})
    assert res.status_code in (200, 201), res.text
    assert not [a for a in probes if isinstance(a, tuple) and a[1] == 1883], probes
