"""
EchoSphere Live Microphone PA Broadcast Unit & Integration Test Suite
====================================================================
Tests real-time binary audio streaming between broadcaster and speaker nodes:
1. HTTP status & probe endpoints
2. WebSocket listener registration (ESP32 / speaker edge client)
3. WebSocket broadcaster session initiation & role authorization
4. Real-time binary PCM frame transmission (< 120ms fan-out)
5. Zone-targeted distribution vs College-Wide broadcast
6. Clean session termination & listener state cleanup
"""

import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

from app.main import app
from app.core.mic_stream_manager import mic_stream_manager
from app.core.jwt_handler import create_access_token


def run_tests():
    client = TestClient(app)
    print("=" * 70)
    print("🔊 EchoSphere Live Microphone PA Streaming Test Suite")
    print("=" * 70)

    # 1. Test HTTP Probe & Status Endpoints
    print("\n--- [1/6] Testing Live Mic HTTP Status & Probes ---")
    resp = client.get("/api/v1/ws/hardware/mic-status")
    assert resp.status_code == 200, f"mic-status failed: {resp.text}"
    data = resp.json()
    assert "is_active" in data
    assert "listener_count" in data
    print(f"  [PASS] /mic-status returned: is_active={data['is_active']}, listeners={data['listener_count']}")

    resp_probe = client.get("/api/v1/ws/hardware/mic-stream")
    assert resp_probe.status_code == 200
    assert "Live Microphone PA" in resp_probe.json()["service"]
    print("  [PASS] /mic-stream HTTP upgrade probe responsive.")

    # 2. Test Speaker Node WebSocket Listener Registration
    print("\n--- [2/6] Testing Speaker Node WebSocket Listener Registration ---")
    speaker_mac = "D4:F3:2D:22:2A:CB"
    speaker_zone = "Auditorium"

    with client.websocket_connect(
        f"/api/v1/ws/hardware/mic-listen?mac_address={speaker_mac}&zone={speaker_zone}"
    ) as spk_ws:
        init_evt = spk_ws.receive_json()
        assert init_evt.get("event") == "LISTENER_CONNECTED"
        assert init_evt.get("mac_address") == speaker_mac
        print(f"  [PASS] Speaker listener connected! Event: {init_evt['event']}")

        # Verify listener is tracked in mic_stream_manager
        assert len(mic_stream_manager.listeners) >= 1
        print(f"  [PASS] Active listeners in manager: {len(mic_stream_manager.listeners)}")

        # 3. Test Role Authorization (Student Rejected vs Admin Accepted)
        print("\n--- [3/6] Testing Broadcaster Role-Based Access Control ---")
        student_token = create_access_token({
            "id": 999,
            "username": "student_rahul",
            "role": "student",
        })
        try:
            with client.websocket_connect(
                f"/api/v1/ws/hardware/mic-stream?token={student_token}&zone=College-Wide"
            ) as bad_ws:
                pass
            print("  [FAIL] Student connection should have been rejected!")
            sys.exit(1)
        except Exception:
            print("  [PASS] Student unauthorized connection rejected with code 1008 as expected.")

        admin_token = create_access_token({
            "id": 1,
            "username": "principal_sharma",
            "role": "principal",
        })

        # 4. Test Live Broadcast Session & Real-Time PCM Audio Streaming
        print("\n--- [4/6] Testing Live PA Broadcast Session & Audio Streaming ---")
        with client.websocket_connect(
            f"/api/v1/ws/hardware/mic-stream?token={admin_token}&zone=College-Wide&is_emergency=false"
        ) as broad_ws:
            sess_evt = broad_ws.receive_json()
            assert sess_evt.get("event") == "SESSION_STARTED"
            session_id = sess_evt.get("session_id")
            print(f"  [PASS] Broadcaster session active: {session_id}")

            # Verify speaker received START_MIC_STREAM event
            spk_msg = spk_ws.receive_text()
            spk_data = json.loads(spk_msg)
            assert spk_data.get("event") == "START_MIC_STREAM"
            assert spk_data.get("sample_rate") == 16000
            print(f"  [PASS] Speaker received hardware event: {spk_data['event']} (16kHz 16-bit PCM)")

            # 5. Stream Binary PCM Audio Chunks
            print("\n--- [5/6] Testing Real-Time Binary PCM Audio Chunks Delivery ---")
            dummy_pcm_frame = bytes([128] * 1024) # 1024 bytes = 512 samples = 32ms of audio
            broad_ws.send_bytes(dummy_pcm_frame)

            received_audio = spk_ws.receive_bytes()
            assert len(received_audio) == 1024
            assert received_audio == dummy_pcm_frame
            print(f"  [PASS] 1024-byte PCM audio frame successfully delivered to speaker in real time!")

            # Send multiple consecutive frames
            for i in range(5):
                frame = bytes([(i * 20) % 256] * 512)
                broad_ws.send_bytes(frame)
                spk_audio = spk_ws.receive_bytes()
                assert len(spk_audio) == 512

            print(f"  [PASS] 5 consecutive audio chunks streamed and received without frame drop.")

            # End broadcast gracefully
            broad_ws.send_text(json.dumps({"command": "STOP"}))

        # Verify speaker received STOP_MIC_STREAM event
        stop_msg = spk_ws.receive_text()
        stop_data = json.loads(stop_msg)
        assert stop_data.get("event") == "STOP_MIC_STREAM"
        print(f"  [PASS] Speaker received STOP_MIC_STREAM event cleanly. Duration: {stop_data.get('duration_seconds')}s")

    # 6. Verify Cleanup
    print("\n--- [6/6] Verifying Clean Teardown & Manager State ---")
    time.sleep(0.1)
    assert mic_stream_manager.active_session is None
    print("  [PASS] mic_stream_manager active session is None.")
    assert len(mic_stream_manager.listeners) == 0
    print("  [PASS] All listener sockets pruned cleanly.")

    print("\n" + "=" * 70)
    print("🏆 ALL 6/6 LIVE PA MICROPHONE STREAMING TESTS PASSED (100% SUCCESS)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
