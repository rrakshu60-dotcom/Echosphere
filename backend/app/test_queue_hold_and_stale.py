"""
A paused notice must never freeze the speaker queue, and a notice no speaker ever played must not linger in it.
On 29 Oct a notice paused while the speakers were offline kept every later notice from playing.
Driven as on the live system: the app publishes and sends queue actions, and the queue daemon runs its pass after.
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
from app.services.hardware_speaker_service import STALE_NOTICE_MINUTES

client = TestClient(app)
ADMIN = bearer("ESDev01")
WAITING = ("Playing", "Next in Queue", "Queued", "Paused", "Held")


@pytest.fixture(autouse=True)
def _empty_speaker_queue():
    """Each test starts with an idle speaker, whatever an earlier test left behind."""
    with SessionLocal() as db:
        db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(WAITING)).update(
            {SpeakerQueue.status: "Completed"}, synchronize_session=False)
        db.query(AnnouncementRepeatSchedule).update({AnnouncementRepeatSchedule.is_active: False}, synchronize_session=False)
        db.commit()


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _publish(title, **fields) -> int:
    with SessionLocal() as db:
        node_id = db.query(SpeakerNode.id).first()[0]
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": title, "description": f"{title} body text.", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False, "deliver_speaker": True, "speaker_node_id": node_id, **fields})
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _daemon_pass():
    """One pass of the live queue daemon (main.py)."""
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    with SessionLocal() as db:
        auto_advance_speaker_queue(db)


def _action(nid, action):
    res = client.post(f"/api/v1/hardware/queue/{nid}/action?action={action}&target=announcement", headers=ADMIN)
    assert res.status_code == 200, res.text
    _daemon_pass()


def _status(nid):
    with SessionLocal() as db:
        return db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid).order_by(SpeakerQueue.id.desc()).first().status


def _age(nid, minutes):
    """Instead of waiting: make the notice due `minutes` ago."""
    with SessionLocal() as db:
        for q in db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid):
            q.scheduled_time = _utc_now() - timedelta(minutes=minutes)
        db.commit()


def test_a_paused_notice_does_not_stop_a_new_one_from_playing():
    old = _publish("Old notice")
    assert _status(old) == "Playing"
    _action(old, "pause")
    assert _status(old) == "Held"

    new = _publish("New notice")
    _daemon_pass()
    assert _status(new) == "Playing", "a paused notice must not hold the rest of the queue"
    assert _status(old) == "Held", "the paused notice stays paused until someone resumes it"


def test_a_waiting_notice_plays_after_the_notice_ahead_is_paused():
    first = _publish("First notice")
    second = _publish("Second notice")
    assert _status(first) == "Playing" and _status(second) in ("Next in Queue", "Queued")
    _action(first, "pause")
    assert _status(second) == "Playing"


def test_playing_another_notice_leaves_a_paused_one_paused():
    first = _publish("First notice")
    second = _publish("Second notice")
    _action(first, "pause")
    _action(second, "play")
    assert _status(second) == "Playing"
    assert _status(first) == "Held"


def test_a_paused_notice_no_speaker_started_leaves_the_queue_after_the_limit():
    nid = _publish("Never heard notice")
    _action(nid, "pause")
    _age(nid, STALE_NOTICE_MINUTES - 1)
    _daemon_pass()
    assert _status(nid) == "Held", "within the limit the paused notice stays"
    _age(nid, STALE_NOTICE_MINUTES + 1)
    _daemon_pass()
    assert _status(nid) == "Failed"
    with SessionLocal() as db:
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid).one()
        assert "No speaker played it" in (item.failure_reason or "")
    queue = client.get("/api/v1/hardware/queue", headers=ADMIN).json()
    items = queue if isinstance(queue, list) else queue.get("items") or queue.get("queue") or []
    assert all(i.get("announcement_id") != nid for i in items), "a failed notice must leave the queue page"


def test_a_paused_notice_a_speaker_did_play_is_kept():
    nid = _publish("Heard notice")
    with SessionLocal() as db:
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid).one()
        item.speaker_confirmed_at = _utc_now()
        db.commit()
    _action(nid, "pause")
    _age(nid, STALE_NOTICE_MINUTES + 5)
    _daemon_pass()
    assert _status(nid) == "Held", "a notice the speaker played is the user's to resume or remove"


def test_a_notice_waiting_behind_a_playing_one_is_not_expired():
    playing = _publish("Long notice")
    waiting = _publish("Waiting notice")
    _age(waiting, STALE_NOTICE_MINUTES + 5)
    with SessionLocal() as db:
        # The playing notice is still mid-broadcast
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == playing).one()
        item.played_at = _utc_now()
        item.duration_seconds = 600
        db.commit()
    _daemon_pass()
    assert _status(playing) == "Playing"
    assert _status(waiting) in ("Next in Queue", "Queued"), "a long queue is not a stale one"


def test_an_emergency_notice_is_never_expired():
    nid = _publish("Fire drill alert", priority="High", emergency_level="Emergency")
    _action(nid, "pause")
    _age(nid, STALE_NOTICE_MINUTES + 5)
    _daemon_pass()
    assert _status(nid) != "Failed"
