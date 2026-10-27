"""Security fixes: login on formerly open endpoints, user-management hierarchy, no HoD self-approval."""
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.core.enums.announcement import AnnouncementStatus
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement import Announcement
from app.models.user import User

client = TestClient(app)
DEV = bearer("ESDev01")
CADMIN = bearer("CAdmin")
PRINCIPAL = bearer("principal")
HOD = bearer("hod_aiml")
STUDENT = bearer("1db23ci079")


def _user_id(username: str) -> int:
    with SessionLocal() as db:
        return db.query(User).filter(User.username == username).one().id


def _pending_notice(creator: str, title: str) -> int:
    with SessionLocal() as db:
        notice = Announcement(
            title=title,
            description=f"{title} - details for the department.",
            status=AnnouncementStatus.PENDING_APPROVAL,
            target_audience="AIML Department",
            category_id=1,
            created_by=db.query(User).filter(User.username == creator).one().id,
        )
        db.add(notice)
        db.commit()
        return notice.id


# --- 1. Login checks ---

def test_formerly_open_endpoints_refuse_anonymous_callers():
    assert client.post("/api/v1/hardware/speakers/1/control", json={"command": "PAUSE"}).status_code == 401
    assert client.get("/api/v1/announcements/").status_code == 401
    assert client.get("/api/v1/announcements").status_code == 401
    assert client.post("/api/v1/ai/chat", json={"prompt": "hello"}).status_code == 401
    assert client.get("/api/v1/ai/status").status_code == 401
    assert client.get("/api/v1/diagnostic/tts").status_code == 401
    assert client.get("/api/v1/hardware/queue").status_code == 401
    assert client.get("/api/v1/hardware/speakers").status_code == 401


def test_students_cannot_control_speakers_or_run_diagnostics():
    assert client.post("/api/v1/hardware/speakers/1/control", headers=STUDENT, json={"command": "PAUSE"}).status_code == 403
    assert client.get("/api/v1/diagnostic/tts", headers=STUDENT).status_code == 403
    assert client.get("/api/v1/diagnostic/tts", headers=HOD).status_code == 403
    assert client.post("/api/v1/announcements/voice-to-notice", headers=STUDENT, json={"raw_transcript": "x"}).status_code == 403


def test_student_only_sees_published_notices_whatever_status_is_asked_for():
    pending_id = _pending_notice("dbitaimlt022022", "Lab timetable draft for review")
    for path in ("/api/v1/announcements/", "/api/v1/announcements/?status=Pending%20Approval"):
        res = client.get(path, headers=STUDENT)
        assert res.status_code == 200, res.text
        assert all(n["status"] == "Published" for n in res.json()), res.json()
        assert pending_id not in [n["id"] for n in res.json()]
    staff = client.get("/api/v1/announcements/?status=Pending%20Approval", headers=PRINCIPAL)
    assert pending_id in [n["id"] for n in staff.json()]


def test_students_see_speaker_names_but_not_device_addresses():
    client.post("/api/v1/hardware/speakers/register", headers=DEV,
                json={"name": "Security Test Speaker", "mac_address": "AA:BB:CC:00:11:22"})
    student_view = client.get("/api/v1/hardware/speakers", headers=STUDENT)
    assert student_view.status_code == 200, student_view.text
    node = next(n for n in student_view.json() if n["name"] == "Security Test Speaker")
    assert node["mac_address"] == "" and node["ip_address"] is None
    staff_view = client.get("/api/v1/hardware/speakers", headers=DEV).json()
    assert any(n["mac_address"] == "AA:BB:CC:00:11:22" for n in staff_view)


def test_ai_chat_uses_the_signed_in_identity_not_the_request_body():
    res = client.post("/api/v1/ai/chat", headers=STUDENT, json={
        "prompt": "who am i", "user_role": "Dev Admin", "full_name": "Somebody Else", "user_id": 1, "usn_or_emp_id": "ESDev01"})
    assert res.status_code == 200, res.text
    assert "Rakshitha S" in res.json()["response"]
    assert "Somebody Else" not in res.json()["response"]


