import os

from dotenv import load_dotenv

load_dotenv()  # ES_PASSWORD_* come from backend/.env
import requests
import time
import json

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"

# 1. Login as admin
login_resp = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "ESDEV01", "password": os.environ.get("ES_PASSWORD_ESDEV01", "")})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.status_code} {login_resp.text}")
    exit(1)

token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("Logged in successfully as ESDEV01!")

# 2. Check current queue
q_resp = requests.get(f"{BASE_URL}/hardware/queue", headers=headers)
print(f"Current Queue Status ({q_resp.status_code}):")
queue_data = q_resp.json()
if isinstance(queue_data, list):
    playing = next((q for q in queue_data if q.get("status") == "Playing"), None)
    print(f"Playing item: {playing}")
    print(f"Active items count: {len(queue_data)}")
else:
    print(f"Playing item: {queue_data.get('now_playing')}")
    print(f"Active items count: {len(queue_data.get('items', []))}")

# 3. Create a normal notice with 30s audio
print("\n--- Creating Long Normal Notice (Notice A) ---")
a_resp = requests.post(
    f"{BASE_URL}/announcements",
    headers=headers,
    json={
        "title": "Normal Notice A - Library Book Return Notice",
        "description": "All students and faculty members who have borrowed books from the central college library are requested to return them before Friday afternoon. Late returns will incur a standard overdue penalty fee.",
        "category_id": 12,
        "priority": "NORMAL",
        "emergency_level": "NORMAL",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "deliver_push": False,
        "speaker_voice": "female",
    }
)
print(f"Created Notice A: {a_resp.status_code}")
ann_a = a_resp.json()
ann_a_id = ann_a["id"]
print(f"Notice A ID: {ann_a_id}, Title: {ann_a['title']}")

# Broadcast Notice A to hardware queue
print(f"Broadcasting Notice A (#{ann_a_id}) to speakers...")
b_a_resp = requests.post(
    f"{BASE_URL}/hardware/queue/add",
    headers=headers,
    json={"announcement_id": ann_a_id}
)
print(f"Broadcast Notice A response: {b_a_resp.status_code}")

print("\nWaiting 4 seconds for ESP32 on COM5 to fetch Notice A and begin audio playback...")
for i in range(4, 0, -1):
    print(f"T-{i}s...", flush=True)
    time.sleep(1)

# Check queue status to confirm Notice A is Playing
q_resp2 = requests.get(f"{BASE_URL}/hardware/queue", headers=headers).json()
if isinstance(q_resp2, list):
    playing_a = next((q for q in q_resp2 if q.get("status") == "Playing"), None)
    print(f"Queue Status during Notice A: Playing = {playing_a.get('announcement_id') if playing_a else None}", flush=True)
else:
    print(f"Queue Status during Notice A: Playing = {q_resp2.get('now_playing', {}).get('announcement_id')}", flush=True)

# 4. Now create an EMERGENCY Notice B
print("\n--- Creating EMERGENCY Notice B ---", flush=True)
b_resp = requests.post(
    f"{BASE_URL}/announcements",
    headers=headers,
    json={
        "title": "EMERGENCY EVACUATION DRILL ALERT",
        "description": "Attention campus! This is an immediate emergency priority broadcast. Please evacuate all academic blocks and proceed directly to assembly point Alpha.",
        "category_id": 12,
        "priority": "EMERGENCY",
        "emergency_level": "CRITICAL",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "deliver_push": True,
        "speaker_voice": "female",
    }
)
print(f"Created Notice B: {b_resp.status_code}", flush=True)
ann_b = b_resp.json()
ann_b_id = ann_b["id"]
print(f"Emergency Notice B ID: {ann_b_id}, Priority: {ann_b['priority']}, Emergency Level: {ann_b['emergency_level']}", flush=True)

# Broadcast Emergency Notice B
print(f"Broadcasting Emergency Notice B (#{ann_b_id}) to speakers...", flush=True)
b_b_resp = requests.post(
    f"{BASE_URL}/hardware/queue/add",
    headers=headers,
    json={"announcement_id": ann_b_id}
)
print(f"Broadcast Notice B response: {b_b_resp.status_code}", flush=True)

# Monitor queue and node response over next 25 seconds
print("\nMonitoring queue state after emergency broadcast (watching for Preemption -> Playing Emergency -> Resuming Paused Notice):", flush=True)
for i in range(25):
    time.sleep(1)
    q_check = requests.get(f"{BASE_URL}/hardware/queue", headers=headers).json()
    items = q_check if isinstance(q_check, list) else q_check.get("items", [])
    now_p = next((q for q in items if q.get("status") == "Playing"), None)
    paused = [q for q in items if q.get("status") == "Paused"]
    queued = [q for q in items if q.get("status") in ("Next in Queue", "Queued")]
    
    now_id = now_p.get("announcement_id") if now_p else None
    now_title = now_p.get("announcement", {}).get("title") if (now_p and isinstance(now_p.get("announcement"), dict)) else (now_p.get("title") if now_p else "None")
    
    paused_ids = [q.get("announcement_id") for q in paused]
    queued_ids = [q.get("announcement_id") for q in queued]
    print(f"[T+{i+1:02d}s] Playing: #{now_id} ('{now_title}') | Paused: {paused_ids} | Queued: {queued_ids}", flush=True)



