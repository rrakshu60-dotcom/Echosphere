"""Who may register a speaker: new speakers need an admin; known speakers reconnect without a login."""
import secrets

from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)


def _auth(username: str) -> dict:
    return bearer(username)


def _new_node() -> dict:
    mac = "02:" + ":".join(f"{b:02X}" for b in secrets.token_bytes(5))
    return {"name": "Corridor speaker", "mac_address": mac, "ip_address": "10.0.0.9", "zone": "Block A"}


def test_anonymous_cannot_register_a_new_speaker():
    r = client.post("/api/v1/hardware/speakers/register", json=_new_node())
    assert r.status_code == 401, r.text


def test_non_admin_cannot_register_a_new_speaker():
    r = client.post("/api/v1/hardware/speakers/register", json=_new_node(), headers=_auth("dbitaimlt022022"))
    assert r.status_code == 403, r.text


def test_admin_registers_a_new_speaker():
    node = _new_node()
    r = client.post("/api/v1/hardware/speakers/register", json=node, headers=_auth("ESDev01"))
    assert r.status_code == 201, r.text
    assert r.json()["mac_address"] == node["mac_address"]


def test_known_speaker_reconnects_without_login():
    node = _new_node()
    assert client.post("/api/v1/hardware/speakers/register", json=node, headers=_auth("ESDev01")).status_code == 201

    r = client.post("/api/v1/hardware/speakers/register", json={**node, "ip_address": "10.0.0.42"})
    assert r.status_code == 201, r.text
    assert r.json()["ip_address"] == "10.0.0.42"
    assert r.json()["status"] == "ONLINE"
