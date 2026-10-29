"""Speaker device keys, signed-in live socket, sign-in and AI limits, CORS, audience matching and HoD scope."""
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth_test_helpers import bearer, speaker_headers
from app.core.audience import is_institution_wide, mentions_department
from app.core.enums.announcement import AnnouncementStatus
from app.core.password import hash_password
from app.core.speaker_auth import SPEAKER_KEY_HEADER, device_key_for
from app.core.throttle import check_ai_quota
from app.core.websocket_manager import _visible_to_role
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement import Announcement
from app.models.department import Department
from app.models.speaker_node import SpeakerNode
from app.models.user import User

client = TestClient(app)
DEV = bearer("ESDev01")
HOD = bearer("hod_aiml")
TEACHER = bearer("dbitaimlt022022")
STUDENT = bearer("1db23ci079")


def _registered_mac(mac: str = "AA:BB:CC:DD:EE:01") -> str:
    with SessionLocal() as db:
        if not db.query(SpeakerNode).filter(SpeakerNode.mac_address == mac).first():
            db.add(SpeakerNode(name="Key test speaker", mac_address=mac, zone="Lab", volume=80, status="ONLINE"))
            db.commit()
    return mac


# ---------------------------------------------------------------- speaker device keys

def test_heartbeat_needs_the_speakers_own_device_key():
    mac = _registered_mac()
    body = {"mac_address": mac, "status": "ONLINE"}
    assert client.post("/api/v1/hardware/speakers/heartbeat", json=body).status_code == 401
    wrong = {SPEAKER_KEY_HEADER: device_key_for("AA:BB:CC:DD:EE:02")}
    assert client.post("/api/v1/hardware/speakers/heartbeat", json=body, headers=wrong).status_code == 401
    assert client.post("/api/v1/hardware/speakers/heartbeat", json=body, headers=speaker_headers(mac)).status_code == 200


def test_poll_and_display_feed_need_a_key_or_a_login():
    mac = _registered_mac()
    assert client.get(f"/api/v1/hardware/speakers/poll/{mac}").status_code == 401
    assert client.get(f"/api/v1/hardware/speakers/poll/{mac}", headers=speaker_headers(mac)).status_code == 200
    assert client.get("/api/v1/hardware/speakers/display-feed").status_code == 401
    assert client.get("/api/v1/hardware/speakers/display-feed", headers=STUDENT).status_code == 200
    assert client.get(f"/api/v1/hardware/speakers/display-feed?mac_address={mac}", headers=speaker_headers(mac)).status_code == 200


def test_queue_complete_without_a_key_is_refused():
    assert client.post("/api/v1/hardware/queue/999999/action?action=complete").status_code in (401, 404)
    with SessionLocal() as db:
        from app.models.speaker_queue import SpeakerQueue
        item = db.query(SpeakerQueue).first()
    if item is not None:
        assert client.post(f"/api/v1/hardware/queue/{item.id}/action?action=complete").status_code == 401


def test_speaker_push_socket_needs_the_device_key():
    mac = _registered_mac()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"/api/v1/ws/speaker/{mac}") as ws:
            ws.receive_text()
    with client.websocket_connect(f"/api/v1/ws/speaker/{mac}", headers=speaker_headers(mac)) as ws:
        ws.send_text("ping")


def test_only_platform_admins_can_read_a_device_key():
    mac = _registered_mac()
    with SessionLocal() as db:
        speaker_id = db.query(SpeakerNode).filter(SpeakerNode.mac_address == mac).one().id
    res = client.get(f"/api/v1/hardware/speakers/{speaker_id}/device-key", headers=DEV)
    assert res.status_code == 200, res.text
    assert res.json()["device_key"] == device_key_for(mac)
    assert client.get(f"/api/v1/hardware/speakers/{speaker_id}/device-key", headers=TEACHER).status_code == 403
    assert client.get(f"/api/v1/hardware/speakers/{speaker_id}/device-key").status_code == 401


