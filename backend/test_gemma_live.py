"""
EchoSphere Live Gemma Model & Formatting Verification Script
Validates:
1. Exact user query: 'hello who are you'
2. Real-time GPU inference through Gemma 2
3. Absence of asterisks, dividers (----), slashes (///), and profile regurgitation
4. Student RBAC courtesy refusal vs DevAdmin hardware navigation
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import AIService

def run_tests():
    print("=" * 65)
    print("ECHOSPHERE LIVE GEMMA & FORMATTING VERIFICATION")
    print("=" * 65)

    # Test 1: User's reported query
    print("\n[TEST 1] User query: 'hello who are you'")
    res1 = AIService.process_chat(
        prompt="hello who are you",
        user_role="DEVADMIN",
        department="General",
        full_name="Dev Admin",
        usn_or_emp_id="ESDev01"
    )
    reply1 = res1.get("response", "")
    model1 = res1.get("model_used", "")
    badge1 = res1.get("category_badge", "")

    print(f"Model Used:     {model1}")
    print(f"Category Badge: {badge1}")
    print(f"Response:\n{reply1}\n")

    # Assertions for Test 1
    assert "Fine-Tuned Gemma 2" in model1, f"Expected Gemma 2, got: {model1}"
    assert "EchoSphere Campus AI Assistant" in reply1, "Assistant identity missing"
    assert "ESDev01" not in reply1, "FATAL: User ID leaked into response!"
    assert "Given your profile" not in reply1, "FATAL: Robotic profile regurgitation!"
    assert "**EchoSphere" not in reply1, "Synthetic bold asterisks found in bot greeting!"
    assert "----" not in reply1, "Divider lines '----' found!"
    assert "///" not in reply1, "Slash tokens '///' found!"
    assert "****" not in reply1, "Asterisk clutter '****' found!"
    print("  -> PASSED: Query answered by Gemma 2 cleanly without artifacts or profile regurgitation!")

    # Test 2: Student RBAC inquiry for speaker queue
    print("\n[TEST 2] Student query: 'Can I view the smart speaker queue?'")
    res2 = AIService.process_chat(
        prompt="Can I view the smart speaker queue?",
        user_role="STUDENT",
        department="CSE",
        full_name="Alex Student",
        usn_or_emp_id="1DB21CS011"
    )
    reply2 = res2.get("response", "")
    badge2 = res2.get("category_badge", "")
    action2 = res2.get("copilot_action")

    print(f"Category Badge: {badge2}")
    print(f"Response:\n{reply2}\n")
    print(f"Copilot Action: {action2}")

    assert "I don't have the authority" in reply2, "Expected polite refusal"
    assert "student and not allowed" not in reply2.lower(), "Offensive phrasing detected!"
    assert action2 is None, "Student must not receive navigation action to hardware!"
    print("  -> PASSED: Student politely restricted without offensive language or hardware access!")

    # Test 3: Dev Admin speaker queue inquiry
    print("\n[TEST 3] Dev Admin query: 'Take me to the smart speaker queue'")
    res3 = AIService.process_chat(
        prompt="Take me to the smart speaker queue",
        user_role="DEVADMIN",
        department="General",
        full_name="Dev Admin",
        usn_or_emp_id="ESDev01"
    )
    action3 = res3.get("copilot_action")
    print(f"Copilot Action: {action3}")
    assert action3 is not None and action3.get("action") == "navigate", "Dev Admin navigation action missing!"
    assert action3["parameters"]["screen"] == "speaker_queue", "Incorrect screen target"
    print("  -> PASSED: Dev Admin navigation action dispatched cleanly!")

    print("\n" + "=" * 65)
    print("ALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
