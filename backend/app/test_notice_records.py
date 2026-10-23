"""Permanent notice records and their event timelines (owner decisions 2026-10-22, step 2)."""
import os
import time

import pytest
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement import Announcement
from app.models.announcement_category import AnnouncementCategory
from app.models.notice_record import NoticeRecord, NoticeRecordEvent
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue

client = TestClient(app)
ADMIN = bearer("ESDev01")


def _category():
    with SessionLocal() as db:
        c = db.query(AnnouncementCategory).first()
        return c.id, c.name


def _create(headers=ADMIN, **fields) -> int:
    cid, _ = _category()
    payload = {
        "title": "Library closes early",
        "description": "The central library closes at 4 PM on Friday for maintenance.",
        "category_id": cid,
        "target_audience": "Entire College",
        "deliver_push": False,
        **fields,
    }
    res = client.post("/api/v1/announcements", json=payload, headers=headers)
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _record(nid) -> NoticeRecord:
    with SessionLocal() as db:
        return db.query(NoticeRecord).filter(NoticeRecord.announcement_id == nid).one()


def _events(nid) -> list:
    with SessionLocal() as db:
        rows = (db.query(NoticeRecordEvent).filter(NoticeRecordEvent.announcement_id == nid)
                .order_by(NoticeRecordEvent.id).all())
        return [(e.event, e.actor_name, e.detail) for e in rows]


def _event_names(nid) -> list:
    return [e[0] for e in _events(nid)]


# ---------------------------------------------------------------- creation & lifecycle


def test_every_new_notice_gets_a_full_record():
    nid = _create(deliver_speaker=True, scheduled_at=None, priority="High")
    r = _record(nid)
    _, cat = _category()
    assert r.title == "Library closes early" and r.original_title == "Library closes early"
    assert r.content.startswith("The central library closes")
    assert r.original_content == r.content
    assert r.category == cat and r.priority == "High" and r.target_audience == "Entire College"
    assert r.creator_name == "Dev Administrator" or r.creator_name  # the seeded Dev Admin's name
    assert r.creator_role == "Dev Admin" and r.creator_id is not None
    assert set(r.channels.split(",")) == {"In-App Feed", "Speaker"}
    assert r.created_at is not None and r.deleted_at is None
    names = _event_names(nid)
    assert names[0] == "CREATED" and "PUBLISHED" in names
    assert _events(nid)[0][1] == r.creator_name  # who did it


def test_approval_and_rejection_are_recorded_with_remarks():
    teacher = bearer("dbitaimlt022022")
    principal = bearer("principal")
    a = _create(headers=teacher)
    b = _create(headers=teacher, title="Second notice")
    assert client.post(f"/api/v1/announcements/{a}/approve", json={"remarks": "Looks good"}, headers=principal).status_code == 200
    assert client.post(f"/api/v1/announcements/{b}/reject", json={"remarks": "Wrong date"}, headers=principal).status_code == 200

    ev_a = _events(a)
    assert [e[0] for e in ev_a][:1] == ["CREATED"]
    approved = [e for e in ev_a if e[0] == "APPROVED"][0]
    assert approved[1] and "Looks good" in approved[2]
    assert "PUBLISHED" in [e[0] for e in ev_a]
    rejected = [e for e in _events(b) if e[0] == "REJECTED"][0]
    assert "Wrong date" in rejected[2]
    assert _record(b).status == "Rejected"


def test_edits_keep_the_previous_title_and_content():
    nid = _create()
    res = client.put(f"/api/v1/announcements/{nid}", json={"title": "Library closes at 5 PM", "description": "New time: 5 PM on Friday."}, headers=ADMIN)
    assert res.status_code == 200, res.text
    r = _record(nid)
    assert r.title == "Library closes at 5 PM" and r.original_title == "Library closes early"
    edited = [e for e in _events(nid) if e[0] == "EDITED"][0]
    assert "Library closes early" in edited[2] and "4 PM" in edited[2]


