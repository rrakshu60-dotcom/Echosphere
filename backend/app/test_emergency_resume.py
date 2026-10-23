"""An emergency interrupts the notice on the speaker; once the emergency finishes, the interrupted notice plays again."""
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue

client = TestClient(app)
ADMIN = bearer("ESDev01")


def _publish(title, **fields) -> int:
    with SessionLocal() as db:
        node_id = db.query(SpeakerNode.id).first()[0]
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": title, "description": f"{title} body text.", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False, "deliver_speaker": True, "speaker_node_id": node_id, **fields})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _item(nid) -> SpeakerQueue:
    with SessionLocal() as db:
        return db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid).order_by(SpeakerQueue.id.desc()).first()


def test_interrupted_notice_plays_again_after_the_emergency():
    normal = _publish("Library timing")
    assert _item(normal).status == "Playing"

    emergency = _publish("Fire drill now", priority="High", emergency_level="Emergency")
    assert _item(emergency).status == "Playing"
    assert _item(normal).status == "Paused"

    # The speaker reports the emergency finished, exactly as the firmware does
    res = client.post(f"/api/v1/hardware/queue/{_item(emergency).id}/action?action=complete")
    assert res.status_code == 200, res.text

    assert _item(emergency).status == "Completed"
    assert _item(normal).status in ("Playing", "Queued"), f"interrupted notice left as {_item(normal).status}"
