import requests
import time
import json
from datetime import datetime, timezone, timedelta

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"

def run_live_verification():
    print("\n" + "="*70)
    print("  LIVE FULL-STACK EMPIRICAL VERIFICATION: REPEAT SCHEDULE FIX")
    print("="*70 + "\n")

    # 1. Login
    print("[STEP 1] Authenticating with Live Backend (ESDEV01)...")
    login_res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"identifier": "ESDEV01", "password": "rakshitha@1228"},
        timeout=15,
    )
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("  [OK] Authenticated! Bearer token obtained.")

    # 2. Inspect initial queue and clean up any completed/stuck items
    print("\n[STEP 2] Inspecting live speaker queue...")
    q_res = requests.get(f"{BASE_URL}/hardware/queue", headers=headers, timeout=15)
    initial_queue = q_res.json() if q_res.status_code == 200 else []
    print(f"  [OK] Initial queue length: {len(initial_queue)}")
    for item in initial_queue:
        print(f"    - ID: {item.get('id')}, Ann: #{item.get('announcement_id')}, Status: {item.get('status')}, Sched: {item.get('scheduled_time')}")

    # Calculate IST time: Custom window starting 20 minutes from now
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    ist_now = utc_now + timedelta(hours=5, minutes=30)
    repeat_time_ist = ist_now + timedelta(minutes=20)
    custom_start = repeat_time_ist.strftime("%H:%M")
    custom_end = (repeat_time_ist + timedelta(minutes=30)).strftime("%H:%M")

    print(f"\n[STEP 3] Current IST: {ist_now.strftime('%H:%M:%S')}")
    print(f"  -> Setting Custom Repeat Window for: {custom_start} - {custom_end} (20 mins in future)")

    # 3. Create notice with Publish Now (play_on_publish=True) + Custom Repeat Window
    ann_payload = {
        "title": "Semester Grade Card Distribution Notice",
        "description": "Grade cards for the previous semester are now available at the administrative office.",
        "category_id": 12,
        "priority": "Normal",
        "deliver_speaker": True,
        "deliver_in_app": True,
        "deliver_push": False,
        "speaker_voice": "female",
        "repeat_schedule": {
            "repeat_mode": "CUSTOM",
            "selected_slots": ["CUSTOM_WINDOW"],
            "custom_start_time": custom_start,
            "custom_end_time": custom_end,
            "play_on_publish": True,
            "max_repeats": 3,
            "target_scope": "COLLEGE_WIDE",
            "start_date": (utc_now - timedelta(hours=1)).isoformat(),
            "end_date": (utc_now + timedelta(hours=24)).isoformat(),
            "event_datetime": (utc_now + timedelta(hours=20)).isoformat(),
            "force_enable_speaker": True,
        }
    }

    print("\n[STEP 4] Publishing Notice on Live Production with Publish Now + Future Repeat Window...")
    create_res = requests.post(f"{BASE_URL}/announcements", json=ann_payload, headers=headers, timeout=20)
    assert create_res.status_code in (200, 201), f"Announcement creation failed: {create_res.text}"
    ann_data = create_res.json()
    ann_id = ann_data["id"]
    print(f"  [OK] Announcement #{ann_id} successfully created: '{ann_data['title']}'")

    # 4. Monitor Speaker Queue for Round 1
    print("\n[STEP 5] Verifying Round 1 starts playing immediately on speaker node...")
    time.sleep(2)
    q_res2 = requests.get(f"{BASE_URL}/hardware/queue", headers=headers, timeout=15)
    queue2 = q_res2.json()
    our_q = next((q for q in queue2 if q.get("announcement_id") == ann_id), None)
    assert our_q is not None, "Announcement was not enqueued in SpeakerQueue!"
    q_id = our_q["id"]
    status_round1 = our_q.get("status")
    print(f"  [OK] Queue Item #{q_id} status: '{status_round1}' (Round 1 playing)")

    # 5. Wait for audio playback or simulate complete signal
    print(f"\n[STEP 6] Waiting for Round 1 audio playback to complete (dur: {our_q.get('duration_seconds', 8)}s)...")
    time.sleep(our_q.get('duration_seconds', 8) + 2)

    # Call complete action if still playing
    comp_res = requests.post(
        f"{BASE_URL}/hardware/speaker-queue/{q_id}/status?action=complete",
        headers=headers,
        timeout=15,
    )
    print(f"  [OK] Complete response: {comp_res.json().get('message', comp_res.json())}")

    # 6. CRITICAL VERIFICATION:
    # Check queue status immediately after Round 1 complete!
    print("\n[STEP 7] CRITICAL CHECK: Inspecting Queue Status After Round 1 Playback Finishes...")
    time.sleep(2)
    q_res3 = requests.get(f"{BASE_URL}/hardware/queue", headers=headers, timeout=15)
    queue3 = q_res3.json()
    our_q_after = next((q for q in queue3 if q.get("announcement_id") == ann_id), None)
    active_playing = [q for q in queue3 if q.get("status") == "Playing"]

    print(f"  -> Announcement #{ann_id} Status: '{our_q_after.get('status') if our_q_after else 'Not in active queue'}'")
    print(f"  -> Scheduled Time: {our_q_after.get('scheduled_time') if our_q_after else 'N/A'}")
    print(f"  -> Currently Playing Items in Queue: {len(active_playing)}")
    for ap in active_playing:
        print(f"     * Playing: #{ap.get('announcement_id')} ('{ap.get('announcement', {}).get('title')}')")

    # Fetch Repeat Schedule details
    sched_res = requests.get(f"{BASE_URL}/repeat-schedules/{ann_id}", headers=headers, timeout=15)
    sched_data = sched_res.json()
    print(f"  -> Repeat Schedule total_played_count: {sched_data.get('total_played_count')}")
    print(f"  -> Repeat Schedule next_repeat_at: {sched_data.get('next_repeat_at')}")

    # VERIFY:
    assert sched_data.get("total_played_count") == 1, f"Expected total_played_count=1, got {sched_data.get('total_played_count')}"
    assert our_q_after is not None, "Item should remain in queue for future repeat!"
    assert our_q_after.get("status") == "Queued", f"Expected status 'Queued' (waiting for {custom_start}), but got '{our_q_after.get('status')}'!"
    assert len(active_playing) == 0, f"No notice should be playing now! Found {len(active_playing)} playing notices!"

    print("\n" + "="*70)
    print(f"  SUCCESS: Notice #{ann_id} played Round 1 on publish, and is now cleanly")
    print(f"  QUEUED waiting for scheduled repeat at {custom_start} IST ({sched_data.get('next_repeat_at')})!")
    print(f"  NO PREMATURE REPEAT LOOP OCCURRED! Speaker queue is properly IDLE.")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_live_verification()
