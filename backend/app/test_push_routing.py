"""Push: signed-in devices register their token with the server, and a notice is sent straight to the devices of
its audience (Firebase topic subscription is refused for this project, so topics are not used)."""
import pytest
from fastapi.testclient import TestClient

import app.services.firebase_push_service as push
from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.push_device import PushDevice

client = TestClient(app)
ADMIN = bearer("ESDev01")
STUDENT_TOKEN = "student-token-abcdefghijklmnopqrstuvwxyz"
TEACHER_TOKEN = "teacher-token-abcdefghijklmnopqrstuvwxyz"


@pytest.fixture
def fake_fcm(monkeypatch):
    """Records which tokens each push went to; tokens containing 'dead' are reported as no longer registered."""
    sent = []
    monkeypatch.setattr(push, "get_firebase_admin_app", lambda: object())
    from firebase_admin import messaging

    def send_each_for_multicast(message, dry_run=False, app=None):
        sent.append(sorted(message.tokens))
        responses = []
        for t in message.tokens:
            ok = "dead" not in t
            exc = None if ok else messaging.UnregisteredError("gone")
            responses.append(type("R", (), {"success": ok, "exception": exc})())
        return type("B", (), {"responses": responses, "success_count": sum(r.success for r in responses),
                              "failure_count": sum(not r.success for r in responses)})()

    monkeypatch.setattr(messaging, "send_each_for_multicast", send_each_for_multicast)
    with SessionLocal() as db:
        db.query(PushDevice).delete()
        db.commit()
    return sent


def _register(user, token):
    res = client.post("/api/v1/push/register", headers=bearer(user), json={"token": token, "platform": "web"})
    assert res.status_code == 200, res.text


def _publish(audience):
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Push routing", "description": "x", "category_id": 1, "target_audience": audience,
        "deliver_push": True, "deliver_in_app": False})
    assert res.status_code in (200, 201), res.text


def test_registering_needs_a_login_and_stores_the_device(fake_fcm):
    assert client.post("/api/v1/push/register", json={"token": STUDENT_TOKEN}).status_code == 401
    _register("1db23ci079", STUDENT_TOKEN)
    _register("1db23ci079", STUDENT_TOKEN)  # registering again doesn't duplicate it
    with SessionLocal() as db:
        assert db.query(PushDevice).filter(PushDevice.token == STUDENT_TOKEN).count() == 1


def test_a_device_moves_to_whoever_signs_in_on_it(fake_fcm):
    _register("1db23ci079", STUDENT_TOKEN)
    _register("dbitaimlt022022", STUDENT_TOKEN)
    _publish("Faculty Members")
    assert fake_fcm == [[STUDENT_TOKEN]]  # now the teacher's device


def test_each_audience_reaches_only_its_devices(fake_fcm):
    _register("1db23ci079", STUDENT_TOKEN)
    _register("dbitaimlt022022", TEACHER_TOKEN)
    for audience, expected in (("Entire College", [STUDENT_TOKEN, TEACHER_TOKEN]),
                               ("Faculty Members", [TEACHER_TOKEN]),
                               ("Alumni Association", None)):
        fake_fcm.clear()
        _publish(audience)
        assert fake_fcm == ([sorted(expected)] if expected else []), (audience, fake_fcm)


def test_a_dead_device_token_is_forgotten(fake_fcm):
    _register("1db23ci079", "dead-token-abcdefghijklmnopqrstuvwxyz")
    _publish("Entire College")
    with SessionLocal() as db:
        assert db.query(PushDevice).count() == 0


def test_an_unknown_platform_value_is_refused(fake_fcm):
    res = client.post("/api/v1/push/register", headers=ADMIN,
                      json={"token": "tok-3-abcdefghijklmnopqrstuvwxyz", "platform": "web\nFAKE LOG LINE"})
    assert res.status_code == 422


def test_a_device_whose_session_ended_gets_no_push(fake_fcm):
    """Signing out (or an admin ending the session) stops pushes to that device, even if it kept its token."""
    headers = bearer("1db23ci079")
    assert client.post("/api/v1/push/register", headers=headers, json={"token": STUDENT_TOKEN}).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    _publish("Entire College")
    assert fake_fcm == [], fake_fcm
