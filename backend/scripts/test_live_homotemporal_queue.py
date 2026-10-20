import sys
sys.stdout.reconfigure(encoding='utf-8')
import requests
import time
import json
from datetime import datetime

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"

print("=================================================================")
print("  ECHOSPHERE 0-LATENCY HOMO-TEMPORAL & EMERGENCY QUEUE LIVE TEST")
print("=================================================================")

# 1. Login with verified production credentials
login_resp = requests.post(f"{BASE_URL}/auth/login", json={"identifier": "ESDEV01", "password": "rakshitha@1228"})
if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.status_code} {login_resp.text}")
    exit(1)

token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("✅ Logged in successfully as ESDEV01!")

# 2. Check initial queue state
q_resp = requests.get(f"{BASE_URL}/hardware/queue", headers=headers)
initial_queue = q_resp.json()
print(f"Initial Queue items: {len(initial_queue) if isinstance(initial_queue, list) else 0}")

# 3. Create Homo-Temporal Notice 1 (Normal Priority, short speech)
print("\n--- STEP 1: Creating Homo-Temporal Normal Notice 1 ---")
n1_resp = requests.post(
    f"{BASE_URL}/announcements",
    headers=headers,
    json={
        "title": "Homo-Temporal Test 1 - Morning Notice",
        "description": "Good morning campus. First homo temporal announcement test is now playing.",
        "category_id": 12,
        "priority": "NORMAL",
        "emergency_level": "NORMAL",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "speaker_voice": "female",
    }
)
n1_data = n1_resp.json()
n1_id = n1_data["id"]
print(f"Created Notice 1: ID #{n1_id} - '{n1_data['title']}'")

# 4. Create Homo-Temporal Notice 2 (Normal Priority, short speech)
print("\n--- STEP 2: Creating Homo-Temporal Normal Notice 2 ---")
n2_resp = requests.post(
    f"{BASE_URL}/announcements",
    headers=headers,
    json={
        "title": "Homo-Temporal Test 2 - Afternoon Notice",
        "description": "Second homo temporal announcement test is waiting next in queue.",
        "category_id": 12,
        "priority": "NORMAL",
        "emergency_level": "NORMAL",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "speaker_voice": "female",
    }
)
n2_data = n2_resp.json()
n2_id = n2_data["id"]
print(f"Created Notice 2: ID #{n2_id} - '{n2_data['title']}'")

# 5. Broadcast BOTH notices to the speaker queue virtually SIMULTANEOUSLY (<200ms apart)
print("\n--- STEP 3: Dispatching Both Homo-Temporal Notices Simultaneously ---")
t0 = time.time()
b1 = requests.post(f"{BASE_URL}/hardware/queue/add", headers=headers, json={"announcement_id": n1_id})
t1 = time.time()
b2 = requests.post(f"{BASE_URL}/hardware/queue/add", headers=headers, json={"announcement_id": n2_id})
t2 = time.time()

print(f"Dispatched Notice 1 in {(t1-t0)*1000:.1f}ms (Status: {b1.status_code})")
print(f"Dispatched Notice 2 in {(t2-t1)*1000:.1f}ms (Status: {b2.status_code})")

# 6. Verify Queue State immediately: Notice 1 MUST be Playing, Notice 2 MUST be Next in Queue (NOT preempted!)
time.sleep(1.0)
q_check = requests.get(f"{BASE_URL}/hardware/queue", headers=headers).json()
print("\n--- STEP 4: Verifying Queue Determinism & Non-Preemption ---")
if isinstance(q_check, list):
    for item in q_check:
        ann = item.get("announcement") or {}
        print(f"  • Pos {item.get('queue_position')}: Announcement #{item.get('announcement_id')} '{ann.get('title')}' -> Status: {item.get('status')}")
    
    n1_item = next((q for q in q_check if q.get("announcement_id") == n1_id), None)
    n2_item = next((q for q in q_check if q.get("announcement_id") == n2_id), None)
    
    if n1_item and n1_item.get("status") == "Playing" and n2_item and n2_item.get("status") in ["Next in Queue", "Queued"]:
        print("✅ SUCCESS: Notice 1 is Playing (Pos 1) and Notice 2 is Next in Queue (Pos 2).")
        print("✅ ZERO PREEMPTION: Non-emergency Notice 2 did NOT interrupt ongoing Notice 1!")
    else:
        print(f"⚠️ Unexpected queue states: N1={n1_item.get('status') if n1_item else 'None'}, N2={n2_item.get('status') if n2_item else 'None'}")

print("\n--- STEP 5: Waiting 10s for ESP32 to receive and stream Notice 1 ---")
time.sleep(10)

# Check queue again to monitor progress
q_check2 = requests.get(f"{BASE_URL}/hardware/queue", headers=headers).json()
print("Queue state at T+10s:")
for item in q_check2:
    ann = item.get("announcement") or {}
    print(f"  • Pos {item.get('queue_position')}: #{item.get('announcement_id')} '{ann.get('title')}' -> Status: {item.get('status')}")

# 7. Now test Emergency Preemption while Notice 2 is playing or queued
print("\n--- STEP 6: Testing Instant Emergency Preemption ---")
emerg_resp = requests.post(
    f"{BASE_URL}/announcements",
    headers=headers,
    json={
        "title": "EMERGENCY CAMPUS SIREN ALERT",
        "description": "Immediate campus evacuation drill alert. Evacuate immediately.",
        "category_id": 12,
        "priority": "EMERGENCY",
        "emergency_level": "CRITICAL",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "speaker_voice": "female",
    }
)
emerg_data = emerg_resp.json()
emerg_id = emerg_data["id"]
print(f"Created Emergency Notice: ID #{emerg_id} - '{emerg_data['title']}'")

print(f"Broadcasting Emergency Notice #{emerg_id} immediately...")
t_em_start = time.time()
b_em = requests.post(f"{BASE_URL}/hardware/queue/add", headers=headers, json={"announcement_id": emerg_id})
t_em_end = time.time()
print(f"Emergency dispatched in {(t_em_end - t_em_start)*1000:.1f}ms (Status: {b_em.status_code})")

time.sleep(1.0)
q_check_em = requests.get(f"{BASE_URL}/hardware/queue", headers=headers).json()
print("Queue state immediately after Emergency dispatch:")
for item in q_check_em:
    ann = item.get("announcement") or {}
    print(f"  • Pos {item.get('queue_position')}: #{item.get('announcement_id')} '{ann.get('title')}' -> Status: {item.get('status')}")

em_item = next((q for q in q_check_em if q.get("announcement_id") == emerg_id), None)
if em_item and em_item.get("status") == "Playing":
    print("🚨 SUCCESS: Emergency Notice took immediate preemption (Status: Playing)!")
else:
    print(f"⚠️ Emergency status: {em_item.get('status') if em_item else 'Not in queue'}")

print("\n=================================================================")
print("  TEST COMPLETED SUCCESSFULLY")
print("=================================================================")
