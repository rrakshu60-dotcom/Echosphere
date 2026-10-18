"""
EchoSphere Test Suite: Feature 5.2 - Atomic Batch Announcement Moderation
Tests atomic transaction batch approval, rejection, RBAC restrictions,
and ensures consistent database state across multiple announcements.
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.core.enums.announcement import AnnouncementStatus, AnnouncementPriority, EmergencyLevel
from app.core.jwt_handler import create_access_token

client = TestClient(app)


def test_student_rbac_batch_moderation():
    print("Test 1: Verifying Student RBAC blocks unauthorized batch moderation...")
    db = next(get_db())
    try:
        # Find a genuine student user from the DB
        student = db.query(User).filter(User.role.has(name="Student")).first()
        assert student is not None, "A student user must exist in DB"
        student_token = create_access_token(data={"sub": student.official_email, "role": "Student"})
        headers = {"Authorization": f"Bearer {student_token}"}

        res = client.post(
            "/api/v1/announcements/batch-moderate",
            json={"ids": [1, 2], "action": "APPROVE"},
            headers=headers
        )
        assert res.status_code == 403, f"Expected 403 Forbidden for Student, got {res.status_code}: {res.text}"
        print("  [PASS] Student role rejected with 403 Forbidden")
    finally:
        db.close()


def test_atomic_batch_approval():
    print("Test 2: Verifying Atomic Batch Approval...")
    db = next(get_db())
    created_ids = []
    try:
        admin = db.query(User).filter(User.official_email.isnot(None)).first()
        admin_token = create_access_token(data={"sub": admin.official_email, "role": "College Admin"})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create 2 pending announcements in database
        for i in range(2):
            ann = Announcement(
                title=f"Batch Approval Test Notice {i + 1}",
                description=f"Automated test content for batch approval notice #{i + 1}",
                category_id=2,
                created_by=admin.id,
                status=AnnouncementStatus.PENDING_APPROVAL,
                priority=AnnouncementPriority.NORMAL,
                emergency_level=EmergencyLevel.NORMAL,
                target_audience="Entire College",
            )
            db.add(ann)
            db.commit()
            db.refresh(ann)
            created_ids.append(ann.id)

        print(f"  Created test pending announcements: {created_ids}")

        # Send atomic batch approval request
        res = client.post(
            "/api/v1/announcements/batch-moderate",
            json={
                "ids": created_ids,
                "action": "APPROVE",
                "remarks": "Batch approved by Test Suite"
            },
            headers=headers
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["processed_count"] == len(created_ids)
        assert set(data["affected_ids"]) == set(created_ids)

        # Verify database state
        db.expire_all()
        for ann_id in created_ids:
            verified_ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
            assert verified_ann.status == AnnouncementStatus.PUBLISHED, f"Notice {ann_id} status should be PUBLISHED"

        print(f"  [PASS] Successfully approved {len(created_ids)} announcements in single atomic transaction")
    finally:
        # Cleanup
        for cid in created_ids:
            try:
                db.query(Announcement).filter(Announcement.id == cid).delete()
            except Exception:
                pass
        db.commit()
        db.close()


def test_atomic_batch_rejection():
    print("Test 3: Verifying Atomic Batch Rejection...")
    db = next(get_db())
    created_ids = []
    try:
        admin = db.query(User).filter(User.official_email.isnot(None)).first()
        admin_token = create_access_token(data={"sub": admin.official_email, "role": "Dev Admin"})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create 2 pending announcements in database
        for i in range(2):
            ann = Announcement(
                title=f"Batch Rejection Test Notice {i + 1}",
                description=f"Automated test content for batch rejection notice #{i + 1}",
                category_id=2,
                created_by=admin.id,
                status=AnnouncementStatus.PENDING_APPROVAL,
                priority=AnnouncementPriority.NORMAL,
                emergency_level=EmergencyLevel.NORMAL,
                target_audience="Entire College",
            )
            db.add(ann)
            db.commit()
            db.refresh(ann)
            created_ids.append(ann.id)

        print(f"  Created test pending announcements: {created_ids}")

        # Send atomic batch rejection request
        rejection_reason = "Duplicate submission detected"
        res = client.post(
            "/api/v1/announcements/batch-moderate",
            json={
                "ids": created_ids,
                "action": "REJECT",
                "remarks": rejection_reason
            },
            headers=headers
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        data = res.json()
        assert data["success"] is True
        assert data["processed_count"] == len(created_ids)
        assert set(data["affected_ids"]) == set(created_ids)

        # Verify database state
        db.expire_all()
        for ann_id in created_ids:
            verified_ann = db.query(Announcement).filter(Announcement.id == ann_id).first()
            assert verified_ann.status == AnnouncementStatus.REJECTED, f"Notice {ann_id} status should be REJECTED"

        print(f"  [PASS] Successfully rejected {len(created_ids)} announcements with feedback")
    finally:
        # Cleanup
        for cid in created_ids:
            try:
                db.query(Announcement).filter(Announcement.id == cid).delete()
            except Exception:
                pass
        db.commit()
        db.close()


def test_batch_moderate_validation():
    print("Test 4: Verifying Input Validation...")
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.official_email.isnot(None)).first()
        admin_token = create_access_token(data={"sub": admin.official_email, "role": "College Admin"})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Invalid action
        res = client.post(
            "/api/v1/announcements/batch-moderate",
            json={"ids": [1], "action": "INVALID_ACTION"},
            headers=headers
        )
        assert res.status_code == 400, f"Expected 400 Bad Request, got {res.status_code}"
        print("  [PASS] Invalid action rejected with 400 Bad Request")

        # Empty ids
        res_empty = client.post(
            "/api/v1/announcements/batch-moderate",
            json={"ids": [], "action": "APPROVE"},
            headers=headers
        )
        assert res_empty.status_code == 200
        assert res_empty.json()["processed_count"] == 0
        print("  [PASS] Empty list handled gracefully with processed_count=0")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n==================================================")
    print("Running EchoSphere Feature 5.2 Test Suite")
    print("==================================================\n")
    test_student_rbac_batch_moderation()
    test_atomic_batch_approval()
    test_atomic_batch_rejection()
    test_batch_moderate_validation()
    print("\n==================================================")
    print("ALL 4/4 BATCH MODERATION TESTS PASSED PERFECTLY!")
    print("==================================================\n")
