"""Alerts: 'restore to unread' is kept by the server, and 'clear history' really clears your read alerts."""
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.notification import Notification
from app.models.user import User

client = TestClient(app)
ME = bearer("ESDev01")


def _my_alerts():
    res = client.get("/api/v1/notifications/", headers=ME)
    assert res.status_code == 200, res.text
    return {n["id"]: n["is_read"] for n in res.json()}


def _seed(count=3):
    res = client.post("/api/v1/announcements", headers=ME, json={
        "title": "Alert history check", "description": "x", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False})
    ann_id = res.json()["id"]
    with SessionLocal() as db:
        me = db.query(User).filter(User.username == "ESDev01").one()
        other = db.query(User).filter(User.username != "ESDev01").first()
        mine = [Notification(announcement_id=ann_id, user_id=me.id, is_read=False) for _ in range(count)]
        theirs = Notification(announcement_id=ann_id, user_id=other.id, is_read=True)
        db.add_all(mine + [theirs]); db.commit()
        return [n.id for n in mine], theirs.id


def test_restoring_an_alert_to_unread_is_kept_by_the_server():
    (a, _b, _c), _ = _seed()
    assert client.put(f"/api/v1/notifications/{a}/read", headers=ME).status_code == 200
    assert _my_alerts()[a] is True
    assert client.put(f"/api/v1/notifications/{a}/unread", headers=ME).status_code == 200
    assert _my_alerts()[a] is False


def test_clear_history_removes_only_my_read_alerts():
    (a, b, c), theirs = _seed()
    client.put(f"/api/v1/notifications/{a}/read", headers=ME)
    client.put(f"/api/v1/notifications/{b}/read", headers=ME)
    res = client.delete("/api/v1/notifications/read", headers=ME)
    assert res.status_code == 200, res.text
    alerts = _my_alerts()
    assert a not in alerts and b not in alerts, "read alerts must be gone"
    assert alerts.get(c) is False, "unread alerts stay"
    with SessionLocal() as db:
        assert db.get(Notification, theirs) is not None, "another person's alerts are untouched"
