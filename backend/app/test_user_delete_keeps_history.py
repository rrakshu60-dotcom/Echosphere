"""Deleting an account removes it but keeps its history: audit entries keep the id, name, role and
department, and announcements keep their author."""
import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.core.enums.announcement import AnnouncementPriority, AnnouncementStatus, EmergencyLevel
from app.core.password import hash_password
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement import Announcement
from app.models.announcement_category import AnnouncementCategory
from app.models.audit_log import AuditLog
from app.models.department import Department
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User
from app.repositories.audit_log_repository import create_audit_log

client = TestClient(app)


def _teacher_with_history():
    name = f"t_del_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        dept = db.query(Department).filter(Department.code == "AIML").one()
        user = User(
            full_name=f"Gone {name}", official_email=f"{name}@test.local", username=name,
            password_hash=hash_password("Pass@1234"), employee_id=name[-8:],
            role_id=db.query(Role).filter(Role.name == "Teacher").one().id, department_id=dept.id,
        )
        db.add(user)
        db.commit()
        now = datetime.utcnow()
        ann = Announcement(
            title=f"Lab notice {name}", description="Bring records.", status=AnnouncementStatus.DRAFT,
            priority=AnnouncementPriority.NORMAL, emergency_level=EmergencyLevel.NORMAL,
            created_by=user.id, category_id=db.query(AnnouncementCategory).first().id,
            created_at=now, updated_at=now,
        )
        db.add(ann)
        db.commit()
        db.add(Notification(announcement_id=ann.id, user_id=user.id, is_read=False, created_at=now, updated_at=now))
        db.commit()
        create_audit_log(db, user.id, "LOGIN", "USER", user.id, f"{user.full_name} logged in.")
        return user.id, user.full_name, dept.name, ann.id


def test_delete_keeps_audit_and_announcement_history():
    user_id, full_name, dept_name, ann_id = _teacher_with_history()

    res = client.delete(f"/api/v1/users/{user_id}", headers=bearer("ESDev01"))
    assert res.status_code == 200, res.text

    with SessionLocal() as db:
        assert db.get(User, user_id) is None
        assert db.query(Notification).filter(Notification.user_id == user_id).count() == 0

        log = db.query(AuditLog).filter(AuditLog.user_id == user_id, AuditLog.action == "LOGIN").one()
        assert (log.user_name, log.user_role, log.user_department) == (full_name, "Teacher", dept_name)

        ann = db.get(Announcement, ann_id)
        assert ann is not None and ann.created_by == user_id
        assert ann.creator_name == full_name

        removed = db.query(AuditLog).filter(AuditLog.action == "DELETE_USER", AuditLog.entity_id == user_id).one()
        assert full_name in removed.description

    items = client.get("/api/v1/audit/activity", params={"q": full_name}, headers=bearer("ESDev01")).json()["items"]
    login = next(i for i in items if i["action"] == "LOGIN")
    assert login["user_name"] == full_name and login["user_deleted"] is True