def test_in_app_alerts_are_recorded_with_their_count():
    with_alerts = _create(deliver_in_app=True)
    without = _create(deliver_in_app=False, deliver_speaker=True)
    alerts = [e for e in _events(with_alerts) if e[0] == "IN_APP_ALERTS"]
    assert alerts and any(ch.isdigit() for ch in alerts[0][2])
    assert "IN_APP_ALERTS" not in _event_names(without)


def test_push_attempts_are_recorded():
    nid = _create(deliver_push=True)
    assert "PUSH_SENT" in _event_names(nid)


# ---------------------------------------------------------------- speaker deliveries


def _play_on_speaker(nid, finish=True):
    with SessionLocal() as db:
        node = db.query(SpeakerNode).first()
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == nid).first()
        if item is None:
            item = SpeakerQueue(announcement_id=nid, queue_position=1, status="Queued", speaker_node_id=node.id)
            db.add(item)
            db.commit()
        item.status = "Playing"
        item.speaker_node_id = node.id
        db.commit()
        if finish:
            item.status = "Completed"
            db.commit()
        return node.name


def test_speaker_plays_are_recorded_with_the_speaker():
    nid = _create(deliver_speaker=True)
    node_name = _play_on_speaker(nid)
    events = _events(nid)
    started = [e for e in events if e[0] == "SPEAKER_STARTED"]
    finished = [e for e in events if e[0] == "SPEAKER_FINISHED"]
    assert started and finished and node_name in started[0][2]
    r = _record(nid)
    assert r.speaker_play_count == 1 and r.first_delivered_at is not None and r.last_delivered_at is not None


# ---------------------------------------------------------------- deletion


def test_deleting_before_broadcast_leaves_a_permanent_footprint():
    nid = _create(deliver_in_app=False, deliver_speaker=True, scheduled_at="2030-01-01T09:00:00")
    assert client.delete(f"/api/v1/announcements/{nid}", headers=bearer("CAdmin")).status_code == 200
    with SessionLocal() as db:
        assert db.get(Announcement, nid) is None
    r = _record(nid)
    assert r.deleted_at is not None and r.deleted_by_name and r.deleted_by_role == "College Admin"
    assert r.deleted_before_broadcast is True
    assert r.content.startswith("The central library")  # content survives the deletion
    assert r.scheduled_at is not None
    assert _event_names(nid)[-1] in ("DELETED", "AUDIO_DELETED")


def test_deleting_after_broadcast_is_marked_so():
    nid = _create(deliver_speaker=True)
    _play_on_speaker(nid)
    client.delete(f"/api/v1/announcements/{nid}", headers=ADMIN)
    assert _record(nid).deleted_before_broadcast is False


def test_delete_is_refused_if_the_record_cannot_be_written(monkeypatch):
    nid = _create()
    import app.services.notice_record_service as records

    def broken(*args, **kwargs):
        raise RuntimeError("record store unavailable")

    monkeypatch.setattr(records, "_record_deletion", broken)
    local = TestClient(app, raise_server_exceptions=False)
    res = local.delete(f"/api/v1/announcements/{nid}", headers=ADMIN)
    assert res.status_code >= 500
    with SessionLocal() as db:
        assert db.get(Announcement, nid) is not None


def test_deleting_a_notice_deletes_its_audio_after_the_record(monkeypatch, tmp_path):
    import app.services.notice_record_service as records
    import app.services.tts_service as tts

    monkeypatch.setattr(tts, "STATIC_AUDIO_DIR", str(tmp_path))
    cloud_calls = []
    monkeypatch.setattr(records, "_delete_cloud_audio", lambda nid: cloud_calls.append(nid) or 2)

    nid = _create()
    other = nid + 1000
    for name in (f"announcement_{nid}_en_female.wav", f"announcement_{nid}_en_female_nochime.wav",
                 f"announcement_{nid}.mp3", f"announcement_{other}_en_female.wav"):
        (tmp_path / name).write_bytes(b"RIFF")

    client.delete(f"/api/v1/announcements/{nid}", headers=ADMIN)
    deadline = time.time() + 5
    while time.time() < deadline and "AUDIO_DELETED" not in _event_names(nid):
        time.sleep(0.05)
    assert "AUDIO_DELETED" in _event_names(nid)
    def mine():
        return [f for f in os.listdir(tmp_path) if f.startswith(f"announcement_{nid}_") or f.startswith(f"announcement_{nid}.")]

    # The notice's own speech job may still be running; once it finishes it must discard its audio too
    deadline = time.time() + 10
    while mine() and time.time() < deadline:
        time.sleep(0.05)
    assert not mine()
    left = os.listdir(tmp_path)  # background speech jobs from other tests may add their own files here
    assert f"announcement_{other}_en_female.wav" in left  # other notices' audio is untouched
    assert cloud_calls == [nid]
    assert _record(nid).audio_deleted_at is not None
    names = _event_names(nid)
    assert names.index("DELETED") < names.index("AUDIO_DELETED")


