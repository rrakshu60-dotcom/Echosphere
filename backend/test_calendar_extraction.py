import sys
import os
import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import AIService

def test_calendar_extraction():
    print("=== Testing EchoSphere Calendar Event Extraction ===")

    # Test Case 1: Deadline with fee and room
    notice_1 = {
        "title": "Exam Form Submission Deadline",
        "description": "All eligible students must submit their examination forms by Oct 24th, 5 PM to Room 302 along with a Rs. 500 fee."
    }
    res_1 = AIService.extract_calendar_event(notice_1["title"], notice_1["description"])
    assert res_1.get("has_event") is True, f"Expected event, got: {res_1}"
    assert "2026-10-24" in res_1.get("start_time", "") or "10-24" in res_1.get("start_time", ""), f"Wrong date: {res_1}"
    assert "302" in res_1.get("location", "").lower(), f"Wrong location: {res_1}"
    print("[PASS] Test Case 1: Deadline with fee and room")

    # Test Case 2: College Event with morning time and venue
    notice_2 = {
        "title": "Annual Sports Day 2026",
        "description": "Annual Sports Day will be held on 15th November 2026 at 9:30 AM in College Football Ground."
    }
    res_2 = AIService.extract_calendar_event(notice_2["title"], notice_2["description"])
    assert res_2.get("has_event") is True, f"Expected event, got: {res_2}"
    assert "2026-11-15" in res_2.get("start_time", ""), f"Wrong date: {res_2}"
    assert "football ground" in res_2.get("location", "").lower(), f"Wrong location: {res_2}"
    print("[PASS] Test Case 2: Event with morning time and venue")

    # Test Case 3: Campus Placement Drive
    notice_3 = {
        "title": "Campus Placement Drive",
        "description": "T&P Cell announces placement drive on Nov 14, 2026 at 10:00 AM in the Central Auditorium."
    }
    res_3 = AIService.extract_calendar_event(notice_3["title"], notice_3["description"])
    assert res_3.get("has_event") is True, f"Expected event, got: {res_3}"
    assert "auditorium" in res_3.get("location", "").lower(), f"Wrong location: {res_3}"
    print("[PASS] Test Case 3: Placement drive in auditorium")

    # Test Case 4: Notice with NO dates or deadlines
    notice_4 = {
        "title": "General Library Hygiene Policy",
        "description": "Please maintain silence and keep your mobile phones on silent mode while in the central reading hall."
    }
    res_4 = AIService.extract_calendar_event(notice_4["title"], notice_4["description"])
    assert res_4.get("has_event") is False, f"Expected no event, got: {res_4}"
    print("[PASS] Test Case 4: Notice with no dates returns has_event=False")

    print("\nAll calendar extraction tests passed successfully!")

if __name__ == "__main__":
    test_calendar_extraction()
