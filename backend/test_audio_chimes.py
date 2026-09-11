import os
import sys
import wave

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.chime_service import (
    resolve_contextual_chime,
    generate_chime_pcm,
    get_or_create_chime_wav,
    prepend_chime_to_wav_file,
    STATIC_CHIMES_DIR,
)

def test_chime_system():
    print("=== Testing EchoSphere Dynamic Audio Jingles & Contextual Chimes ===")

    # Test 1: Contextual Chime Resolution
    assert resolve_contextual_chime(priority="EMERGENCY") == "emergency"
    assert resolve_contextual_chime(priority="HIGH", category="Examination") == "urgent_academic"
    assert resolve_contextual_chime(priority="NORMAL", category="Academic") == "urgent_academic"
    assert resolve_contextual_chime(priority="NORMAL", category="Sports") == "events_sports"
    assert resolve_contextual_chime(priority="NORMAL", category="Event") == "events_sports"
    assert resolve_contextual_chime(priority="NORMAL", category="General") == "standard"
    print("[PASS] Test 1: Contextual Chime Resolution correctly categorizes all notice types")

    # Test 2: Acoustic PCM Synthesis for all 4 profiles
    chimes = ["urgent_academic", "events_sports", "emergency", "standard"]
    for c in chimes:
        pcm = generate_chime_pcm(c, sample_rate=24000)
        assert len(pcm) > 4000, f"PCM for {c} too short: {len(pcm)}"
        # Verify 16-bit alignment (even number of bytes)
        assert len(pcm) % 2 == 0, f"PCM for {c} not 16-bit aligned"
    print("[PASS] Test 2: Synthesized pure 16-bit PCM for all 4 chime types")

    # Test 3: Standalone WAV generation
    for c in chimes:
        wav_path = get_or_create_chime_wav(c, sample_rate=24000)
        assert os.path.exists(wav_path), f"WAV file not created: {wav_path}"
        with wave.open(wav_path, "rb") as wf:
            assert wf.getframerate() == 24000, f"Wrong framerate: {wf.getframerate()}"
            assert wf.getnchannels() == 1, f"Wrong channels: {wf.getnchannels()}"
            assert wf.getsampwidth() == 2, f"Wrong sample width: {wf.getsampwidth()}"
            assert wf.getnframes() > 1000
    print("[PASS] Test 3: Generated and validated 24kHz 16-bit WAV files")

    # Test 4: Audio Prepending / Mixing
    dummy_speech_path = os.path.join(STATIC_CHIMES_DIR, "dummy_speech.wav")
    dummy_output_path = os.path.join(STATIC_CHIMES_DIR, "dummy_chime_speech.wav")

    # Create dummy speech wav (0.5s silence)
    with wave.open(dummy_speech_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 12000)

    ok = prepend_chime_to_wav_file(dummy_speech_path, dummy_output_path, chime_type="urgent_academic")
    assert ok is True, "prepend_chime_to_wav_file failed"
    assert os.path.exists(dummy_output_path), "output wav missing"

    with wave.open(dummy_output_path, "rb") as out_wf:
        assert out_wf.getnframes() > 12000, "Output not longer than original speech"

    # Clean up test scratch files
    if os.path.exists(dummy_speech_path):
        os.remove(dummy_speech_path)
    if os.path.exists(dummy_output_path):
        os.remove(dummy_output_path)

    print("[PASS] Test 4: Audio chime seamlessly prepended to speech WAV stream")
    print("\nAll audio chime tests passed successfully!")


def test_gender_voice_isolation():
    from app.services.tts_service import resolve_voice_profile, STATIC_AUDIO_DIR
    from app.api.v1.announcement import _find_cached_audio_file

    # 1. Voice profile resolution
    kok_vf, _, edge_vf, name_vf = resolve_voice_profile("female", "american")
    kok_vm, _, edge_vm, name_vm = resolve_voice_profile("male", "american")

    assert "Jenny" in name_vf or "bella" in kok_vf or "Female" in name_vf
    assert "Guy" in name_vm or "michael" in kok_vm or "Male" in name_vm
    assert edge_vf != edge_vm, "Female and Male voices must use distinct neural profiles"

    # 2. Strict cache isolation between male and female
    test_female_file = os.path.join(STATIC_AUDIO_DIR, "announcement_7777_american_female_standard.mp3")
    try:
        with open(test_female_file, "wb") as f:
            f.write(b"RIFF" + b"\x00" * 2000)

        # Look up for male when only female exists must return None
        fname, fpath, _ = _find_cached_audio_file(7777, "american_male", "standard")
        assert fname is None and fpath is None, f"Cross-contamination: Male search returned {fname}"

        # Look up for female must find the female file
        fname_f, fpath_f, _ = _find_cached_audio_file(7777, "american_female", "standard")
        assert fname_f == "announcement_7777_american_female_standard.mp3"
    finally:
        if os.path.exists(test_female_file):
            os.remove(test_female_file)


if __name__ == "__main__":
    test_chime_system()
    test_gender_voice_isolation()
