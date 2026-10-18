"""
EchoSphere Test Suite: Feature 4.3 - AI Copilot In-App Execution Depth
Tests offline deterministic action parsing, parameter extraction,
strict RBAC role verification, and the FastAPI Copilot endpoint.
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.services.copilot_runtime import CopilotRuntime, ECHOSPHERE_COPILOT_ACTIONS
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_copilot_action_schema_depth():
    print("Test 1: Verifying Copilot Action Schemas in CopilotRuntime...")
    action_names = [a.name for a in ECHOSPHERE_COPILOT_ACTIONS]
    required_actions = [
        "navigate",
        "create_announcement_draft",
        "toggle_theme",
        "control_speaker_queue",
        "set_speaker_volume",
        "approve_notice",
        "reject_notice",
        "delete_notice",
        "filter_notices"
    ]
    for req in required_actions:
        assert req in action_names, f"Action '{req}' missing from ECHOSPHERE_COPILOT_ACTIONS"
    print(f"  [PASS] All {len(required_actions)} actions present in official CopilotKit schema.")


def test_speaker_volume_execution():
    print("Test 2: Verifying 'set_speaker_volume' intent extraction and clamping...")
    
    # 2a: Set auditorium volume to 80%
    res = CopilotRuntime.process_copilot_request(
        message="Set Auditorium volume to 80%",
        app_state={},
        user_role="ADMIN"
    )
    assert res.get("copilot_action") is not None, "copilot_action should not be None"
    assert res["copilot_action"]["action"] == "set_speaker_volume"
    assert res["copilot_action"]["parameters"]["node_id"] == "Auditorium"
    assert res["copilot_action"]["parameters"]["volume"] == 80
    print("  [PASS] Successfully parsed 'Set Auditorium volume to 80%'")

    # 2b: Clamp over 100%
    res_clamp = CopilotRuntime.process_copilot_request(
        message="Set volume to 125%",
        app_state={},
        user_role="FACULTY"
    )
    assert res_clamp["copilot_action"]["action"] == "set_speaker_volume"
    assert res_clamp["copilot_action"]["parameters"]["volume"] == 100
    print("  [PASS] Successfully clamped volume > 100% to 100%")

    # 2c: Mute speaker node
    res_mute = CopilotRuntime.process_copilot_request(
        message="Mute corridor speaker",
        app_state={},
        user_role="ADMIN"
    )
    assert res_mute["copilot_action"]["action"] == "set_speaker_volume"
    assert res_mute["copilot_action"]["parameters"]["volume"] == 0
    assert "Corridor" in res_mute["copilot_action"]["parameters"]["node_id"]
    print("  [PASS] Successfully parsed mute command to volume 0%")


def test_notice_moderation_execution():
    print("Test 3: Verifying Notice Moderation (Approve, Reject, Delete)...")

    # 3a: Approve notice
    res_approve = CopilotRuntime.process_copilot_request(
        message="Approve notice #42",
        app_state={},
        user_role="COLLEGE ADMIN"
    )
    assert res_approve["copilot_action"]["action"] == "approve_notice"
    assert res_approve["copilot_action"]["parameters"]["announcement_id"] == 42
    print("  [PASS] Successfully parsed 'Approve notice #42'")

    # 3b: Reject notice with reason
    res_reject = CopilotRuntime.process_copilot_request(
        message="Reject notice #15: Incomplete venue information",
        app_state={},
        user_role="FACULTY"
    )
    assert res_reject["copilot_action"]["action"] == "reject_notice"
    assert res_reject["copilot_action"]["parameters"]["announcement_id"] == 15
    assert "Incomplete venue information" in res_reject["copilot_action"]["parameters"]["remarks"]
    print("  [PASS] Successfully parsed 'Reject notice #15' with remarks")

    # 3c: Delete notice
    res_delete = CopilotRuntime.process_copilot_request(
        message="Delete announcement #8",
        app_state={},
        user_role="ADMIN"
    )
    assert res_delete["copilot_action"]["action"] == "delete_notice"
    assert res_delete["copilot_action"]["parameters"]["announcement_id"] == 8
    print("  [PASS] Successfully parsed 'Delete announcement #8'")


def test_filter_notices_execution():
    print("Test 4: Verifying 'filter_notices' intent extraction...")
    res_filter = CopilotRuntime.process_copilot_request(
        message="Filter exam notices",
        app_state={},
        user_role="STUDENT"
    )
    assert res_filter["copilot_action"]["action"] == "filter_notices"
    assert res_filter["copilot_action"]["parameters"]["category"] == "Examinations"
    print("  [PASS] Successfully parsed 'Filter exam notices' for student")


def test_strict_student_rbac_guardrails():
    print("Test 5: Verifying Strict Student RBAC Guardrails...")

    # Student trying to set speaker volume
    res_vol = CopilotRuntime.process_copilot_request(
        message="Set Auditorium volume to 80%",
        app_state={},
        user_role="STUDENT"
    )
    assert res_vol.get("copilot_action") is None, "Student must NOT be given speaker volume action"
    assert "Access Restricted" in res_vol.get("category_badge", "")
    assert "cannot execute administrative operations" in res_vol["response"]
    print("  [PASS] Student blocked from adjusting speaker volume")

    # Student trying to approve a notice
    res_app = CopilotRuntime.process_copilot_request(
        message="Approve notice #12",
        app_state={},
        user_role="STUDENT"
    )
    assert res_app.get("copilot_action") is None, "Student must NOT be given approve action"
    assert "Access Restricted" in res_app.get("category_badge", "")
    print("  [PASS] Student blocked from approving notice")

    # Student trying to delete a notice
    res_del = CopilotRuntime.process_copilot_request(
        message="Delete notice #8",
        app_state={},
        user_role="STUDENT"
    )
    assert res_del.get("copilot_action") is None, "Student must NOT be given delete action"
    assert "Access Restricted" in res_del.get("category_badge", "")
    print("  [PASS] Student blocked from deleting notice")


def test_fastapi_copilot_chat_endpoint():
    print("Test 6: Verifying FastAPI /api/v1/ai/copilot/chat Endpoint...")
    
    # 6a: Volume adjust by Admin
    payload = {
        "message": "Set Library volume to 65%",
        "app_state": {"current_screen": "speaker_queue"},
        "user_role": "ADMIN",
        "department": "CSE",
        "full_name": "Dr. Campus Admin"
    }
    response = client.post("/api/v1/ai/copilot/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["copilot_action"] is not None
    assert data["copilot_action"]["action"] == "set_speaker_volume"
    assert data["copilot_action"]["parameters"]["volume"] == 65
    print("  [PASS] API endpoint returned valid set_speaker_volume action")

    # 6b: RBAC via API
    student_payload = {
        "message": "Approve notice #99",
        "app_state": {},
        "user_role": "STUDENT"
    }
    s_response = client.post("/api/v1/ai/copilot/chat", json=student_payload)
    assert s_response.status_code == 200
    s_data = s_response.json()
    assert s_data["copilot_action"] is None
    assert "Access Restricted" in s_data["category_badge"]
    print("  [PASS] API endpoint enforced student RBAC restriction")


if __name__ == "__main__":
    print("\n==================================================")
    print("Running EchoSphere Feature 4.3 Test Suite")
    print("==================================================\n")
    test_copilot_action_schema_depth()
    test_speaker_volume_execution()
    test_notice_moderation_execution()
    test_filter_notices_execution()
    test_strict_student_rbac_guardrails()
    test_fastapi_copilot_chat_endpoint()
    print("\n==================================================")
    print("ALL 6/6 COPILOT DEPTH TESTS PASSED PERFECTLY!")
    print("==================================================\n")