# ---------------------------------------------------------------- admin API


def test_only_dev_admin_and_college_admin_can_read_notice_records():
    nid = _create()
    for path in ("/api/v1/audit/notices", f"/api/v1/audit/notices/{nid}"):
        assert client.get(path, headers=bearer("principal")).status_code == 403
        assert client.get(path).status_code == 401
        assert client.get(path, headers=bearer("CAdmin")).status_code == 200


def test_notice_record_search_filters_sorting_and_detail():
    keep = _create(title="Seminar on quantum computing", description="Hall B, Monday 10 AM.")
    gone = _create(title="Seminar on robotics", description="Hall C, Tuesday 2 PM.", deliver_speaker=True)
    client.delete(f"/api/v1/announcements/{gone}", headers=ADMIN)

    def search(**params):
        res = client.get("/api/v1/audit/notices", params=params, headers=ADMIN)
        assert res.status_code == 200, res.text
        return res.json()

    assert {i["announcement_id"] for i in search(q="Seminar on")["items"]} >= {keep, gone}
    assert [i["announcement_id"] for i in search(q=str(keep))["items"]][:1] == [keep]  # by notice ID
    assert any(i["announcement_id"] == keep for i in search(q="Hall B")["items"])  # by content
    deleted = search(q="Seminar on", state="deleted")["items"]
    assert [i["announcement_id"] for i in deleted] == [gone]
    assert all(i["announcement_id"] != keep for i in search(state="deleted")["items"])
    assert gone in [i["announcement_id"] for i in search(channel="Speaker", q="robotics")["items"]]
    oldest = search(q="Seminar on", sort="created", order="asc")["items"]
    assert [i["announcement_id"] for i in oldest][:2] == [keep, gone]
    page = search(q="Seminar on", page_size=1)
    assert page["total"] >= 2 and len(page["items"]) == 1

    detail = client.get(f"/api/v1/audit/notices/{gone}", headers=ADMIN).json()
    assert detail["record"]["title"] == "Seminar on robotics" and detail["record"]["deleted_at"]
    assert [e["event"] for e in detail["events"]][0] == "CREATED"
    assert client.get("/api/v1/audit/notices/987654321", headers=ADMIN).status_code == 404


def test_audio_generated_after_deletion_is_discarded(monkeypatch, tmp_path):
    # A notice's speech job can finish after the notice was deleted; its audio must not survive.
    import app.services.notice_record_service as records
    import app.services.tts_service as tts

    monkeypatch.setattr(tts, "STATIC_AUDIO_DIR", str(tmp_path))
    monkeypatch.setattr(records, "_delete_cloud_audio", lambda nid: 0)
    nid = _create()
    client.delete(f"/api/v1/announcements/{nid}", headers=ADMIN)

    def slow_synthesis(announcement_id, text, **kwargs):  # finishes after the delete
        (tmp_path / f"announcement_{announcement_id}_american_female_nochime.wav").write_bytes(b"RIFF")
        return {"status": "ok"}

    monkeypatch.setattr(tts, "_generate_announcement_audio", slow_synthesis)
    tts.generate_announcement_audio_sync(nid, "late speech")
    assert not [f for f in os.listdir(tmp_path) if f.startswith(f"announcement_{nid}_")]
    assert any(e[0] == "AUDIO_DELETED" and "after" in e[2] for e in _events(nid))


