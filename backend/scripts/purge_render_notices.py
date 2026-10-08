import urllib.request
import json
import time

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"

# 1. Login as principal to get token
login_data = json.dumps({"identifier": "principal", "password": "Principal@123"}).encode()
req = urllib.request.Request(
    f"{BASE_URL}/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=15) as res:
    auth_resp = json.loads(res.read().decode())
    token = auth_resp.get("access_token")
    print(f"Logged in successfully as {auth_resp.get('role')}!")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# 2. Fetch all announcements on Render
req = urllib.request.Request(f"{BASE_URL}/announcements?limit=200", headers=headers)
with urllib.request.urlopen(req, timeout=15) as res:
    notices = json.loads(res.read().decode())

print(f"Found {len(notices)} notices to delete on Render...")

# 3. Delete each notice via DELETE /announcements/{id}
deleted_count = 0
for n in notices:
    nid = n.get("id")
    title = n.get("title")
    del_req = urllib.request.Request(
        f"{BASE_URL}/announcements/{nid}",
        headers=headers,
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(del_req, timeout=15) as del_res:
            res_json = json.loads(del_res.read().decode())
            print(f"Deleted ID {nid}: '{title}' -> {res_json.get('message')}")
            deleted_count += 1
    except Exception as e:
        print(f"Failed to delete ID {nid} ('{title}'): {e}")
    time.sleep(0.1)

print(f"\nPurged {deleted_count}/{len(notices)} notices from Render.")

# 4. Verify remaining
time.sleep(1)
req = urllib.request.Request(f"{BASE_URL}/announcements?limit=200", headers=headers)
with urllib.request.urlopen(req, timeout=15) as res:
    remaining = json.loads(res.read().decode())
    print(f"Render Verification: {len(remaining)} notices remaining in Render database!")
