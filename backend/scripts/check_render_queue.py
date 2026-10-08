import urllib.request
import json

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"

# Login as principal
login_data = json.dumps({"identifier": "principal", "password": "Principal@123"}).encode()
req = urllib.request.Request(
    f"{BASE_URL}/auth/login",
    data=login_data,
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
    method="POST"
)

with urllib.request.urlopen(req, timeout=15) as res:
    token = json.loads(res.read().decode()).get("access_token")

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# Check speaker queue
try:
    req = urllib.request.Request(f"{BASE_URL}/hardware/queue", headers=headers)
    with urllib.request.urlopen(req, timeout=15) as res:
        queue = json.loads(res.read().decode())
        print(f"Render Speaker Queue: {len(queue)} items")
        for item in queue:
            qid = item.get("id")
            del_req = urllib.request.Request(f"{BASE_URL}/hardware/queue/{qid}", headers=headers, method="DELETE")
            try:
                urllib.request.urlopen(del_req, timeout=10)
                print(f"  Deleted queue item {qid}")
            except Exception as e:
                print(f"  Error deleting queue item {qid}: {e}")
except Exception as e:
    print("Error checking queue:", e)

# Final check announcements
req = urllib.request.Request(f"{BASE_URL}/announcements?limit=100", headers=headers)
with urllib.request.urlopen(req, timeout=15) as res:
    notices = json.loads(res.read().decode())
    print(f"Render Final Announcements Count: {len(notices)}")
