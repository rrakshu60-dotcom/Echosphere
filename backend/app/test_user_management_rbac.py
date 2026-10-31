"""User directory: every staff role sees all accounts; changes follow the role and department rules."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.core.password import hash_password
from app.db.database import SessionLocal
from app.main import app
from app.models.department import Department
from app.models.role import Role
from app.models.user import User

client = TestClient(app)


def _dept(code):
    with SessionLocal() as db:
        return db.query(Department).filter(Department.code == code).one().id


def _make_user(role, dept_code=None):
    name = f"t_{role.replace(' ', '').lower()}_{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        user = User(
            full_name=name,
            official_email=f"{name}@test.local",
            username=name,
            password_hash=hash_password("Pass@1234"),
            role_id=db.query(Role).filter(Role.name == role).one().id,
            department_id=_dept(dept_code) if dept_code else None,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, name


def _create(caller, role, dept_code=None):
    name = f"new_{uuid.uuid4().hex[:8]}"
    body = {"full_name": name, "official_email": f"{name}@test.local", "password": "Pass@1234", "role_name": role}
    if dept_code:
        body["department_id"] = _dept(dept_code)
    return client.post("/api/v1/users/", json=body, headers=bearer(caller))


@pytest.mark.parametrize("role,dept", [("Teacher", "AIML"), ("HoD", None), ("Principal", None)])
def test_every_staff_role_sees_all_accounts(role, dept):
    _, caller = _make_user(role, dept)
    _make_user("Teacher", "CSE")
    res = client.get("/api/v1/users/", headers=bearer(caller))
    assert res.status_code == 200, res.text
    roles = {u["role"] for u in res.json()}
    assert {"Dev Admin", "College Admin", "Principal", "HoD", "Teacher", "Student"} <= roles
    assert any(u["department_id"] == _dept("CSE") for u in res.json())


def test_students_cannot_open_the_directory():
    _, student = _make_user("Student", "AIML")
    assert client.get("/api/v1/users/", headers=bearer(student)).status_code == 403


@pytest.mark.parametrize(
    "caller_role,allowed,denied",
    [
        ("Principal", ["HoD", "Teacher", "Student"], ["Principal", "College Admin", "Dev Admin"]),
        ("HoD", ["Teacher", "Student"], ["HoD", "Principal", "College Admin", "Dev Admin"]),
        ("Teacher", ["Student"], ["Teacher", "HoD", "Principal", "College Admin", "Dev Admin"]),
    ],
)
def test_create_follows_role_rules(caller_role, allowed, denied):
    _, caller = _make_user(caller_role, "AIML")
    for role in allowed:
        assert _create(caller, role).status_code == 201, role
    for role in denied:
        assert _create(caller, role).status_code == 403, role


def test_hod_and_teacher_create_only_in_own_department():
    for role, new_role in (("HoD", "Teacher"), ("Teacher", "Student")):
        _, caller = _make_user(role, "AIML")
        assert _create(caller, new_role, "CSE").status_code == 403
        res = _create(caller, new_role)
        assert res.status_code == 201 and res.json()["department_id"] == _dept("AIML")


def test_hod_manages_only_teachers_and_students_of_own_department():
    _, hod = _make_user("HoD", "AIML")
    own_teacher, _ = _make_user("Teacher", "AIML")
    other_teacher, _ = _make_user("Teacher", "CSE")
    principal, _ = _make_user("Principal")
    h = bearer(hod)

    assert client.put(f"/api/v1/users/{own_teacher}", json={"is_active": False}, headers=h).status_code == 200
    assert client.put(f"/api/v1/users/{own_teacher}", json={"role_name": "HoD"}, headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{own_teacher}", json={"department_id": _dept("CSE")}, headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{other_teacher}", json={"is_active": False}, headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{principal}", json={"is_active": False}, headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{principal}", headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{other_teacher}", headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{own_teacher}", headers=h).status_code == 200


def test_teacher_manages_only_students_of_own_department():
    _, teacher = _make_user("Teacher", "AIML")
    own_student, _ = _make_user("Student", "AIML")
    other_student, _ = _make_user("Student", "CSE")
    peer, _ = _make_user("Teacher", "AIML")
    h = bearer(teacher)

    assert client.put(f"/api/v1/users/{own_student}", json={"role_name": "Teacher"}, headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{peer}", json={"is_active": False}, headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{other_student}", headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{own_student}", headers=h).status_code == 200


def test_principal_cannot_touch_admins():
    _, principal = _make_user("Principal")
    college_admin, _ = _make_user("College Admin")
    hod, _ = _make_user("HoD", "CSE")
    h = bearer(principal)
    assert client.put(f"/api/v1/users/{college_admin}", json={"is_active": False}, headers=h).status_code == 403
    assert client.delete(f"/api/v1/users/{college_admin}", headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{hod}", json={"role_name": "College Admin"}, headers=h).status_code == 403
    assert client.put(f"/api/v1/users/{hod}", json={"department_id": _dept("AIML")}, headers=h).status_code == 200


def test_hod_without_department_can_view_but_not_change():
    _, hod = _make_user("HoD")
    assert client.get("/api/v1/users/", headers=bearer(hod)).status_code == 200
    assert _create(hod, "Student").status_code == 403
