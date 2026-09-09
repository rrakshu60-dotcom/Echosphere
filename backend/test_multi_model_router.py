"""
Test Suite for EchoSphere Next-Gen AI System:
- Multi-Model Router & Congestion Balancer
- Gemma Action Engine
- CopilotKit Agent Runtime
- AI Markdown Sanitizer (zero ***, ##$, ---, **** clutter)
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_text_sanitizer import sanitize_ai_markdown
from app.services.model_router import ModelRouter, GemmaActionEngine
from app.services.copilot_runtime import CopilotRuntime


def test_markdown_sanitization():
    print("\n--- 1. Testing AI Text & Markdown Sanitizer ---")

    # Case A: Dollar-prefixed headings
    raw_heading = "##$Academics\nImportant circular."
    clean_h = sanitize_ai_markdown(raw_heading)
    assert "## Academics" in clean_h, f"Expected '## Academics', got: {clean_h}"
    print("  -> Passed: Fixed dollar-prefixed header '##$Academics'")

    # Case B: Literal dividers and asterisk clutter
    raw_dividers = "Notice Details\n---\n***\n****Official Circular****\n___"
    clean_d = sanitize_ai_markdown(raw_dividers)
    assert "---" not in clean_d
    assert "***" not in clean_d
    assert "**Official Circular**" in clean_d
    print("  -> Passed: Removed raw dividers '---', '***' and normalized '****' to bold")

    # Case C: CommonMark bullet list spacing and spaces between bold markers
    raw_bullets = "Guidelines:\n- **Item 1:** First requirement\n- **Item 2:** Second requirement"
    clean_b = sanitize_ai_markdown(raw_bullets)
    assert "Guidelines:\n\n- **Item 1:** First requirement" in clean_b
    assert "- **Item 1:** First requirement" in clean_b
    print("  -> Passed: Ensured CommonMark compliant list spacing and word separation")

    # Case D: Space after bold colon
    raw_colon = "- **Mandatory Attendance:**A minimum of **75% attendance**"
    clean_c = sanitize_ai_markdown(raw_colon)
    assert "**Mandatory Attendance:** A minimum" in clean_c
    print("  -> Passed: Ensured space after bold colon")


def test_gemma_action_engine():
    print("\n--- 2. Testing Gemma Action Engine ---")

    # Test Speaker Queue navigation (Teacher - Allowed)
    res_teacher = GemmaActionEngine.match_action("Take me to speaker queue", "Teacher", "CSE")
    assert res_teacher is not None
    assert res_teacher["navigation_target"] == "nav:hardware:speakers"
    print("  -> Passed: Teacher query routed to 'nav:hardware:speakers'")

    # Test Speaker Queue navigation (Student - Restricted)
    res_student = GemmaActionEngine.match_action("Take me to speaker queue", "Student", "CSE")
    assert res_student is not None
    assert res_student["action"] == "access_denied"
    assert "don't have the authority" in res_student["response"]
    print("  -> Passed: Student restricted from speaker hardware navigation")

    # Test Theme toggle
    res_theme = GemmaActionEngine.match_action("Switch to dark mode", "Student", "AIML")
    assert res_theme is not None
    assert res_theme["navigation_target"] == "action:theme:dark"
    print("  -> Passed: Theme query mapped to 'action:theme:dark'")

    # Test Notice Filter
    res_filter = GemmaActionEngine.match_action("Show me exam timetable", "Student", "CSE")
    assert res_filter is not None
    assert res_filter["navigation_target"] == "nav:notices:filter:Examinations"
    print("  -> Passed: Exam query mapped to 'nav:notices:filter:Examinations'")


def test_copilot_runtime():
    print("\n--- 3. Testing CopilotKit Agent Runtime ---")

    req = {
        "message": "Filter all placement circulars",
        "app_state": {"active_route": "/home", "current_filter": "All"},
        "user_role": "STUDENT",
        "department": "CSE",
        "full_name": "Test Student"
    }

    res = CopilotRuntime.process_copilot_request(
        message=req["message"],
        app_state=req["app_state"],
        user_role=req["user_role"],
        department=req["department"],
        full_name=req["full_name"]
    )

    assert "response" in res
    assert res.get("copilot_action") is not None or res.get("navigation_target") is not None
    print(f"  -> Passed: CopilotRuntime generated response with action: {res.get('copilot_action') or res.get('navigation_target')}")


def test_router_status_and_health():
    print("\n--- 4. Testing Multi-Model Router Health & Metrics ---")

    router = ModelRouter.get_instance()
    status = router.get_router_status()
    assert "active_providers" in status
    assert "gemma_action_engine" in status["active_providers"]
    assert "campus_ml_fallback" in status["active_providers"]
    print(f"  -> Passed: Router status report operational: {list(status['active_providers'].keys())}")


if __name__ == "__main__":
    print("============================================================")
    print("RUNNING MULTI-MODEL ROUTER, COPILOT & SANITIZER TEST SUITE")
    print("============================================================")
    test_markdown_sanitization()
    test_gemma_action_engine()
    test_copilot_runtime()
    test_router_status_and_health()
    print("============================================================")
    print("ALL NEXT-GEN AI & SANITIZER TESTS PASSED (100%)!")
    print("============================================================")
