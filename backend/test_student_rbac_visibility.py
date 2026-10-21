"""
test_student_rbac_visibility.py
Verifies strict RBAC enforcement ensuring Student roles cannot access or trigger
administrative, speaker, moderation, user management, or VIP protocol endpoints.
"""

import sys
from fastapi.testclient import TestClient
from app.main import app
from app.core.jwt_handler import create_access_token

client = TestClient(app)

STUDENT_TOKEN = create_access_token({"sub": "1db23ci079"})
ADMIN_TOKEN = create_access_token({"sub": "CAdmin"})
DEV_TOKEN = create_access_token({"sub": "ESDev01"})


def test_student_blocked_from_approval_queue():
    """Verify students receive HTTP 403 when trying to fetch the approval queue."""
    resp = client.get(
        "/api/v1/announcements/approval-queue",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
    )
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
    print("PASS: Student strictly blocked from approval queue (403)")


def test_student_blocked_from_user_management():
    """Verify students receive HTTP 403 when trying to list users or inspect user profiles."""
    resp_list = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
    )
    assert resp_list.status_code == 403, f"Expected 403 for list users, got {resp_list.status_code}"

    resp_detail = client.get(
        "/api/v1/users/1",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
    )
    assert resp_detail.status_code == 403, f"Expected 403 for user detail, got {resp_detail.status_code}"
    print("PASS: Student strictly blocked from user management directory (403)")


def test_student_blocked_from_hardware_speakers():
    """Verify students receive HTTP 403 when trying to enqueue, broadcast, or override speakers."""
    # 1. Broadcast to node
    resp_bc = client.post(
        "/api/v1/hardware/speakers/1/broadcast",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
        json={"announcement_id": 1},
    )
    assert resp_bc.status_code == 403, f"Expected 403 for speaker broadcast, got {resp_bc.status_code}: {resp_bc.text}"

    # 2. Emergency override
    resp_ov = client.post(
        "/api/v1/hardware/speakers/override",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
        json={"message": "Unauthorized emergency announcement", "title": "Test"},
    )
    assert resp_ov.status_code == 403, f"Expected 403 for emergency override, got {resp_ov.status_code}: {resp_ov.text}"

    # 3. Enqueue to speaker
    resp_enq = client.post(
        "/api/v1/hardware/queue/add",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
        json={"announcement_id": 1},
    )
    assert resp_enq.status_code == 403, f"Expected 403 for queue add, got {resp_enq.status_code}: {resp_enq.text}"
    print("PASS: Student strictly blocked from smart speaker PA system and playback queue (403)")


def test_student_blocked_from_repeat_schedule_configuration():
    """Verify students receive HTTP 403 when attempting to configure or delete repeat schedules."""
    resp_set = client.put(
        "/api/v1/announcements/1/repeat-schedule",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
        json={
            "repeat_mode": "BREAK_SLOTS",
            "selected_slots": ["SHORT_BREAK"],
            "target_scope": "COLLEGE_WIDE",
        },
    )
    assert resp_set.status_code == 403, f"Expected 403 for set repeat schedule, got {resp_set.status_code}: {resp_set.text}"

    resp_del = client.delete(
        "/api/v1/announcements/1/repeat-schedule",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
    )
    assert resp_del.status_code == 403, f"Expected 403 for delete repeat schedule, got {resp_del.status_code}: {resp_del.text}"
    print("PASS: Student strictly blocked from repeat schedule creation and deletion (403)")


def test_student_blocked_from_vip_protocol():
    """Verify students receive HTTP 403 when attempting to analyze or trigger VIP fanfare."""
    resp_an = client.post(
        "/api/v1/announcements/1/vip-protocol/analyze",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
    )
    assert resp_an.status_code == 403, f"Expected 403 for VIP analysis, got {resp_an.status_code}: {resp_an.text}"

    resp_arr = client.post(
        "/api/v1/announcements/1/vip-protocol/arrival",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"},
        json={"target_zone": "Auditorium"},
    )
    assert resp_arr.status_code == 403, f"Expected 403 for VIP arrival fanfare, got {resp_arr.status_code}: {resp_arr.text}"
    print("PASS: Student strictly blocked from VIP dignitary analysis and fanfare triggers (403)")


def test_admin_allowed_access():
    """Verify administrative roles retain legitimate access to user management and hardware."""
    resp = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
    )
    assert resp.status_code == 200, f"Expected 200 for admin user list, got {resp.status_code}: {resp.text}"
    print("PASS: Admin role has full authorized access to administrative endpoints")


if __name__ == "__main__":
    print("--- RUNNING STUDENT RBAC ENFORCEMENT TEST SUITE ---")
    test_student_blocked_from_approval_queue()
    test_student_blocked_from_user_management()
    test_student_blocked_from_hardware_speakers()
    test_student_blocked_from_repeat_schedule_configuration()
    test_student_blocked_from_vip_protocol()
    test_admin_allowed_access()
    print("--- ALL 6 RBAC ENFORCEMENT TESTS PASSED PERFECTLY ---")