def test_direct_password_reset_gives_one_answer_for_unknown_user_and_wrong_password():
    unknown = client.post("/api/v1/auth/reset-password-direct",
                          json={"identifier": "no-such-user", "current_password": "x", "new_password": "y12345678"})
    wrong = client.post("/api/v1/auth/reset-password-direct",
                        json={"identifier": "1db23ci079", "current_password": "wrong", "new_password": "y12345678"})
    wildcard = client.post("/api/v1/auth/reset-password-direct",
                           json={"identifier": "1db23ci0%", "current_password": "unit-test-1db23ci079", "new_password": "y12345678"})
    assert unknown.status_code == wrong.status_code == wildcard.status_code == 400
    assert unknown.json()["detail"] == wrong.json()["detail"] == wildcard.json()["detail"] == "Invalid credentials."


# --- 2. User-management hierarchy ---

def _new_user(headers, role: str, tag: str):
    return client.post("/api/v1/users/", headers=headers, json={
        "full_name": f"Hierarchy {tag}", "official_email": f"hierarchy.{tag}@echosphere.edu",
        "password": "Password@123", "role_name": role, "employee_id": f"EMP_HIER_{tag.upper()}"})


def test_principal_cannot_create_or_promote_to_dev_admin_or_change_own_role():
    assert _new_user(PRINCIPAL, "Dev Admin", "p1").status_code == 403
    assert _new_user(PRINCIPAL, "Principal", "p2").status_code == 403
    teacher = _new_user(PRINCIPAL, "Teacher", "p3")
    assert teacher.status_code == 201, teacher.text
    teacher_id = teacher.json()["id"]
    assert client.put(f"/api/v1/users/{teacher_id}", headers=PRINCIPAL, json={"role_name": "Dev Admin"}).status_code == 403
    assert client.put(f"/api/v1/users/{teacher_id}", headers=PRINCIPAL, json={"role_name": "HoD"}).status_code == 200

    me = _user_id("principal")
    assert client.put(f"/api/v1/users/{me}", headers=PRINCIPAL, json={"role_name": "Dev Admin"}).status_code == 403
    assert client.put(f"/api/v1/users/{me}", headers=PRINCIPAL, json={"is_active": False}).status_code == 403
    assert client.delete(f"/api/v1/users/{me}", headers=PRINCIPAL).status_code == 403


def test_college_admin_cannot_edit_or_delete_a_principal_but_dev_admin_can():
    principal_id = _user_id("principal")
    assert client.put(f"/api/v1/users/{principal_id}", headers=CADMIN, json={"is_active": False}).status_code == 403
    assert client.delete(f"/api/v1/users/{principal_id}", headers=CADMIN).status_code == 403
    res = client.put(f"/api/v1/users/{principal_id}", headers=DEV, json={"role_name": "Principal"})
    assert res.status_code == 200, res.text
    assert res.json()["role"] == "Principal"


def test_dev_admin_can_create_a_dev_admin_but_not_demote_themself():
    created = _new_user(DEV, "Dev Admin", "d1")
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "Dev Admin"
    me = _user_id("ESDev01")
    assert client.put(f"/api/v1/users/{me}", headers=DEV, json={"role_name": "Student"}).status_code == 403


# --- 3. HoD self-approval ---

def test_hod_cannot_approve_own_notice_but_can_approve_a_teachers_from_same_department():
    own = _pending_notice("hod_aiml", "HoD office hours change")
    res = client.post(f"/api/v1/announcements/{own}/approve", headers=HOD, json={})
    assert res.status_code == 403
    assert "cannot approve your own notice" in res.json()["detail"]

    batch = client.post("/api/v1/announcements/batch-moderate", headers=HOD, json={"ids": [own], "action": "APPROVE"})
    assert batch.status_code == 200, batch.text
    assert own in batch.json()["failed_ids"]

    teachers = _pending_notice("dbitaimlt022022", "AIML lab session moved")
    res = client.post(f"/api/v1/announcements/{teachers}/approve", headers=HOD, json={})
    assert res.status_code == 200, res.text

    # Principal can still approve the HoD's notice.
    assert client.post(f"/api/v1/announcements/{own}/approve", headers=PRINCIPAL, json={}).status_code == 200


def test_hod_cannot_approve_a_notice_whose_creator_has_no_department():
    no_dept = _pending_notice("CAdmin", "Admin office notice")
    res = client.post(f"/api/v1/announcements/{no_dept}/approve", headers=HOD, json={})
    assert res.status_code == 403
