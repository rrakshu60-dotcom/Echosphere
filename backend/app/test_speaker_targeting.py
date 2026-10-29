"""
A notice sent to one speaker plays on that speaker every time: when it is sent again from the app, and when the
queue starts it. On 29 Oct a notice meant for one speaker played on another when it was broadcast again,
because "Entire College" (who should hear it) was read as "every speaker" (where it plays).
Also checks that a notice keeps the audience it was published for.
"""
import json

import pytest

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
from app.models.speaker_command import SpeakerCommand
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue

client = TestClient(app)
ADMIN = bearer("ESDev01")
SPEAKER_1 = "D4:F3:2D:00:00:01"
SPEAKER_2 = "D4:F3:2D:00:00:02"


@pytest.fixture(autouse=True)
def _idle_queue_and_two_speakers():
    with SessionLocal() as db:
        db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(("Playing", "Next in Queue", "Queued", "Paused", "Held"))).update(
            {SpeakerQueue.status: "Completed"}, synchronize_session=False)
        db.query(AnnouncementRepeatSchedule).update({AnnouncementRepeatSchedule.is_active: False}, synchronize_session=False)
        for i, mac in enumerate((SPEAKER_1, SPEAKER_2), start=1):
            if not db.query(SpeakerNode).filter(SpeakerNode.mac_address == mac).first():
                db.add(SpeakerNode(name=f"Targeting test speaker {i}", mac_address=mac, zone=f"Block {i}", status="ONLINE"))
        db.commit()


def _node_id(mac):
    with SessionLocal() as db:
        return db.query(SpeakerNode.id).filter(SpeakerNode.mac_address == mac).scalar()


def _publish(title, **fields) -> int:
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": title, "description": f"{title} body text.", "category_id": 2,
        "deliver_push": False, "deliver_in_app": False, "deliver_speaker": True, **fields})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _play_targets(nid):
    """MACs the play commands for this notice went to, oldest first (None: every speaker)."""
    with SessionLocal() as db:
        rows = db.query(SpeakerCommand).filter(SpeakerCommand.command.in_(("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"))).order_by(SpeakerCommand.id).all()
        return [r.target_mac for r in rows if json.loads(r.payload_json or "{}").get("announcement_id") == nid]


def _finish(nid):
    with SessionLocal() as db:
        for q in db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid):
            q.status = "Completed"
        db.commit()


def test_sending_a_notice_again_keeps_its_speaker():
    nid = _publish("Lab timing change", target_audience="Entire College", speaker_node_id=_node_id(SPEAKER_1))
    assert _play_targets(nid) == [SPEAKER_1]
    _finish(nid)

    # The app's "broadcast to speaker" on a published notice sends no node
    res = client.post("/api/v1/hardware/queue/add", headers=ADMIN, json={"announcement_id": nid})
    assert res.status_code == 200, res.text
    assert _play_targets(nid)[-1] == SPEAKER_1, "the notice must play on the speaker it was sent to, not on every speaker"


def test_sending_a_notice_again_to_every_speaker():
    nid = _publish("Library notice", speaker_node_id=_node_id(SPEAKER_1))
    _finish(nid)
    res = client.post("/api/v1/hardware/queue/add", headers=ADMIN, json={"announcement_id": nid, "speaker_node_id": 0})
    assert res.status_code == 200, res.text
    assert _play_targets(nid)[-1] is None, "0 asks for every speaker"


def test_sending_a_notice_again_to_another_speaker():
    nid = _publish("Seminar notice", speaker_node_id=_node_id(SPEAKER_1))
    _finish(nid)
    res = client.post("/api/v1/hardware/queue/add", headers=ADMIN, json={"announcement_id": nid, "speaker_node_id": _node_id(SPEAKER_2)})
    assert res.status_code == 200, res.text
    assert _play_targets(nid)[-1] == SPEAKER_2


def test_the_play_button_keeps_the_notices_speaker():
    nid = _publish("Exam hall notice", target_audience="Entire College", speaker_node_id=_node_id(SPEAKER_2))
    res = client.post(f"/api/v1/hardware/queue/{nid}/action?action=play&target=announcement", headers=ADMIN)
    assert res.status_code == 200, res.text
    assert _play_targets(nid)[-1] == SPEAKER_2


def test_a_notice_for_every_speaker_still_plays_everywhere():
    nid = _publish("College-wide notice")
    assert _play_targets(nid) == [None]


def test_a_notice_keeps_its_audience_and_speaker():
    node = _node_id(SPEAKER_1)
    nid = _publish("CSE seminar", target_audience="CSE Department", speaker_node_id=node)
    res = client.get(f"/api/v1/announcements/{nid}", headers=ADMIN)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["target_audience"] == "CSE Department"
    assert body["speaker_node_id"] == node
    assert body["deliver_in_app"] is False and body["deliver_push"] is False and body["deliver_speaker"] is True
