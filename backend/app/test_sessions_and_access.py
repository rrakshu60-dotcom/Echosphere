"""Sessions, sign-in log and app-access log (owner decisions 2026-10-22)."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.core.jwt_handler import create_access_token, verify_access_token
from app.db.database import SessionLocal
from app.main import app
from app.models.app_access_log import AppAccessLog
from app.models.audit_log import AuditLog
from app.models.password_reset_token import PasswordResetToken
from app.models.sign_in_log import SignInLog
from app.models.user import User
from app.models.user_session import UserSession

client = TestClient(app)
import os

PASSWORD = os.environ["ES_PASSWORD_DBITAIMLT022022"]
TEACHER = "dbitaimlt022022"
# On Render, Cloudflare sets CF-Connecting-IP (and overwrites any client value); X-Forwarded-For can be forged.
CLIENT_HEADERS = {
    "CF-Connecting-IP": "203.0.113.7",
    "X-Forwarded-For": "6.6.6.6, 10.26.96.152",
    "User-Agent": "EchoSphereTest/1.0",
}


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _login(identifier=TEACHER, password=PASSWORD, remember_me=False, platform="android"):
    return client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password, "remember_me": remember_me, "platform": platform},
        headers=CLIENT_HEADERS,
    )


def _last_sign_in() -> SignInLog:
    with SessionLocal() as db:
        return db.query(SignInLog).order_by(SignInLog.id.desc()).first()


def _me(token):
    return client.get("/api/v1/notifications/", headers={"Authorization": f"Bearer {token}"})


@pytest.fixture(autouse=True)
def _teacher_active():
    yield
    with SessionLocal() as db:
        db.query(User).filter(User.username == TEACHER).update({"is_active": True})
        db.commit()


# ---------------------------------------------------------------- sign-in


def test_successful_sign_in_creates_a_session_and_is_logged():
    res = _login(remember_me=True)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["access_token"] and body["refresh_token"] and body["session_id"]

    log = _last_sign_in()
    assert log.success is True and log.reason == "ok"
    assert log.identifier == TEACHER and log.user_id is not None
    assert log.ip == "203.0.113.7"  # Cloudflare's address for the client, not a forgeable header
    assert log.platform == "android" and log.user_agent == "EchoSphereTest/1.0"
    assert log.session_id == body["session_id"]

    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        assert s.remember_me is True and s.ended_at is None
        assert s.refresh_hash != body["refresh_token"]  # stored scrambled, never in plain text
        assert timedelta(days=29) < s.expires_at - s.created_at <= timedelta(days=30)


def test_access_token_lasts_30_minutes_and_names_its_session():
    body = _login().json()
    claims = verify_access_token(body["access_token"])
    assert claims["sid"] == body["session_id"]
    lifetime = datetime.fromtimestamp(claims["exp"], timezone.utc) - datetime.now(timezone.utc)
    assert timedelta(minutes=28) < lifetime <= timedelta(minutes=30)


def test_session_without_remember_me_ends_within_12_hours():
    body = _login(remember_me=False).json()
    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        assert s.remember_me is False
        assert timedelta(hours=11) < s.expires_at - s.created_at <= timedelta(hours=12)


@pytest.mark.parametrize(
    "identifier,password,reason",
    [("nobody-here", "whatever", "unknown_user"), (TEACHER, "wrong-password", "wrong_password")],
)
def test_failed_sign_ins_are_logged_with_the_reason(identifier, password, reason):
    res = _login(identifier=identifier, password=password)
    assert res.status_code == 400
    assert res.json()["detail"] == "Invalid credentials."  # same message either way: no account probing
    log = _last_sign_in()
    assert log.success is False and log.reason == reason
    assert log.session_id is None and log.ip == "203.0.113.7"
    if reason == "wrong_password":
        assert log.identifier == identifier  # a real account ID: kept so admins can see who was targeted


def test_unknown_identifiers_are_masked_in_case_a_password_was_typed_there():
    _login(identifier="MyS3cretPassw0rd!", password="x")
    log = _last_sign_in()
    assert log.reason == "unknown_user"
    assert "S3cret" not in log.identifier and log.identifier.startswith("My")
    assert "17" in log.identifier  # length kept, content hidden


def test_disabled_account_cannot_sign_in():
    with SessionLocal() as db:
        db.query(User).filter(User.username == TEACHER).update({"is_active": False})
        db.commit()
    res = _login()
    assert res.status_code == 400
    assert _last_sign_in().reason == "disabled"


# ---------------------------------------------------------------- requests


def test_tokens_without_a_session_are_rejected():
    legacy = create_access_token({"sub": TEACHER})
    assert _me(legacy).status_code == 401


def test_disabling_an_account_signs_it_out_at_once():
    token = _login().json()["access_token"]
    assert _me(token).status_code == 200
    with SessionLocal() as db:
        db.query(User).filter(User.username == TEACHER).update({"is_active": False})
        db.commit()
    assert _me(token).status_code == 401


def test_sign_out_ends_the_session():
    body = _login().json()
    auth = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.post("/api/v1/auth/logout", headers=auth).status_code == 200
    assert _me(body["access_token"]).status_code == 401
    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        assert s.ended_at is not None and s.end_reason == "sign_out"


# ---------------------------------------------------------------- refresh


def _refresh(refresh_token, **extra):
    return client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token, "platform": "web", "app_version": "2.2.0", **extra},
        headers=CLIENT_HEADERS,
    )


def test_refresh_hands_out_a_new_key_and_the_old_one_stops_working():
    body = _login(remember_me=True).json()
    first = _refresh(body["refresh_token"])
    assert first.status_code == 200, first.text
    new = first.json()
    assert new["refresh_token"] != body["refresh_token"]
    assert verify_access_token(new["access_token"])["sid"] == body["session_id"]
    assert _refresh(body["refresh_token"]).status_code == 401  # old key is spent
    assert _refresh(new["refresh_token"]).status_code == 200


def test_refresh_is_logged_as_app_access():
    body = _login().json()
    _refresh(body["refresh_token"])
    with SessionLocal() as db:
        log = db.query(AppAccessLog).order_by(AppAccessLog.id.desc()).first()
    assert log.event == "refresh" and log.session_id == body["session_id"]
    assert log.platform == "web" and log.app_version == "2.2.0" and log.ip == "203.0.113.7"


def test_refresh_refused_after_the_session_expires():
    body = _login(remember_me=True).json()
    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        s.expires_at = _now() - timedelta(seconds=1)
        db.commit()
    assert _refresh(body["refresh_token"]).status_code == 401


def test_remembered_session_ends_after_7_days_unused():
    body = _login(remember_me=True).json()
    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        s.last_seen_at = _now() - timedelta(days=7, minutes=1)
        db.commit()
    assert _refresh(body["refresh_token"]).status_code == 401
    assert _me(body["access_token"]).status_code == 401


def test_refresh_refused_for_a_disabled_account():
    body = _login().json()
    with SessionLocal() as db:
        db.query(User).filter(User.username == TEACHER).update({"is_active": False})
        db.commit()
    assert _refresh(body["refresh_token"]).status_code == 401


def test_password_reset_signs_out_every_device():
    a, b = _login().json(), _login(platform="windows").json()
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == TEACHER).one()
        db.add(PasswordResetToken(user_id=user.id, token="reset-xyz", expires_at=_now() + timedelta(hours=1), used=False))
        db.commit()
    from app.services.password_reset_service import reset_password_service

    with SessionLocal() as db:
        reset_password_service(db=db, token="reset-xyz", new_password=PASSWORD)
    assert _refresh(a["refresh_token"]).status_code == 401
    assert _me(b["access_token"]).status_code == 401


# ---------------------------------------------------------------- app opens


def test_app_open_is_logged_for_signed_in_users():
    body = _login().json()
    res = client.post(
        "/api/v1/auth/access",
        json={"event": "resume", "platform": "windows", "app_version": "2.2.0"},
        headers={**CLIENT_HEADERS, "Authorization": f"Bearer {body['access_token']}"},
    )
    assert res.status_code == 204, res.text
    with SessionLocal() as db:
        log = db.query(AppAccessLog).order_by(AppAccessLog.id.desc()).first()
        user = db.query(User).filter(User.username == TEACHER).one()
    assert log.event == "resume" and log.user_id == user.id and log.session_id == body["session_id"]
    assert log.platform == "windows" and log.ip == "203.0.113.7"


def test_app_open_on_the_sign_in_screen_is_logged_anonymously():
    res = client.post("/api/v1/auth/access", json={"event": "launch", "platform": "web", "app_version": "2.2.0"}, headers=CLIENT_HEADERS)
    assert res.status_code == 204
    with SessionLocal() as db:
        log = db.query(AppAccessLog).order_by(AppAccessLog.id.desc()).first()
    assert log.event == "launch" and log.user_id is None and log.session_id is None


def test_app_open_rejects_unknown_events():
    res = client.post("/api/v1/auth/access", json={"event": "hack", "platform": "web"}, headers=CLIENT_HEADERS)
    assert res.status_code == 422


def test_app_access_entries_older_than_90_days_are_purged():
    from app.services.session_service import purge_old_access_logs

    with SessionLocal() as db:
        db.add(AppAccessLog(event="launch", platform="web", ip="1.1.1.1", created_at=_now() - timedelta(days=91)))
        db.add(AppAccessLog(event="launch", platform="web", ip="2.2.2.2", created_at=_now() - timedelta(days=89)))
        db.commit()
        removed = purge_old_access_logs(db)
        ips = {r.ip for r in db.query(AppAccessLog).all()}
    assert removed >= 1
    assert "1.1.1.1" not in ips and "2.2.2.2" in ips


# ---------------------------------------------------------------- admin views


def test_only_dev_admin_and_college_admin_can_read_access_logs():
    for path in ("/api/v1/audit/sign-ins", "/api/v1/audit/access", "/api/v1/audit/sessions"):
        assert client.get(path, headers=bearer("principal")).status_code == 403
        assert client.get(path, headers=bearer(TEACHER)).status_code == 403
        assert client.get(path).status_code == 401
        assert client.get(path, headers=bearer("ESDev01")).status_code == 200
        assert client.get(path, headers=bearer("CAdmin")).status_code == 200


def test_sign_in_log_search_filter_sort_and_pages():
    _login(identifier="sp-probe-one", password="x")
    _login(identifier="sp-probe-two", password="x")
    _login()
    admin = bearer("ESDev01")
    page = client.get(
        "/api/v1/audit/sign-ins",
        params={"q": "sp", "success": "false", "sort": "at", "order": "asc", "page": 1, "page_size": 1},
        headers=admin,
    ).json()
    assert page["total"] == 2 and page["page"] == 1 and len(page["items"]) == 1
    assert page["items"][0]["success"] is False and page["items"][0]["reason"] == "unknown_user"

    by_ip = client.get("/api/v1/audit/sign-ins", params={"q": "203.0.113.7"}, headers=admin).json()
    assert by_ip["total"] >= 3


def test_admin_can_end_another_users_session_and_it_is_audited():
    body = _login().json()
    admin = bearer("CAdmin")
    res = client.post(f"/api/v1/audit/sessions/{body['session_id']}/end", headers=admin)
    assert res.status_code == 200, res.text
    assert _me(body["access_token"]).status_code == 401
    assert _refresh(body["refresh_token"]).status_code == 401
    with SessionLocal() as db:
        s = db.get(UserSession, body["session_id"])
        assert s.end_reason == "ended_by_admin" and s.ended_by_user_id is not None
        audit = db.query(AuditLog).filter(AuditLog.action == "END_SESSION").order_by(AuditLog.id.desc()).first()
        assert audit is not None and audit.entity_id == body["session_id"]

    active = client.get("/api/v1/audit/sessions", params={"state": "active", "q": TEACHER}, headers=admin).json()
    assert body["session_id"] not in [x["id"] for x in active["items"]]


# ---------------------------------------------------------------- live microphone


def _mic_socket_refused(params: str) -> bool:
    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect(f"/api/v1/ws/hardware/mic-stream?zone=College-Wide{params}") as ws:
            ws.receive_json()
    except WebSocketDisconnect as closed:
        return closed.code == 1008
    return False


def test_live_microphone_refuses_callers_without_a_session():
    assert _mic_socket_refused("")
    assert _mic_socket_refused("&token=" + create_access_token({"sub": "ESDev01", "role": "Dev Admin"}))


def test_live_microphone_refuses_students():
    student = bearer("1db23ci079")["Authorization"].split()[1]
    assert _mic_socket_refused("&token=" + student)


def test_live_microphone_refuses_an_ended_session():
    body = _login().json()
    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert _mic_socket_refused("&token=" + body["access_token"])


def test_without_cloudflare_forwarded_headers_are_not_trusted():
    from starlette.requests import Request

    from app.services.session_service import client_ip

    def req(headers):
        return Request({"type": "http", "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
                        "client": ("10.0.0.5", 1234)})

    # X-Forwarded-For can be typed by anyone; only the direct connection counts then
    assert client_ip(req({"X-Forwarded-For": "198.51.100.4, 10.26.96.152"})) == "10.0.0.5"
    assert client_ip(req({})) == "10.0.0.5"
