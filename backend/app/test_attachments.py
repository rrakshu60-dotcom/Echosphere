"""Notice attachments: uploaded to cloud storage by signed-in staff, kept with the notice, opened by everyone.
(Only the file names were saved before; the files themselves were never uploaded.)"""
import pytest
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")
UPLOAD = "/api/v1/announcements/attachments/upload"


@pytest.fixture(autouse=True)
def _temp_storage(monkeypatch, tmp_path):
    import app.services.cloud_storage_service as storage
    monkeypatch.setattr(storage, "STATIC_DIR", str(tmp_path))


def _upload(name="circular.pdf", data=b"%PDF-1.4 test", mime="application/pdf", headers=ADMIN):
    return client.post(UPLOAD, headers=headers, files={"file": (name, data, mime)})


def test_uploading_needs_a_staff_login():
    assert _upload(headers={}).status_code == 401
    assert _upload(headers=bearer("1db23ci079")).status_code == 403  # a student


def test_too_large_and_unsupported_files_are_refused():
    assert _upload(data=b"0" * (10 * 1024 * 1024 + 1)).status_code == 413
    assert _upload(name="setup.exe", mime="application/octet-stream").status_code == 400


def test_same_name_uploads_do_not_overwrite_each_other():
    a, b = _upload().json(), _upload().json()
    assert a["file_url"] != b["file_url"]
    assert a["file_name"].endswith("circular.pdf") and a["size_bytes"] == len(b"%PDF-1.4 test")


def test_a_notice_keeps_its_attachments():
    up = _upload().json()
    attachment = {"name": "circular.pdf", "url": up["file_url"], "size": up["size_bytes"], "mime": up["mime_type"]}
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Exam circular", "description": "See the attached circular.", "category_id": 1,
        "target_audience": "Entire College", "deliver_push": False, "deliver_in_app": False,
        "attachments": [attachment]})
    assert res.status_code in (200, 201), res.text
    nid = res.json()["id"]
    listed = [a for a in client.get("/api/v1/announcements", headers=ADMIN).json() if a["id"] == nid][0]
    assert listed["attachments"] == [attachment]


def test_only_links_to_our_attachment_storage_are_accepted():
    """A notice can't carry a link to any other site (e.g. a phishing page) as an 'attachment'."""
    for bad in ("https://evil.example/login.pdf", "http://huggingface.co/datasets/x/resolve/main/attachments/a.pdf",
                "javascript:alert(1)", "https://huggingface.co/datasets/x/resolve/main/audio_streams/a.wav"):
        res = client.post("/api/v1/announcements", headers=ADMIN, json={
            "title": "Bad link", "description": "x", "category_id": 1, "target_audience": "Entire College",
            "deliver_push": False, "deliver_in_app": False, "attachments": [{"name": "a.pdf", "url": bad}]})
        assert res.status_code == 422, (bad, res.status_code)


def test_deleting_a_notice_removes_its_attachment_files(monkeypatch):
    """Otherwise every deleted notice's files would stay in cloud storage forever."""
    import threading
    from app.services.cloud_storage_service import CloudStorageService

    removed = []
    monkeypatch.setattr(CloudStorageService, "delete_attachment_files", classmethod(lambda cls, names: removed.extend(names) or len(names)))
    up = _upload().json()
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Temporary circular", "description": "x", "category_id": 1, "target_audience": "Entire College",
        "deliver_push": False, "deliver_in_app": False,
        "attachments": [{"name": "circular.pdf", "url": up["file_url"]}]})
    nid = res.json()["id"]
    assert client.delete(f"/api/v1/announcements/{nid}", headers=ADMIN).status_code == 200
    for t in threading.enumerate():
        if t.name.startswith("NoticeAttachmentDelete-"):
            t.join(timeout=10)
    assert removed == [up["file_name"]], removed
