"""
A pause (the 'Held' status) must never leave the speakers silent for good. Seen live: a notice was paused while the
speakers were offline, the hold stayed, and every notice published after it waited in the queue without playing.
Now a newly published notice ends the pause, and a hold nobody resumes expires after HOLD_MAX_MINUTES.
"""
from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.services.hardware_speaker_service import HOLD_MAX_MINUTES

client = TestClient(app)
ADMIN = bearer("ESDev01")
ACTIVE = ("Playing", "Next in Queue", "Queued")


@pytest.fixture(autouse=True)
def _empty_speaker_queue():
    with SessionLocal() as db:
        db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(ACTIVE + ("Paused", "Held"))).update(
            {SpeakerQueue.status: "Completed"}, synchronize_session=False)
        db.query(AnnouncementRepeatSchedule).update({AnnouncementRepeatSchedule.is_active: False}, synchronize_session=False)
        db.commit()


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _publish(title) -> int:
    with SessionLocal() as db:
        node_id = db.query(SpeakerNode.id).first()[0]
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": title, "description": f"{title} body text.", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False, "deliver_speaker": True, "speaker_node_id": node_id})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _pause(nid):
    res = client.post(f"/api/v1/hardware/queue/{nid}/action?action=pause&target=announcement", headers=ADMIN)
    assert res.status_code == 200, res.text


def _status(nid):
    with SessionLocal() as db:
        return db.query(SpeakerQueue.status).filter(SpeakerQueue.announcement_id == nid).order_by(SpeakerQueue.id.desc()).first()[0]


def _daemon_pass():
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    with SessionLocal() as db:
        auto_advance_speaker_queue(db)


def test_publishing_a_notice_ends_a_pause_and_plays_it():
    paused = _publish("Hold test paused notice")
    assert _status(paused) == "Playing"
    _pause(paused)
    assert _status(paused) == "Held"

    fresh = _publish("Hold test fresh notice")
    assert _status(fresh) == "Playing"
    assert _status(paused) in ("Next in Queue", "Queued")  # back in the queue behind it, not lost


def test_a_forgotten_hold_expires_and_the_queue_moves_on():
    paused = _publish("Hold test forgotten notice")
    _pause(paused)
    with SessionLocal() as db:  # the pause was pressed long ago, and a notice is waiting behind it
        held = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == paused).one()
        db.query(SpeakerQueue).filter(SpeakerQueue.id == held.id).update(
            {SpeakerQueue.updated_at: _utc_now() - timedelta(minutes=HOLD_MAX_MINUTES + 1)}, synchronize_session=False)
        waiting = _publish_while_held(db)
        db.commit()

    _daemon_pass()
    assert _status(paused) == "Cancelled"
    assert _status(waiting) == "Playing"


def test_a_recent_hold_still_holds():
    paused = _publish("Hold test recent pause")
    _pause(paused)
    with SessionLocal() as db:
        waiting = _publish_while_held(db)
        db.commit()

    _daemon_pass()
    assert _status(paused) == "Held"
    assert _status(waiting) == "Next in Queue"


def _publish_while_held(db) -> int:
    """A notice that reached the queue while the hold was on, as the live one did before this fix."""
    from app.models.announcement import Announcement
    template = db.query(Announcement).order_by(Announcement.id.desc()).first()
    waiting = Announcement(
        title=f"{template.title} (waiting)", description=template.description, status=template.status,
        priority=template.priority, emergency_level=template.emergency_level, created_by=template.created_by,
        category_id=template.category_id, speaker_voice=template.speaker_voice,
    )
    db.add(waiting)
    db.flush()
    db.add(SpeakerQueue(announcement_id=waiting.id, queue_position=2, status="Next in Queue",
                        scheduled_time=_utc_now() - timedelta(seconds=5)))
    return waiting.id
