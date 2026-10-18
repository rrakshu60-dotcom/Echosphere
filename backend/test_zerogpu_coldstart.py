"""
Unit & Integration Test Suite for Feature 4.1:
Hugging Face ZeroGPU Cold-Start Sleep Latency & 4-Second Fast Fallback.
"""

import os
import sys
import time
from unittest.mock import patch

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Ensure backend root is on sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.tts_service import (
    get_zerogpu_health_status,
    ping_zerogpu_worker,
    start_zerogpu_keepalive_daemon,
    synthesize_remote_kokoro_api,
    generate_announcement_audio_sync,
)


def run_tests():
    print("=" * 70)
    print("🚀 Running EchoSphere Feature 4.1 ZeroGPU Cold-Start Test Suite")
    print("=" * 70)

    # -------------------------------------------------------------
    # Test 1: ZeroGPU Diagnostics & Health API
    # -------------------------------------------------------------
    print("\n--- [1/4] Verifying ZeroGPU Health & Diagnostic Schema ---")
    status = get_zerogpu_health_status()
    assert "fast_fallback_timeout_sec" in status, "Missing fast_fallback_timeout_sec in status"
    assert status["fast_fallback_timeout_sec"] == 4.0, f"Expected 4.0s timeout, got {status['fast_fallback_timeout_sec']}"
    assert "keepalive_daemon_active" in status, "Missing keepalive_daemon_active in status"
    print(f"  [PASS] ZeroGPU Health Schema verified! Configured fast fallback: {status['fast_fallback_timeout_sec']}s")

    # -------------------------------------------------------------
    # Test 2: Background Keep-Alive Daemon Thread Launch
    # -------------------------------------------------------------
    print("\n--- [2/4] Testing ZeroGPU Keep-Alive Daemon Startup ---")
    start_zerogpu_keepalive_daemon()
    time.sleep(0.5)
    status_after = get_zerogpu_health_status()
    assert status_after["keepalive_daemon_active"] is True, "Daemon thread should be active"
    print("  [PASS] ZeroGPU Keep-Alive Daemon thread is actively running in background!")

    # -------------------------------------------------------------
    # Test 3: 4.0-Second Strict Timeout on Hanging/Sleeping Remote Worker
    # -------------------------------------------------------------
    print("\n--- [3/4] Testing 4.0s Cold-Start Timeout Protection ---")
    # Simulate a sleeping ZeroGPU container by mocking a slow gradio inference that takes 10s
    def fake_slow_predict(*args, **kwargs):
        time.sleep(10.0)
        return "fake_audio.wav"

    class FakeClient:
        def predict(self, *args, **kwargs):
            return fake_slow_predict(*args, **kwargs)

    with patch.dict(os.environ, {"KOKORO_API_URL": "https://fake-sleeping-space.hf.space"}):
        with patch("app.services.tts_service._cached_gradio_client", FakeClient()), \
             patch("app.services.tts_service._cached_gradio_url", "https://fake-sleeping-space.hf.space"), \
             patch("app.services.tts_service._openai_endpoint_supported", False):
            start_t = time.time()
            ok = synthesize_remote_kokoro_api(
                text="Test emergency broadcast under cold start",
                output_path="test_coldstart.mp3",
                timeout=4.0,
            )
            elapsed = time.time() - start_t
            print(f"  [INFO] Cold-start fallback returned in {elapsed:.2f}s (result={ok})")
            assert ok is False, "Expected synthesize_remote_kokoro_api to return False upon timeout"
            assert elapsed < 5.5, f"Expected timeout under ~5s, but took {elapsed:.2f}s"
            assert elapsed >= 3.8, f"Expected timeout to wait at least ~4s, but finished in {elapsed:.2f}s"
            print("  [PASS] 4.0-second timeout cutoff successfully prevented 45s hang and returned False!")

    # -------------------------------------------------------------
    # Test 4: Seamless End-to-End Fallback to Edge-TTS
    # -------------------------------------------------------------
    print("\n--- [4/4] Testing Seamless Full Pipeline Edge-TTS Fallback ---")
    # When Kokoro API worker times out, generate_announcement_audio_sync must instantly
    # drop to Edge-TTS without raising an exception and return valid audio!
    with patch.dict(os.environ, {"KOKORO_API_URL": "https://fake-sleeping-space.hf.space"}):
        with patch("app.services.tts_service._cached_gradio_client", FakeClient()), \
             patch("app.services.tts_service._cached_gradio_url", "https://fake-sleeping-space.hf.space"), \
             patch("app.services.tts_service._openai_endpoint_supported", False):
            start_t = time.time()
            result = generate_announcement_audio_sync(
                announcement_id=8888,
                text="Attention all students and faculty. This is an official speech test with ZeroGPU cold start fallback.",
                gender="female",
                accent="american",
                include_chime=False,
            )
            total_elapsed = time.time() - start_t
            print(f"  [INFO] Full announcement speech produced in {total_elapsed:.2f}s!")
            print(f"  [INFO] Fallback Engine Used: {result.get('engine')} | File: {result.get('file_name')}")
            assert result is not None, "Speech generation returned None"
            assert os.path.exists(result["file_path"]), f"Generated file does not exist: {result['file_path']}"
            assert os.path.getsize(result["file_path"]) > 1024, "Generated audio file is too small"
            assert any(k in result.get("engine", "") for k in ("Kokoro", "Neural", "Edge-TTS")), f"Expected valid speech engine, got {result.get('engine')}"
            print(f"  [PASS] Seamless speech fallback succeeded! Generated {os.path.getsize(result['file_path'])} bytes using engine: {result.get('engine')}")

    print("\n" + "=" * 70)
    print("🏆 ALL 4/4 ZEROGPU COLD-START & FALLBACK TESTS PASSED (100% SUCCESS)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
