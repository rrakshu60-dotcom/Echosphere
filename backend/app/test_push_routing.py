"""Push: a signed-in device is subscribed (by the server, from the account) to its topics, and a notice is pushed
to the topic of its audience (it used the creator's department, so 'Entire College' notices went to one dept)."""
import pytest
from fastapi.testclient import TestClient

import app.services.firebase_push_service as push
from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.user import User

client = TestClient(app)
ADMIN = bearer("ESDev01")


@pytest.fixture
def fake_fcm(monkeypatch):
    calls = {"subscribed": [], "sent": []}
    monkeypatch.setattr(push, "get_firebase_admin_app", lambda: object())

    def subscribe(tokens, topic, app=None):
        calls["subscribed"].append((tuple(tokens), topic))
        return type("R", (), {"success_count": len(tokens), "failure_count": 0, "errors": []})()

    def send(message, dry_run=False, app=None):
        calls["sent"].append(message.topic)
        return "projects/test/messages/1"

    from firebase_admin import messaging
    monkeypatch.setattr(messaging, "subscribe_to_topic", subscribe)
    monkeypatch.setattr(messaging, "send", send)
    return calls


def test_registering_a_device_subscribes_it_to_the_accounts_topics(fake_fcm):
    assert client.post("/api/v1/push/register", json={"token": "tok-1-abcdefghijklmnopqrstuvwxyz"}).status_code == 401
    res = client.post("/api/v1/push/register", headers=bearer("1db23ci079"), json={"token": "tok-1-abcdefghijklmnopqrstuvwxyz", "platform": "web"})
    assert res.status_code == 200, res.text
    with SessionLocal() as db:
        student = db.query(User).filter(User.username == "1db23ci079").one()
        dept = student.department.code.lower() if student.department else None
    topics = {t for _tok, t in fake_fcm["subscribed"]}
    assert {"all_campus", "emergency_broadcasts"} <= topics
    if dept:
        assert f"dept_{dept}" in topics
    assert all(tok == ("tok-1-abcdefghijklmnopqrstuvwxyz",) for tok, _t in fake_fcm["subscribed"])


def _publish(audience, **fields):
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Push routing", "description": "x", "category_id": 1, "target_audience": audience,
        "deliver_push": True, "deliver_in_app": False, **fields})
    assert res.status_code in (200, 201), res.text


def test_an_entire_college_notice_is_pushed_to_everyone(fake_fcm):
    _publish("Entire College")
    assert fake_fcm["sent"] == ["all_campus"], fake_fcm["sent"]


def test_a_department_notice_is_pushed_to_that_department(fake_fcm):
    _publish("CSE Department")
    assert fake_fcm["sent"] == ["dept_cse"], fake_fcm["sent"]
