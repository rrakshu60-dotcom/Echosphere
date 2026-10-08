import urllib.request
import json

login_url = "https://echosphere-backend-9lv8.onrender.com/api/v1/auth/login"

users_to_try = [
    ("ESDev01", "Dbit@ES01"),
    ("admin", "admin123"),
    ("admin", "Admin@123"),
    ("ESDev01", "admin123"),
    ("principal", "Principal@123"),
]

for username, password in users_to_try:
    try:
        data = json.dumps({"identifier": username, "password": password}).encode()
        req = urllib.request.Request(
            login_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            res_data = json.loads(res.read().decode())
            print(f"Login SUCCESS for {username}: role={res_data.get('role')}, token={res_data.get('access_token')[:20]}...")
            break
    except Exception as e:
        print(f"Login failed for {username}: {e}")
