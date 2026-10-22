"""In-app alerts (Notification rows) follow the notice's in-app delivery setting."""
from fastapi.testclient import TestClient

from app.core.jwt_handler import create_access_token
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement_category import AnnouncementCategory
from app.models.notification import Notification

client = TestClient(app)
ADMIN = {"Authorization": f"Bearer {create_access_token({'sub': 'ESDev01'})}"}


def _publish(**fields) -> int:
    with SessionLocal() as db:
        category_id = db.query(AnnouncementCategory.id).first()[0]
    payload = {
        "title": "Library hours change",
        "description": "The central library closes at 6 PM this Friday.",
        "category_id": category_id,
        "target_audience": "Entire College",
        "deliver_push": False,
        **fields,
    }
    res = client.post("/api/v1/announcements", json=payload, headers=ADMIN)
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]


def _alert_count(announcement_id: int) -> int:
    with SessionLocal() as db:
        return db.query(Notification).filter(Notification.announcement_id == announcement_id).count()


def test_in_app_delivery_creates_alerts():
    assert _alert_count(_publish(deliver_in_app=True)) > 0


def test_no_alerts_when_in_app_delivery_is_off():
    assert _alert_count(_publish(deliver_in_app=False, deliver_speaker=True)) == 0


def _teacher_notice(**fields) -> int:
    with SessionLocal() as db:
        category_id = db.query(AnnouncementCategory.id).first()[0]
    teacher = {"Authorization": f"Bearer {create_access_token({'sub': 'dbitaimlt022022'})}"}
    payload = {
        "title": "Lab session moved",
        "description": "Friday's AIML lab session moves to Saturday 10 AM.",
        "category_id": category_id,
        "target_audience": "Entire College",
        **fields,
    }
    res = client.post("/api/v1/announcements", json=payload, headers=teacher)
    assert res.status_code in (200, 201), res.text
    nid = res.json()["id"]
    assert _alert_count(nid) == 0  # not published yet
    return nid


def _approve(nid: int) -> None:
    # College-wide notices are approved by the Principal or College Admin
    principal = {"Authorization": f"Bearer {create_access_token({'sub': 'principal'})}"}
    res = client.post(f"/api/v1/announcements/{nid}/approve", json={"remarks": "ok"}, headers=principal)
    assert res.status_code == 200, res.text


def test_approval_keeps_in_app_delivery_off():
    nid = _teacher_notice(deliver_in_app=False, deliver_push=False, deliver_speaker=True)
    _approve(nid)
    assert _alert_count(nid) == 0


def test_approval_still_alerts_when_in_app_delivery_is_on():
    nid = _teacher_notice(deliver_in_app=True, deliver_push=False)
    _approve(nid)
    assert _alert_count(nid) > 0
