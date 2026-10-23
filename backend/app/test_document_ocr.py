"""Document OCR: a photo or PDF of a circular is read by the configured Gemini model; when it can't be read the
app is told so plainly (it used to decode the image bytes as text and invent a circular around 'IHDR...')."""
import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

import app.services.smart_intake_service as intake
from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")


def _png() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), "white").save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode()


class _Resp:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


@pytest.fixture
def gemini(monkeypatch):
    """A fake Gemini: records the models asked, answers only for the configured one."""
    calls = []
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test-current")

    def fake_post(url, json=None, timeout=None, headers=None, **_):
        assert "test-key" not in url, "the API key must not be in the URL (errors and logs include it)"
        assert (headers or {}).get("x-goog-api-key") == "test-key"
        model = url.split("/models/")[1].split(":")[0]
        calls.append(model)
        if model != "gemini-test-current":
            return _Resp(404, {"error": {"message": f"model {model} not found"}})
        text = '{"title": "Library closed Friday", "content": "The library is closed on Friday after 4 PM.", ' \
               '"suggested_category": "Academic", "suggested_priority": "NORMAL", "suggested_audience": "Entire College", ' \
               '"reference_number": "42", "extracted_event": null, "raw_text": "CIRCULAR No 42"}'
        return _Resp(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})

    monkeypatch.setattr(intake.requests, "post", fake_post)
    return calls


def test_an_image_is_read_with_the_configured_model(gemini):
    res = client.post("/api/v1/announcements/ocr-document", headers=ADMIN,
                      json={"file_base64": _png(), "filename": "circular.png", "mime_type": "image/png"})
    assert res.status_code == 200, res.text
    assert res.json()["title"] == "Library closed Friday"
    assert gemini[0] == "gemini-test-current", gemini


def test_an_unreadable_image_is_reported_not_invented(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    res = client.post("/api/v1/announcements/ocr-document", headers=ADMIN,
                      json={"file_base64": _png(), "filename": "circular.png", "mime_type": "image/png"})
    assert res.status_code == 422, res.text
    assert "IHDR" not in res.text and "PNG" not in res.text
    assert "read" in res.json()["detail"].lower()