def test_backups_of_deleted_notices_are_skipped(monkeypatch, tmp_path):
    import app.services.tts_service as tts
    from app.services.cloud_storage_service import CloudStorageService

    monkeypatch.setattr(records_module(), "_delete_cloud_audio", lambda nid: 0)
    nid = _create()
    client.delete(f"/api/v1/announcements/{nid}", headers=ADMIN)
    uploads = []
    monkeypatch.setattr(CloudStorageService, "upload_file", lambda *a, **k: uploads.append(k.get("custom_filename")))
    assert tts._should_back_up(f"announcement_{nid}_american_female.wav") is False
    alive = _create()
    assert tts._should_back_up(f"announcement_{alive}_american_female.wav") is True
    assert tts._should_back_up("chime_soft.wav") is True


def records_module():
    import app.services.notice_record_service as records

    return records


def test_cleanup_removes_audio_of_notices_deleted_before_the_record_system(monkeypatch, tmp_path):
    import app.services.notice_record_service as records
    import app.services.tts_service as tts
    from app.services.cloud_storage_service import CloudStorageService

    import threading
    # Let audio deletions started by earlier tests finish, or the clean-up below also picks up their notices
    for t in threading.enumerate():
        if t.name.startswith("NoticeAudioDelete-"):
            t.join(timeout=10)
    monkeypatch.setattr(tts, "STATIC_AUDIO_DIR", str(tmp_path))
    with SessionLocal() as db:
        # two notices deleted in the past (records exist, audio never removed), one live notice, one already cleaned
        db.add_all([
            NoticeRecord(announcement_id=880001, title="Old A", deleted_at=records._now(), partial=True, speaker_play_count=0),
            NoticeRecord(announcement_id=880002, title="Old B", deleted_at=records._now(), partial=True, speaker_play_count=0),
            NoticeRecord(announcement_id=880003, title="Live", speaker_play_count=0),
            NoticeRecord(announcement_id=880004, title="Done", deleted_at=records._now(), audio_deleted_at=records._now(), speaker_play_count=0),
        ])
        db.commit()
    for nid in (880001, 880002, 880003):
        (tmp_path / f"announcement_{nid}_american_female_nochime.wav").write_bytes(b"RIFF")

    calls = []
    monkeypatch.setattr(CloudStorageService, "delete_audio_for_notices",
                        classmethod(lambda cls, ids: calls.append(sorted(ids)) or {i: 2 for i in ids}))
    cleaned = records.purge_audio_of_deleted_notices(SessionLocal)

    assert sorted(cleaned) == [880001, 880002]
    assert calls == [[880001, 880002]]  # one cloud commit for all of them
    assert sorted(os.listdir(tmp_path)) == ["announcement_880003_american_female_nochime.wav"]
    for nid in (880001, 880002):
        assert _record(nid).audio_deleted_at is not None
        assert any(e[0] == "AUDIO_DELETED" and "2 cloud" in e[2] for e in _events(nid))
    assert _record(880003).audio_deleted_at is None
    assert records.purge_audio_of_deleted_notices(SessionLocal) == []  # nothing left to do


def test_cleanup_retries_later_if_the_backup_cannot_be_reached(monkeypatch, tmp_path):
    import app.services.notice_record_service as records
    import app.services.tts_service as tts
    from app.services.cloud_storage_service import CloudStorageService

    monkeypatch.setattr(tts, "STATIC_AUDIO_DIR", str(tmp_path))
    with SessionLocal() as db:
        db.add(NoticeRecord(announcement_id=880010, title="Old", deleted_at=records._now(), partial=True, speaker_play_count=0))
        db.commit()

    def unreachable(cls, ids):
        raise ConnectionError("backup unreachable")

    monkeypatch.setattr(CloudStorageService, "delete_audio_for_notices", classmethod(unreachable))
    assert records.purge_audio_of_deleted_notices(SessionLocal) == []
    assert _record(880010).audio_deleted_at is None
