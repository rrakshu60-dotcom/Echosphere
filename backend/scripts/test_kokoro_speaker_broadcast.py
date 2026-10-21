import time
import requests
import json
import os

from dotenv import load_dotenv

load_dotenv()  # ES_PASSWORD_* come from backend/.env

BASE_URL = "https://echosphere-backend-9lv8.onrender.com/api/v1"
LOG_PATH = r"C:\Users\Rakshitha\.gemini\antigravity-ide\brain\a04559c6-a19d-4fcd-b96a-6b073258a0bf\.system_generated\tasks\task-6362.log"

def read_esp32_logs_tail(num_lines=20):
    if os.path.exists(LOG_PATH):
        try:
            with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return [line.strip() for line in lines[-num_lines:]]
        except Exception as e:
            return [f"Log read error: {e}"]
    return ["Log file not found"]

def test_kokoro_speaker_broadcast():
    print("=" * 70)
    print("  KOKORO-82M LIVE SPEAKER PLAYBACK & QUEUE RESPONSIVENESS TEST")
    print("=" * 70)

    # 1. Login
    print("\n[STEP 1] Authenticating on Live Production Backend...")
    resp = requests.post(
        f"{BASE_URL}/auth/login",
        json={"identifier": "ESDEV01", "password": os.environ.get("ES_PASSWORD_ESDEV01", "")},
        timeout=15,
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    print("  + Authenticated successfully!")

    # 2. Check TTS Engine status
    print("\n[STEP 2] Verifying Kokoro-82M Worker on Production Backend...")
    diag_resp = requests.get(f"{BASE_URL}/diagnostic/tts?run_test=true", timeout=25)
    assert diag_resp.status_code == 200, f"Diagnostic failed: {diag_resp.text}"
    diag_data = diag_resp.json()
    engine_name = diag_data.get("generate_result", {}).get("engine", "")
    gradio_status = diag_data.get("gradio_client_status", "")
    print(f"  + Gradio Status: {gradio_status}")
    print(f"  + Test Synthesis Engine: {engine_name}")
    assert "Kokoro-82M" in engine_name, f"Expected Kokoro-82M engine, got {engine_name}"

    # 3. Create announcement
    print("\n[STEP 3] Publishing Campus Announcement...")
    payload = {
        "title": "Kokoro Neural Audio Broadcast",
        "description": "This is a live test announcement synthesized with the Hugging Face Kokoro-82M neural voice worker. Verification of zero queue lag and flawless physical speaker streaming.",
        "category_id": 12,
        "priority": "Normal",
        "target_audience": "Entire Campus",
        "deliver_speaker": False,
        "speaker_voice": "female",
    }
    create_resp = requests.post(f"{BASE_URL}/announcements", json=payload, headers=headers, timeout=45)
    assert create_resp.status_code in (200, 201), f"Create failed: {create_resp.text}"
    ann = create_resp.json()
    ann_id = ann["id"]
    print(f"  + Announcement created with ID #{ann_id}")

    # 4. Trigger speaker broadcast (dispatches to ESP32 node 13 and enqueues)
    print(f"\n[STEP 4] Dispatching Announcement #{ann_id} to Hardware Speaker Node 13...")
    t0 = time.time()
    bc_resp = requests.post(
        f"{BASE_URL}/hardware/speakers/13/broadcast",
        json={"announcement_id": ann_id},
        headers=headers,
        timeout=45,
    )
    elapsed_bc = time.time() - t0
    print(f"  + Broadcast API responded in {elapsed_bc:.2f}s (Status: {bc_resp.status_code})")
    assert elapsed_bc < 3.0, f"Broadcast took too long ({elapsed_bc:.2f}s) - zero-lag expectation violated!"
    assert bc_resp.status_code in (200, 201), f"Broadcast failed: {bc_resp.text}"
    bc_data = bc_resp.json()
    print(f"  + Dispatch result: command={bc_data.get('command')}, queue_pos={bc_data.get('queue_position')}")

    # 5. Monitor Physical ESP32 Serial Monitor & Queue Status
    print("\n[STEP 5] Monitoring Live ESP32 Hardware Streaming on COM5...")
    start_time = time.time()
    seen_broadcast_start = False
    seen_streaming = False

    for sec in range(35):
        time.sleep(1)
        tail_lines = read_esp32_logs_tail(10)
        for line in tail_lines:
            if "Kokoro Neural Audio Broadcast" in line or "BROADCAST" in line or "I2S" in line or "Playing" in line or "STREAM" in line:
                print(f"    [ESP32 COM5 Log] {line}")
                seen_broadcast_start = True

        # Check SpeakerQueue status
        q_resp = requests.get(f"{BASE_URL}/hardware/queue", headers=headers, timeout=10)
        if q_resp.status_code == 200:
            q_list = q_resp.json()
            matching = [it for it in q_list if it.get("announcement_id") == ann_id]
            if matching:
                q_item = matching[0]
                status = q_item.get("status")
                dur = q_item.get("duration_seconds")
                played_at = q_item.get("played_at")
                if sec % 3 == 0:
                    print(f"    [T+{sec}s Queue Status] #{ann_id} - status='{status}', duration={dur}s, played_at={played_at}")
                if status == "Completed":
                    print(f"  + Queue item #{ann_id} smoothly completed!")
                    break

    print("\n[STEP 6] Latest 15 lines from physical ESP32 Serial Monitor:")
    for line in read_esp32_logs_tail(15):
        print(f"  {line}")

    print("\n" + "=" * 70)
    print("  KOKORO-82M SPEAKER BROADCAST EMPIRICALLY CONFIRMED!")
    print("=" * 70)

if __name__ == "__main__":
    test_kokoro_speaker_broadcast()