def test_device_keys_differ_per_speaker_and_ignore_mac_case():
    assert device_key_for("aa:bb:cc:dd:ee:01") == device_key_for("AA:BB:CC:DD:EE:01")
    assert device_key_for("AA:BB:CC:DD:EE:01") != device_key_for("AA:BB:CC:DD:EE:02")
    assert len(device_key_for("AA:BB:CC:DD:EE:01")) == 32


# ---------------------------------------------------------------- live socket

def test_live_socket_refuses_anonymous_and_ended_sessions():
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/live") as ws:
            ws.receive_json()
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/live?token=not-a-token") as ws:
            ws.receive_json()
    token = STUDENT["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/api/v1/ws/live?token={token}") as ws:
        assert ws.receive_json()["event"] == "CONNECTED"


def test_students_are_not_told_about_unpublished_notices():
    pending = {"event": "ANNOUNCEMENT_CREATED", "status": "Pending Approval", "title": "Draft"}
    published = {"event": "ANNOUNCEMENT_CREATED", "status": "Published", "title": "Out now"}
    rejected = {"event": "ANNOUNCEMENT_REJECTED", "title": "No"}
    assert not _visible_to_role(pending, "Student")
    assert not _visible_to_role(rejected, "Student")
    assert _visible_to_role(published, "Student")
    assert _visible_to_role(pending, "Teacher")
    assert _visible_to_role({"event": "QUEUE_SYNC_START"}, "Student")
    assert not _visible_to_role({"event": "ANNOUNCEMENT_DELETED", "status": "Draft", "title": "x"}, "Student")
    assert _visible_to_role({"event": "ANNOUNCEMENT_DELETED", "status": "Published", "title": "x"}, "Student")


# ---------------------------------------------------------------- sign-in and AI limits

def _set_password(username: str, password: str) -> str:
    """A throw-away account with a known password (seeded accounts keep theirs for other tests)."""
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            teacher = db.query(User).filter(User.username == "dbitaimlt022022").one()
            user = User(username=username, full_name=username, official_email=f"{username}@example.org",
                        role_id=teacher.role_id, department_id=teacher.department_id, is_active=True)
            db.add(user)
        user.password_hash = hash_password(password)
        db.commit()
        return user.official_email


def test_repeated_wrong_passwords_are_slowed_down_per_account_and_address():
    email = _set_password("throttle_user_a", "Right-Pass-123")
    other = _set_password("throttle_user_b", "Other-Pass-123")
    addr = {"cf-connecting-ip": "192.0.2.17"}
    for _ in range(8):
        r = client.post("/api/v1/auth/login", json={"identifier": email, "password": "wrong"}, headers=addr)
        assert r.status_code == 400
    r = client.post("/api/v1/auth/login", json={"identifier": email, "password": "Right-Pass-123"}, headers=addr)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0
    # Another student on the same campus address is not locked out
    assert client.post("/api/v1/auth/login", json={"identifier": other, "password": "Other-Pass-123"}, headers=addr).status_code == 200
    # Nor is the same account from another address
    other_addr = {"cf-connecting-ip": "198.51.100.9"}
    assert client.post("/api/v1/auth/login", json={"identifier": email, "password": "Right-Pass-123"}, headers=other_addr).status_code == 200


def test_successful_sign_in_clears_earlier_failures():
    email = _set_password("throttle_user_a", "Right-Pass-123")
    addr = {"cf-connecting-ip": "192.0.2.18"}
    for _ in range(7):
        client.post("/api/v1/auth/login", json={"identifier": email, "password": "wrong"}, headers=addr)
    assert client.post("/api/v1/auth/login", json={"identifier": email, "password": "Right-Pass-123"}, headers=addr).status_code == 200
    for _ in range(7):
        assert client.post("/api/v1/auth/login", json={"identifier": email, "password": "wrong"}, headers=addr).status_code == 400


