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


def login(remember: bool, headers: dict | None = None) -> dict:
    res = requests.post(f"{API}/auth/login", json={
        "identifier": "ESDEV01", "password": os.environ["ES_PASSWORD_ESDEV01"],
        "remember_me": remember, "platform": "test",
    }, headers=headers or {}, timeout=30)
    assert res.status_code == 200, f"login: HTTP {res.status_code} {res.text[:200]}"
    return res.json()


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


OPENED: list = []  # access tokens of sessions this run opened; all are signed out at the end


def main() -> None:
    a = login(remember=True)
    OPENED.append(a["access_token"])
    assert a.get("refresh_token") and a.get("session_id"), "login returned no refresh key / session"
    c = claims(a["access_token"])
    lifetime = c["exp"] - time.time()
    assert c.get("sid") == a["session_id"], "access token does not name its session"
    assert 25 * 60 < lifetime <= 30 * 60 + 5, f"access token lifetime {lifetime / 60:.1f} min, expected 30"
    print(f"PASS sign-in opened session #{a['session_id']}; access token lasts {lifetime / 60:.1f} min")

    r = requests.post(f"{API}/auth/refresh", json={"refresh_token": a["refresh_token"], "platform": "test", "app_version": "live-check"}, timeout=30)
    assert r.status_code == 200, f"refresh: HTTP {r.status_code}"
    b = r.json()
    OPENED.append(b["access_token"])
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
    # This machine may reach the backend over IPv4 or IPv6: accept either of its public addresses
    public_ips = set()
    for lookup in ("https://api.ipify.org", "https://api6.ipify.org"):
        try:
            public_ips.add(requests.get(lookup, timeout=10).text.strip())
        except requests.RequestException:
            pass
    assert mine[0]["ip"] in public_ips, f"logged IP {mine[0]['ip']} is not this machine's public IP {public_ips}"
    public_ip = mine[0]["ip"]
    print(f"PASS sign-in log has it, with this machine's real public IP {public_ip}")

    # A forged CF-Connecting-IP never reaches the backend: Cloudflare's edge rejects the request
    edge = requests.post(f"{API}/auth/login", json={"identifier": "ESDEV01", "password": os.environ["ES_PASSWORD_ESDEV01"]},
                         headers={"CF-Connecting-IP": "203.0.113.99"}, timeout=30)
    assert edge.status_code == 403 and "cloudflare" in edge.text.lower(), f"forged CF-Connecting-IP got HTTP {edge.status_code}"
    print("PASS a forged CF-Connecting-IP header is blocked at Cloudflare's edge")

    # A forged X-Forwarded-For passes the edge but does not change the logged IP
    forged = login(remember=False, headers={"X-Forwarded-For": "198.51.100.99"})
    OPENED.append(forged["access_token"])
    entry = [s for s in requests.get(f"{API}/audit/sign-ins", params={"q": "ESDEV01", "page_size": 5}, headers=admin,
                                     timeout=30).json()["items"] if s["session_id"] == forged["session_id"]][0]
    assert entry["ip"] == public_ip, f"forged X-Forwarded-For changed the logged IP to {entry['ip']}"
    print("PASS a forged X-Forwarded-For header did not change the logged IP")

    acc = requests.get(f"{API}/audit/access", params={"q": "live-check", "page_size": 10}, headers=admin, timeout=30).json()
    events = {x["event"] for x in acc["items"] if x["session_id"] == a["session_id"]}
    assert {"refresh", "launch"} <= events, f"app-access log missing events, found {events}"
    print("PASS app-access log has the refresh and the launch")

    second = login(remember=False)
    OPENED.append(second["access_token"])
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

    gone_mic = requests.get(f"{API}/ws/hardware/mic-status", timeout=30)
    assert gone_mic.status_code == 404, f"live microphone endpoint still exists: HTTP {gone_mic.status_code}"
    print("PASS the removed live microphone endpoint is gone")


if __name__ == "__main__":
    try:
        main()
    except AssertionError as exc:
        print(f"FAIL {exc}")
        sys.exit(1)
    finally:
        for token in OPENED:
            requests.post(f"{API}/auth/logout", headers=auth(token), timeout=30)
