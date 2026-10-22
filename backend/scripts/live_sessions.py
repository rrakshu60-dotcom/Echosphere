"""
Live check of sessions and the sign-in / app-access logs on production (.agents/rules/testing.md §4).

Uses only genuine ESDEV01 sign-ins (log entries are permanent by design, so no fake identifiers or
deliberately wrong passwords are sent). Every session it opens is signed out again.

    python backend/scripts/live_sessions.py
"""
import base64
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
API = os.environ.get("ES_LIVE_API", "https://echosphere-backend-9lv8.onrender.com/api/v1")


def claims(token: str) -> dict:
    body = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))


def login(remember: bool) -> dict:
    res = requests.post(f"{API}/auth/login", json={
        "identifier": "ESDEV01", "password": os.environ["ES_PASSWORD_ESDEV01"],
        "remember_me": remember, "platform": "test",
    }, timeout=30)
    assert res.status_code == 200, f"login: HTTP {res.status_code} {res.text[:200]}"
    return res.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    a = login(remember=True)
    assert a.get("refresh_token") and a.get("session_id"), "login returned no refresh key / session"
    c = claims(a["access_token"])
    lifetime = c["exp"] - time.time()
    assert c.get("sid") == a["session_id"], "access token does not name its session"
    assert 25 * 60 < lifetime <= 30 * 60 + 5, f"access token lifetime {lifetime / 60:.1f} min, expected 30"
    print(f"PASS sign-in opened session #{a['session_id']}; access token lasts {lifetime / 60:.1f} min")

    r = requests.post(f"{API}/auth/refresh", json={"refresh_token": a["refresh_token"], "platform": "test", "app_version": "live-check"}, timeout=30)
    assert r.status_code == 200, f"refresh: HTTP {r.status_code}"
    b = r.json()
    old = requests.post(f"{API}/auth/refresh", json={"refresh_token": a["refresh_token"]}, timeout=30)
    assert old.status_code == 401, f"spent refresh key accepted again: HTTP {old.status_code}"
    print("PASS refresh gave a new key; the old key was refused")

    access = requests.post(f"{API}/auth/access", json={"event": "launch", "platform": "test", "app_version": "live-check"},
                           headers=auth(b["access_token"]), timeout=30)
    assert access.status_code == 204, f"app access: HTTP {access.status_code}"

    admin = auth(b["access_token"])  # ESDEV01 is a Dev Admin
    sign_ins = requests.get(f"{API}/audit/sign-ins", params={"q": "ESDEV01", "page_size": 5}, headers=admin, timeout=30).json()
    mine = [s for s in sign_ins["items"] if s["session_id"] == a["session_id"]]
    assert mine and mine[0]["success"] and mine[0]["platform"] == "test", "sign-in not in the sign-in log"
    print(f"PASS sign-in log has it (IP {mine[0]['ip']}, total entries for ESDEV01: {sign_ins['total']})")

    acc = requests.get(f"{API}/audit/access", params={"q": "live-check", "page_size": 10}, headers=admin, timeout=30).json()
    events = {x["event"] for x in acc["items"] if x["session_id"] == a["session_id"]}
    assert {"refresh", "launch"} <= events, f"app-access log missing events, found {events}"
    print("PASS app-access log has the refresh and the launch")

    second = login(remember=False)
    ended = requests.post(f"{API}/audit/sessions/{second['session_id']}/end", headers=admin, timeout=30)
    assert ended.status_code == 200, f"admin end session: HTTP {ended.status_code}"
    after = requests.get(f"{API}/notifications/", headers=auth(second["access_token"]), timeout=30)
    assert after.status_code == 401, f"ended session still works: HTTP {after.status_code}"
    print("PASS an admin ended a session and its token stopped working at once")

    out = requests.post(f"{API}/auth/logout", headers=auth(b["access_token"]), timeout=30)
    assert out.status_code == 200, f"logout: HTTP {out.status_code}"
    gone = requests.get(f"{API}/notifications/", headers=auth(b["access_token"]), timeout=30)
    assert gone.status_code == 401, f"signed-out token still works: HTTP {gone.status_code}"
    print("PASS sign-out ended the session")

    try:
        import websockets.sync.client as ws_client

        ws_url = API.replace("https://", "wss://") + "/ws/hardware/mic-stream?zone=College-Wide"
        with ws_client.connect(ws_url, open_timeout=20) as ws:
            ws.recv(timeout=10)
        raise AssertionError("live microphone accepted a caller without a session")
    except AssertionError:
        raise
    except Exception as exc:
        code = getattr(getattr(exc, "rcvd", None), "code", None) or getattr(exc, "code", None)
        refused = code in (1008, 403) or "1008" in str(exc) or "403" in str(exc)
        assert refused, f"microphone socket failed for another reason: {exc!r}"
        print(f"PASS live microphone refused a caller without a session ({type(exc).__name__})")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
