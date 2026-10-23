"""
Repeat schedules keep rotating on their own: inside a custom window the notice plays again after the normal gap until
the window ends or its round cap is reached, then waits for the next day's window. Each round is counted once.
Driven as on the live system: the app publishes and sets the schedule, the speaker reports each round finished,
and the queue daemon runs its pass after every change.
"""
from datetime import datetime, timedelta, timezone

import pytest

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule, RepeatSlotExecutionLog
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue

client = TestClient(app)
ADMIN = bearer("ESDev01")
IST = timedelta(hours=5, minutes=30)
ACTIVE = ("Playing", "Next in Queue", "Queued")


@pytest.fixture(autouse=True)
def _empty_speaker_queue():
    """Each test starts with an idle speaker, whatever an earlier test left behind."""
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


def _set_schedule(nid, **fields):
    now = datetime.now(timezone.utc)
    payload = {  # as the app's repeat dialog sends it
        "is_active": True, "target_scope": "COLLEGE_WIDE", "force_enable_speaker": True,
        "start_date": (now - timedelta(minutes=5)).isoformat(), "end_date": (now + timedelta(hours=48)).isoformat(),
        **fields,
    }
    res = client.put(f"/api/v1/announcements/{nid}/repeat-schedule", headers=ADMIN, json=payload)
    assert res.status_code == 200, res.text
    _daemon_pass()


def _daemon_pass():
    """One pass of the live queue daemon (main.py)."""
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    from app.services.repeat_schedule_service import evaluate_and_dispatch_repeat_slots
    with SessionLocal() as db:
        auto_advance_speaker_queue(db)
        evaluate_and_dispatch_repeat_slots(db)


def _active(nid):
    with SessionLocal() as db:
        return db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid, SpeakerQueue.status.in_(ACTIVE)).all()


def _sched(nid):
    with SessionLocal() as db:
        return db.query(AnnouncementRepeatSchedule).filter(AnnouncementRepeatSchedule.announcement_id == nid).one()


def _finish_round(nid):
    """The speaker reports the playing round finished, then the daemon reacts."""
    items = _active(nid)
    assert len(items) == 1 and items[0].status == "Playing", [(i.id, i.status) for i in items]
    res = client.post(f"/api/v1/hardware/queue/{items[0].id}/action?action=complete")
    assert res.status_code == 200, res.text
    _daemon_pass()


def _let_gap_pass(nid):
    """Instead of sleeping through the gap: make the waiting round due now, then the daemon reacts."""
    with SessionLocal() as db:
        for q in db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid, SpeakerQueue.status.in_(ACTIVE)):
            q.scheduled_time = _utc_now() - timedelta(seconds=1)
        s = db.query(AnnouncementRepeatSchedule).filter(AnnouncementRepeatSchedule.announcement_id == nid).one()
        if s.next_repeat_at:
            s.next_repeat_at = _utc_now() - timedelta(seconds=1)
        db.commit()
    _daemon_pass()


def _open_window():
    ist = _utc_now() + IST
    return (ist - timedelta(minutes=2)).strftime("%H:%M"), (ist + timedelta(minutes=20)).strftime("%H:%M")


def test_custom_window_keeps_rotating_until_its_cap_then_waits_for_tomorrow():
    start, end = _open_window()
    nid = _publish("Exam hall change")
    _set_schedule(nid, repeat_mode="BREAK_SLOTS", interval_minutes=0, max_repeats=6, play_on_publish=False,
                  selected_slots=["CUSTOM_WINDOW"], custom_start_time=start, custom_end_time=end)
    cap = _sched(nid).max_repeats

    for round_no in range(1, cap + 1):
        items = _active(nid)
        assert len(items) == 1 and items[0].status == "Playing", f"round {round_no} did not start: {[(i.status) for i in items]}"
        _finish_round(nid)
        assert _sched(nid).total_played_count == round_no, "each round must be counted exactly once"
        waiting = _active(nid)
        assert len(waiting) <= 1, "the notice must never be in the queue twice"
        if round_no < cap:
            assert waiting and waiting[0].scheduled_time <= _utc_now() + timedelta(seconds=10), \
                f"after round {round_no} the next round must follow within the window, not {waiting and waiting[0].scheduled_time}"
            _let_gap_pass(nid)

    with SessionLocal() as db:
        keys = [k for (k,) in db.query(RepeatSlotExecutionLog.slot_key).filter(RepeatSlotExecutionLog.schedule_id == _sched(nid).id)]
    assert len(keys) == cap and len(set(keys)) == cap, keys

    # Cap reached: nothing more today; the next round (if any) is tomorrow's window
    waiting = _active(nid)
    assert all(q.scheduled_time > _utc_now() + timedelta(hours=12) for q in waiting), [q.scheduled_time for q in waiting]
    _daemon_pass()
    assert not [q for q in _active(nid) if q.status == "Playing"]


def test_publish_play_counts_once_and_the_window_starts_on_time():
    ist = _utc_now() + IST
    start = (ist + timedelta(minutes=3)).strftime("%H:%M")
    end = (ist + timedelta(minutes=10)).strftime("%H:%M")
    nid = _publish("Library notice")
    _set_schedule(nid, repeat_mode="BREAK_SLOTS", interval_minutes=0, max_repeats=6, play_on_publish=True,
                  selected_slots=["CUSTOM_WINDOW"], custom_start_time=start, custom_end_time=end)
    _finish_round(nid)  # the play on publish
    assert _sched(nid).total_played_count == 1
    waiting = _active(nid)
    assert len(waiting) == 1 and waiting[0].status == "Queued"
    window_start_utc = datetime.strptime(f"{ist:%Y-%m-%d} {start}", "%Y-%m-%d %H:%M") - IST
    assert abs((waiting[0].scheduled_time - window_start_utc).total_seconds()) < 60, waiting[0].scheduled_time


def test_interval_rounds_are_counted_once_each():
    nid = _publish("Bus timing")
    _set_schedule(nid, repeat_mode="INTERVAL", interval_minutes=1, max_repeats=3, play_on_publish=True,
                  selected_slots=["INTERVAL"])
    for round_no in range(1, 4):
        if round_no > 1:
            _let_gap_pass(nid)
        _finish_round(nid)
        assert _sched(nid).total_played_count == round_no
    assert not _active(nid) and _sched(nid).is_active is False


def test_interval_schedule_sent_without_slots_stays_an_interval():
    nid = _publish("Canteen notice")
    _set_schedule(nid, repeat_mode="INTERVAL", interval_minutes=1, max_repeats=2, play_on_publish=True)
    assert _sched(nid).repeat_mode == "INTERVAL", "the default break slot must not turn an interval into a daily break"
    _finish_round(nid)
    waiting = _active(nid)
    assert len(waiting) == 1 and waiting[0].scheduled_time <= _utc_now() + timedelta(minutes=1, seconds=5), \
        [q.scheduled_time for q in waiting]
