"""Rescheduling a notice from the app changes its real scheduled time on the server."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.db.database import SessionLocal
from app.main import app
from app.models.announcement import Announcement

client = TestClient(app)
ADMIN = bearer("ESDev01")


def test_reschedule_sets_the_new_time_and_scheduled_status():
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Placement talk", "description": "Placement talk in the seminar hall.", "category_id": 1,
        "target_audience": "Entire College", "deliver_push": False, "deliver_in_app": False})
    nid = res.json()["id"]
    new_time = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=0)
    # exactly what the app sends when rescheduling
    res = client.put(f"/api/v1/announcements/{nid}", headers=ADMIN,
                     json={"scheduled_at": new_time.isoformat(), "status": "Scheduled"})
    assert res.status_code == 200, res.text
    with SessionLocal() as db:
        ann = db.get(Announcement, nid)
        assert ann.scheduled_at.replace(tzinfo=None) == new_time.replace(tzinfo=None)
        assert getattr(ann.status, "value", ann.status) == "Scheduled"
    listed = [a for a in client.get("/api/v1/announcements", headers=ADMIN).json() if a["id"] == nid][0]
    assert listed["scheduled_at"].startswith(new_time.strftime("%Y-%m-%dT%H:%M"))
