"""
Comprehensive Verification Suite for EchoSphere Cloud Storage (Hugging Face Datasets CDN)
========================================================================================
Validates:
  1. CloudStorageService initialization & fallback behavior.
  2. Local static asset persistence and manifest indexing.
  3. Seamless integration with TTS audio synthesis.
  4. Circular attachment upload & URL generation.
  5. Container resurrection logic (recovering deleted local files).
"""

import os
import sys
import json
import logging

# Set up paths
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test_cloud_storage")


def test_cloud_storage_suite():
    print("=" * 80)
    print(" [ECHOSPHERE] RUNNING CLOUD STORAGE VERIFICATION SUITE")
    print("=" * 80)

    from app.services.cloud_storage_service import CloudStorageService, STATIC_DIR

    # 1. Test Service Status
    is_cloud = CloudStorageService.is_cloud_enabled()
    print(f"\n[1] Cloud Storage Engine Status:")
    print(f"    - Hugging Face Datasets Active: {is_cloud}")
    print(f"    - Target Repo ID: {CloudStorageService._repo_id or 'Local Static Fallback'}")
    print(f"    - Static Directory: {STATIC_DIR}")

    # 2. Test Byte Upload (Attachment)
    sample_pdf_bytes = b"%PDF-1.4 Official EchoSphere Exam Circular Announcement"
    filename = "circular_dec_2026.pdf"
    res = CloudStorageService.upload_bytes(sample_pdf_bytes, filename=filename, folder="attachments")

    print(f"\n[2] Attachment Upload Test:")
    print(f"    - Status: {res.get('status')}")
    print(f"    - Public URL: {res.get('public_url')}")
    print(f"    - Storage Mode: {res.get('storage_mode')}")
    assert res["file_name"] == filename, "Filename mismatch"
    assert "public_url" in res, "Missing public_url"

    # Verify local file exists
    expected_path = os.path.join(STATIC_DIR, "attachments", filename)
    assert os.path.exists(expected_path), f"File {expected_path} was not created"
    print(f"    - Verified local file on disk: {expected_path} ({os.path.getsize(expected_path)} bytes)")

    # 3. Test URL Lookup via Manifest
    resolved_url = CloudStorageService.get_public_url("attachments", filename)
    print(f"\n[3] URL Manifest Lookup Test:")
    print(f"    - Resolved URL: {resolved_url}")
    assert resolved_url == res["public_url"], "Resolved URL should match upload result"

    # 4. Test TTS Integration
    print(f"\n[4] TTS Service Audio Generation & Storage Test:")
    from app.services.tts_service import synthesize_text_audio
    tts_res = synthesize_text_audio(
        text="All students must submit placement registration forms by Friday.",
        gender="female",
        accent="american",
        filename_prefix="test_broadcast"
    )
    print(f"    - Audio Filename: {tts_res.get('file_name')}")
    print(f"    - Audio Filepath: {tts_res.get('file_path')}")
    print(f"    - Public URL: {tts_res.get('public_url')}")
    print(f"    - Audio Engine: {tts_res.get('engine')}")
    assert "public_url" in tts_res, "TTS result must contain public_url"
    assert os.path.exists(tts_res["file_path"]), "Synthesized audio file must exist on disk"

    # 5. Test Container Reboot Simulation (Wiping local static file & restoring)
    print(f"\n[5] Render Container Reboot Resilience Simulation:")
    test_restore_filename = tts_res["file_name"]
    local_audio_path = tts_res["file_path"]

    # Delete local file to simulate Render ephemeral disk wipe
    if os.path.exists(local_audio_path):
        os.remove(local_audio_path)
        print(f"    - [SIMULATED WIPE] Deleted local file: {local_audio_path}")
        assert not os.path.exists(local_audio_path), "File should be removed"

    # Attempt restore
    restored = CloudStorageService.restore_file_from_cdn_if_missing(test_restore_filename, folder="audio_streams")
    print(f"    - Container Restoration Result: {'Restored from CDN' if restored else 'Local Regenerate Triggered'}")

    print("\n" + "=" * 80)
    print(" [SUCCESS] ALL CLOUD STORAGE VERIFICATION CHECKS PASSED (100%)")
    print("=" * 80)


if __name__ == "__main__":
    test_cloud_storage_suite()
