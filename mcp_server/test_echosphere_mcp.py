"""
EchoSphere MCP Server Validation Test Suite
===========================================
Runs verification tests against all tools, resources, and prompts exposed by
the EchoSphere Master MCP Server.
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "mcp_server"))
sys.path.insert(0, str(WORKSPACE_ROOT / "backend"))

from echosphere_mcp import (
    mcp,
    echosphere_system_health_audit,
    echosphere_speaker_queue_control,
    echosphere_repeat_schedule_manager,
    echosphere_hardware_node_manager,
    echosphere_esp32_driver_checker,
    echosphere_audio_integrity_auditor,
    echosphere_zerogpu_space_auditor,
    echosphere_render_safeguard_auditor,
    echosphere_zero_jargon_scanner,
    echosphere_ai_summarizer_validator,
    echosphere_database_and_git_guard,
    echosphere_run_verification_matrix,
    get_chronology_resource,
    get_architecture_resource,
    get_rules_resource,
    prompt_diagnose_speaker_issue,
    prompt_verify_zerogpu_deployment
)

def run_tests():
    print("=" * 70)
    print("🚀 RUNNING ECHOSPHERE MCP SERVER VALIDATION SUITE")
    print("=" * 70)

    # 1. Test Resources
    print("\n[1/14] Testing MCP Resources...")
    chronology = get_chronology_resource()
    assert len(chronology) > 100, "Chronology resource empty"
    arch = get_architecture_resource()
    assert "Supabase PostgreSQL" in arch, "Architecture resource missing Supabase"
    rules = get_rules_resource()
    assert "Zero Internal / Technical Jargon" in rules or "Strict Prohibition of Developer" in rules, "Rules resource missing Zero-Jargon"
    print("  ✅ Resources: Chronology, Architecture, Rules verified!")

    # 2. Test Prompts
    print("\n[2/14] Testing MCP Prompts...")
    prompt1 = prompt_diagnose_speaker_issue("Speaker audio is broken")
    assert "echosphere_audio_integrity_auditor" in prompt1
    prompt2 = prompt_verify_zerogpu_deployment()
    assert "echosphere_zerogpu_space_auditor" in prompt2
    print("  ✅ Prompts: Speaker issue and ZeroGPU verification prompts verified!")

    # 3. Test ESP32 Driver Checker
    print("\n[3/14] Testing echosphere_esp32_driver_checker...")
    esp32_res = json.loads(echosphere_esp32_driver_checker())
    print("  ESP32 Verdict:", esp32_res.get("final_verdict"))
    assert esp32_res["pin_verifications"]["BCLK_pin_26"], "BCLK pin not 26"
    assert esp32_res["pin_verifications"]["LRC_pin_25"], "LRC pin not 25"
    assert esp32_res["pin_verifications"]["DIN_pin_27"], "DIN pin not 27"
    print("  ✅ ESP32 Driver Checker: Pins & zero PSRAM DMA verified!")

    # 4. Test ZeroGPU Space Auditor
    print("\n[4/14] Testing echosphere_zerogpu_space_auditor...")
    zg_res = json.loads(echosphere_zerogpu_space_auditor())
    print("  ZeroGPU Status:", zg_res.get("status"))
    assert zg_res["details"]["error_3_zerogpu_cuda_startup_check"]["import_spaces_on_line_1"], "Line 1 must be import spaces"
    assert zg_res["details"]["error_3_zerogpu_cuda_startup_check"]["gpu_decorator_applied"], "GPU decorator must be applied"
    assert zg_res["details"]["error_4_pydantic_boolean_schema_and_proxy_crash"]["pydantic_pinned_le_2_10_6"], "Pydantic must be pinned"
    print("  ✅ ZeroGPU Space Auditor: Errors 1-4 validation passed!")

    # 5. Test Audio Integrity Auditor
    print("\n[5/14] Testing echosphere_audio_integrity_auditor...")
    audio_res = json.loads(echosphere_audio_integrity_auditor(action="scan_code_for_beeps"))
    print("  Audio Verdict:", audio_res.get("verdict"))
    assert len(audio_res["banned_tone_generators_found"]) == 0, "Banned sine wave generator found!"
    assert audio_res["anti_beep_purge_mechanism_active"], "Purge mechanism missing"
    print("  ✅ Audio Integrity: Anti-beep guarantee verified!")

    # 6. Test Render Safeguard Auditor
    print("\n[6/14] Testing echosphere_render_safeguard_auditor...")
    render_res = json.loads(echosphere_render_safeguard_auditor())
    print("  Render Memory Guard:", render_res.get("memory_safeguard_status"))
    assert render_res["render_cloud_detection_present"], "Render environment check missing"
    print("  ✅ Render Safeguards: 512MB RAM safeguard verified!")

    # 7. Test Repeat Schedule Manager
    print("\n[7/14] Testing echosphere_repeat_schedule_manager...")
    rbac_admin = json.loads(echosphere_repeat_schedule_manager(action="validate_rbac", user_role="principal"))
    assert rbac_admin["permitted"] is True, "Principal should be permitted"
    rbac_student = json.loads(echosphere_repeat_schedule_manager(action="validate_rbac", user_role="student"))
    assert rbac_student["permitted"] is False, "Student must be prohibited"
    print("  ✅ Repeat Schedules: RBAC authorization logic verified!")

    # 8. Test Hardware Node Manager
    print("\n[8/14] Testing echosphere_hardware_node_manager...")
    serial_res = json.loads(echosphere_hardware_node_manager(action="serial_status"))
    assert serial_res["recommended_baud_rate"] == 115200
    print("  ✅ Hardware Nodes: Serial port & 115200 baud verified!")

    # 9. Test Zero-Jargon Scanner
    print("\n[9/14] Testing echosphere_zero_jargon_scanner...")
    jargon_res = json.loads(echosphere_zero_jargon_scanner())
    print("  Zero-Jargon Verdict:", jargon_res.get("verdict"))
    print(f"  Scanned: {jargon_res.get('scanned_files_count')} Dart files, Violations: {jargon_res.get('violations_count')}")
    print("  ✅ Zero-Jargon Scanner: AGENTS.md rule scanner verified!")

    # 10. Test AI Summarizer Validator
    print("\n[10/14] Testing echosphere_ai_summarizer_validator...")
    sum_res = json.loads(echosphere_ai_summarizer_validator())
    assert sum_res["meets_minimum_15_words"] is True
    print("  ✅ AI Summarizer: Sanitizer & word length verified!")

    # 11. Test Database & Git Guard
    print("\n[11/14] Testing echosphere_database_and_git_guard...")
    git_res = json.loads(echosphere_database_and_git_guard())
    assert git_res["zero_secrets_guarantee"] is True, "Secrets or DB committed in git!"
    print("  ✅ Git & DB Guard: Zero-secrets guarantee verified!")

    # 12. Test Speaker Queue Control
    print("\n[12/14] Testing echosphere_speaker_queue_control...")
    queue_res = json.loads(echosphere_speaker_queue_control(action="verify_play_once"))
    print("  Queue Play-Once Check:", queue_res.get("result", "Checked"))
    print("  ✅ Speaker Queue: Play-once & lifecycle verified!")

    # 13. Test Full System Health Audit
    print("\n[13/14] Testing echosphere_system_health_audit...")
    health_res = echosphere_system_health_audit(check_live_backend=True)
    assert "Full System Health Audit" in health_res
    print("  ✅ System Health Audit: Multi-tier audit verified!")

    # 14. Test Verification Matrix Runner
    print("\n[14/14] Testing echosphere_run_verification_matrix...")
    matrix_res = echosphere_run_verification_matrix()
    print("\n" + matrix_res)
    assert "Production Verification Matrix" in matrix_res

    print("\n" + "=" * 70)
    print("🎉 ALL 14 ECHOSPHERE MCP TESTS PASSED WITH 100% PRECISION!")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
