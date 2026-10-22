"""
Live check of speaker registration on the production backend (.agents/rules/testing.md §4):
anonymous callers cannot add a new speaker; an admin can.

Registers a tagged throw-away speaker as admin, asserts it was created and listed, and always deletes it,
then fails if any speaker tagged with this run's id is left behind.

    python backend/scripts/live_speaker_registration.py
"""
import os
import secrets
import sys
import time

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

BASE_URL = os.environ.get("ES_LIVE_API", "https://echosphere-backend-9lv8.onrender.com/api/v1")
RUN_ID = secrets.token_hex(3)
TAG = f"[ES-TEST {RUN_ID}]"


def main() -> None:
    login = requests.post(
        f"{BASE_URL}/auth/login",
        json={"identifier": "ESDEV01", "password": os.environ["ES_PASSWORD_ESDEV01"]},
        timeout=30,
    )
    assert login.status_code == 200, f"login failed: {login.status_code}"
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Locally administered MAC (02:...) can never collide with real hardware.
    mac = "02:" + ":".join(f"{b:02X}" for b in secrets.token_bytes(5))
    created_id = None
    try:
        anon = requests.post(
            f"{BASE_URL}/hardware/speakers/register",
            json={"name": f"{TAG} anonymous", "mac_address": mac, "zone": TAG},
            timeout=30,
        )
        assert anon.status_code == 401, f"anonymous new speaker: expected 401, got {anon.status_code}"
        print("PASS anonymous caller cannot add a new speaker -> 401")

        t0 = time.monotonic()
        reg = requests.post(
            f"{BASE_URL}/hardware/speakers/register",
            json={"name": f"{TAG} speaker", "mac_address": mac, "ip_address": "10.255.255.1", "zone": TAG},
            headers=headers,
            timeout=30,
        )
        assert reg.status_code == 201, f"register new MAC: expected 201, got {reg.status_code} {reg.text[:200]}"
        body = reg.json()
        created_id = body["id"]
        assert body["mac_address"].upper() == mac, f"wrong MAC echoed: {body['mac_address']}"
        print(f"PASS register new speaker -> 201 id={created_id} in {time.monotonic() - t0:.2f}s")

        nodes = requests.get(f"{BASE_URL}/hardware/speakers", headers=headers, timeout=30).json()
        assert any(n["id"] == created_id for n in nodes), "new speaker missing from /hardware/speakers"
        print("PASS new speaker is listed")
    finally:
        if created_id is not None:
            requests.delete(f"{BASE_URL}/hardware/speakers/{created_id}", headers=headers, timeout=30)
        leftovers = [
            n for n in requests.get(f"{BASE_URL}/hardware/speakers", headers=headers, timeout=30).json()
            if TAG in (n.get("name") or "") or TAG in (n.get("zone") or "")
        ]
        assert not leftovers, f"cleanup failed, left behind: {[n['id'] for n in leftovers]}"
        print("PASS cleanup: no test speakers left")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