def test_ai_quota_stops_runaway_callers():
    for _ in range(20):
        check_ai_quota(424242, heavy=True)
    with pytest.raises(Exception) as refused:
        check_ai_quota(424242, heavy=True)
    assert getattr(refused.value, "status_code", None) == 429
    check_ai_quota(424243, heavy=True)  # other users are unaffected


# ---------------------------------------------------------------- CORS

def _preflight(origin: str):
    return client.options("/api/v1/announcements", headers={
        "Origin": origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "authorization",
    })


def test_cors_allows_only_the_echosphere_web_app_and_local_development():
    assert _preflight("https://echosphere-2jf.pages.dev").headers.get("access-control-allow-origin") == "https://echosphere-2jf.pages.dev"
    assert _preflight("https://a1b2c3.echosphere-2jf.pages.dev").headers.get("access-control-allow-origin")
    assert _preflight("http://localhost:5173").headers.get("access-control-allow-origin")
    assert not _preflight("https://evil.example").headers.get("access-control-allow-origin")
    assert not _preflight("https://echosphere-2jf.pages.dev.evil.example").headers.get("access-control-allow-origin")


# ---------------------------------------------------------------- audience matching and HoD scope

def test_department_codes_match_whole_words_only():
    assert mentions_department("ISE 5th Sem", "ISE")
    assert not mentions_department("Students who raise funds", "ISE")
    assert not mentions_department("All teachers", "CHE")
    assert mentions_department("Artificial Intelligence & Machine Learning students", "AIML", "Artificial Intelligence & Machine Learning")
    assert is_institution_wide("Entire College")
    assert is_institution_wide("college-wide")
    assert not is_institution_wide("CSE exam hall seating")


def _notice(title: str, creator_username: str, audience: str) -> int:
    with SessionLocal() as db:
        creator = db.query(User).filter(User.username == creator_username).one()
        notice = Announcement(
            title=title, description=f"{title} - details.", status=AnnouncementStatus.PUBLISHED,
            target_audience=audience, created_by=creator.id, category_id=1,
        )
        db.add(notice)
        db.commit()
        return notice.id


def _other_department_teacher() -> str:
    with SessionLocal() as db:
        if not db.query(User).filter(User.username == "cse_teacher_sec").first():
            teacher = db.query(User).filter(User.username == "dbitaimlt022022").one()
            cse = db.query(Department).filter(Department.code == "CSE").one()
            db.add(User(username="cse_teacher_sec", full_name="CSE Teacher", official_email="cse.t@echosphere.edu",
                        password_hash=hash_password("Cse-Teacher-1"), role_id=teacher.role_id,
                        department_id=cse.id, is_active=True))
            db.commit()
    return "cse_teacher_sec"


def test_hod_deletes_only_notices_from_their_own_department():
    other = _other_department_teacher()
    foreign = _notice("CSE lab timings", other, "CSE")
    own = _notice("AIML seminar", "dbitaimlt022022", "AIML")
    assert client.delete(f"/api/v1/announcements/{foreign}", headers=HOD).status_code == 403
    assert client.delete(f"/api/v1/announcements/{own}", headers=HOD).status_code == 200
    assert client.delete(f"/api/v1/announcements/{foreign}", headers=bearer("principal")).status_code == 200


def test_hod_and_teacher_list_only_their_own_department():
    _other_department_teacher()
    for headers in (HOD, TEACHER):
        res = client.get("/api/v1/users/", headers=headers)
        assert res.status_code == 200, res.text
        names = {u["full_name"] for u in res.json()}
        assert "CSE Teacher" not in names
        with SessionLocal() as db:
            cse = db.query(Department).filter(Department.code == "CSE").one().id
            other_id = db.query(User).filter(User.username == "cse_teacher_sec").one().id
        assert client.get(f"/api/v1/users/?department_id={cse}", headers=headers).json() == []
        assert client.get(f"/api/v1/users/{other_id}", headers=headers).status_code == 404
    assert "CSE Teacher" in {u["full_name"] for u in client.get("/api/v1/users/", headers=DEV).json()}
