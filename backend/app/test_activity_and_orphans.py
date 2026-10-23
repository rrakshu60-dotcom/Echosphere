"""Paged Activity trail for admins, and clean-up of audio backups that belong to no notice at all."""
import os
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.audit_log import AuditLog
from app.models.notice_record import NoticeRecord
from app.models.user import User

client = TestClient(app)
ADMIN = bearer("ESDev01")


def _seed_activity():
    with SessionLocal() as db:
        teacher = db.query(User).filter(User.username == "dbitaimlt022022").one()
        admin = db.query(User).filter(User.username == "ESDev01").one()
        base = datetime(2026, 1, 10, 9, 0, 0)
        db.add_all([
            AuditLog(user_id=teacher.id, action="CREATE_ANNOUNCEMENT", entity="ANNOUNCEMENT", entity_id=7001,
                     description="Created announcement: Orbit lab timetable", created_at=base, updated_at=base),
            AuditLog(user_id=admin.id, action="DELETE_ANNOUNCEMENT", entity="ANNOUNCEMENT", entity_id=7001,
                     description="Deleted announcement: Orbit lab timetable", created_at=base + timedelta(hours=1),
                     updated_at=base + timedelta(hours=1)),
            AuditLog(user_id=admin.id, action="END_SESSION", entity="SESSION", entity_id=91,
                     description="Dev Admin signed out session #91 of Orbit Tester.", created_at=base + timedelta(hours=2),
                     updated_at=base + timedelta(hours=2)),
        ])
        db.commit()
        return teacher.full_name, admin.full_name


def _activity(**params):
    res = client.get("/api/v1/audit/activity", params=params, headers=ADMIN)
    assert res.status_code == 200, res.text
    return res.json()


def test_activity_is_admin_only():
    assert client.get("/api/v1/audit/activity", headers=bearer("principal")).status_code == 403
    assert client.get("/api/v1/audit/activity").status_code == 401
    assert client.get("/api/v1/audit/activity", headers=bearer("CAdmin")).status_code == 200


def test_activity_search_filter_sort_and_pages():
    teacher_name, admin_name = _seed_activity()

    found = _activity(q="Orbit")
    assert found["total"] == 3
    assert [i["action"] for i in found["items"]] == ["END_SESSION", "DELETE_ANNOUNCEMENT", "CREATE_ANNOUNCEMENT"]

    oldest = _activity(q="Orbit", order="asc")
    assert oldest["items"][0]["action"] == "CREATE_ANNOUNCEMENT"
    assert oldest["items"][0]["user_name"] == teacher_name  # who did it, by name

    deleted = _activity(q="Orbit", action="DELETE_ANNOUNCEMENT")
    assert deleted["total"] == 1 and deleted["items"][0]["user_name"] == admin_name

    by_notice = _activity(q="7001")  # a notice ID finds its entries
    assert by_notice["total"] == 2
    by_user = _activity(q=teacher_name)  # so does the person's name
    assert any(i["entity_id"] == 7001 for i in by_user["items"])

    dated = _activity(q="Orbit", **{"from": "2026-01-10T09:30:00", "to": "2026-01-10T10:30:00"})
    assert [i["action"] for i in dated["items"]] == ["DELETE_ANNOUNCEMENT"]

    page = _activity(q="Orbit", page_size=2, page=2)
    assert page["total"] == 3 and len(page["items"]) == 1 and page["page"] == 2

    by_action = _activity(q="Orbit", sort="action", order="asc")
    assert [i["action"] for i in by_action["items"]] == ["CREATE_ANNOUNCEMENT", "DELETE_ANNOUNCEMENT", "END_SESSION"]


# ---------------------------------------------------------------- orphaned audio backups


def test_orphaned_audio_is_removed_but_audio_of_real_notices_is_kept(monkeypatch, tmp_path):
    import app.services.notice_record_service as records
    import app.services.tts_service as tts
    from app.services.cloud_storage_service import CloudStorageService

    monkeypatch.setattr(tts, "STATIC_AUDIO_DIR", str(tmp_path))
    with SessionLocal() as db:
        db.add(NoticeRecord(announcement_id=660001, title="Has a record", deleted_at=records._now(),
                            audio_deleted_at=records._now(), speaker_play_count=0))
        db.commit()
    # 660001: deleted notice with a record (kept: its audio is the record's business, not an orphan)
    # 660002 / 99999: no notice and no record anywhere -> orphans
    for nid in (660001, 660002, 99999):
        (tmp_path / f"announcement_{nid}_american_female.wav").write_bytes(b"RIFF")

    monkeypatch.setattr(CloudStorageService, "list_notice_audio_ids", classmethod(lambda cls: {660001, 660002, 99999}))
    deleted_batches = []
    monkeypatch.setattr(CloudStorageService, "delete_audio_for_notices",
                        classmethod(lambda cls, ids: deleted_batches.append(sorted(ids)) or {i: 1 for i in ids}))

    removed = records.purge_orphaned_audio(SessionLocal)

    assert sorted(removed) == [99999, 660002]
    assert deleted_batches == [[99999, 660002]]
    assert sorted(os.listdir(tmp_path)) == ["announcement_660001_american_female.wav"]


def test_orphan_cleanup_never_touches_existing_notices(monkeypatch):
    import app.services.notice_record_service as records
    from app.services.cloud_storage_service import CloudStorageService

    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Real notice", "description": "Still live.", "category_id": 1,
        "target_audience": "Entire College", "deliver_push": False})
    live_id = res.json()["id"]
    monkeypatch.setattr(CloudStorageService, "list_notice_audio_ids", classmethod(lambda cls: {live_id}))
    monkeypatch.setattr(CloudStorageService, "delete_audio_for_notices",
                        classmethod(lambda cls, ids: (_ for _ in ()).throw(AssertionError(f"tried to delete {ids}"))))
    assert records.purge_orphaned_audio(SessionLocal) == []
