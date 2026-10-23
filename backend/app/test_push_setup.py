"""Push notifications: Firebase is set up from the base64 key in the environment, and without Firebase a push is
recorded as not sent (it was recorded as 'sent', with a fake 'mock_sent' result)."""
import base64
import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

import app.services.firebase_push_service as push
from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")


@pytest.fixture(autouse=True)
def _fresh_firebase(monkeypatch):
    monkeypatch.setattr(push, "_firebase_app", None)
    for var in ("FIREBASE_SERVICE_ACCOUNT_KEY", "FIREBASE_SERVICE_ACCOUNT_JSON", "FIREBASE_SERVICE_ACCOUNT_JSON_B64"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(push.glob, "glob", lambda *_a, **_k: [])


def _service_account() -> dict:
    pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    return {"type": "service_account", "project_id": "test-project", "private_key_id": "abc", "private_key": pem,
            "client_email": "push@test-project.iam.gserviceaccount.com", "client_id": "1",
            "token_uri": "https://oauth2.googleapis.com/token"}


def test_firebase_is_set_up_from_the_base64_key(monkeypatch):
    import firebase_admin
    seen = {}

    def fake_init(cred, *a, **k):
        seen["project"] = cred.project_id
        return type("App", (), {"project_id": cred.project_id})()

    monkeypatch.setattr(firebase_admin, "_apps", {})
    monkeypatch.setattr(firebase_admin, "initialize_app", fake_init)
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON_B64", base64.b64encode(json.dumps(_service_account()).encode()).decode())
    assert push.get_firebase_admin_app() is not None
    assert seen["project"] == "test-project"


def test_without_firebase_a_push_is_recorded_as_not_sent(monkeypatch):
    import firebase_admin
    monkeypatch.setattr(firebase_admin, "_apps", {})
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Push check", "description": "x", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": True, "deliver_in_app": False})
    nid = res.json()["id"]
    from app.db.database import SessionLocal
    from app.models.notice_record import NoticeRecordEvent
    with SessionLocal() as db:
        details = [e.detail for e in db.query(NoticeRecordEvent).filter(NoticeRecordEvent.announcement_id == nid,
                                                                          NoticeRecordEvent.event == "PUSH_SENT")]
    assert details and "not sent" in details[0].lower() and "mock" not in details[0].lower(), details
