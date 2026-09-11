import sys
import os

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.relevance_scoring_service import RelevanceScoringService


def test_student_direct_match_high_relevance():
    user = {
        "role": "Student",
        "department": "AIML",
        "semester": 5,
        "usn": "1DB23CI079",
    }
    notice = {
        "id": 101,
        "title": "5th Sem AIML Internal Assessment Examination Schedule",
        "description": "IA-1 for 5th semester AIML students will commence next Monday in Lab 4.",
        "department": "AIML",
        "target_audience": "3rd Year Students",
        "category": "Examination",
        "priority": "HIGH",
    }
    result = RelevanceScoringService.calculate_score(user, notice)
    print(f"Test 1 - Direct Match Score: {result['score']}, Highly Relevant: {result['is_highly_relevant']}, Reasons: {result['reasons']}")
    assert result["score"] >= 0.70, f"Expected score >= 0.70, got {result['score']}"
    assert result["is_highly_relevant"] is True
    assert any("AIML" in r for r in result["reasons"])
    assert any("5" in r or "Semester" in r for r in result["reasons"])


def test_different_department_and_semester_low_relevance():
    user = {
        "role": "Student",
        "department": "AIML",
        "semester": 5,
        "usn": "1DB23CI079",
    }
    notice = {
        "id": 102,
        "title": "Civil Engineering Survey Camp for 1st Year Students",
        "description": "All 1st sem Civil engineering students must report with drafting tools.",
        "department": "CIVIL",
        "target_audience": "1st Year Students",
        "category": "Workshop",
        "priority": "NORMAL",
    }
    result = RelevanceScoringService.calculate_score(user, notice)
    print(f"Test 2 - Civil 1st Sem Notice Score: {result['score']}, Highly Relevant: {result['is_highly_relevant']}")
    assert result["score"] <= 0.40, f"Expected score <= 0.40, got {result['score']}"
    assert result["is_highly_relevant"] is False


def test_emergency_notice_universal_boost():
    user = {
        "role": "Student",
        "department": "ECE",
        "semester": 3,
    }
    emergency_notice = {
        "id": 103,
        "title": "Severe Weather Warning: Campus Closure Today",
        "description": "Due to heavy rains, all classes and labs are suspended immediately.",
        "department": "General",
        "target_audience": "Entire College",
        "category": "Emergency",
        "priority": "EMERGENCY",
        "emergency_level": "CRITICAL",
    }
    result = RelevanceScoringService.calculate_score(user, emergency_notice)
    print(f"Test 3 - Emergency Score: {result['score']}, Highly Relevant: {result['is_highly_relevant']}")
    assert result["score"] >= 0.50
    assert any("Emergency" in r for r in result["reasons"])


def test_placement_drive_senior_vs_junior():
    placement_notice = {
        "id": 104,
        "title": "Google Campus Placement Drive & Coding Assessment",
        "description": "Pre-placement talk and online test for graduating engineering students.",
        "department": "Placement",
        "target_audience": "4th Year Students",
        "category": "Placement",
        "priority": "HIGH",
    }

    senior_student = {"role": "Student", "department": "CSE", "semester": 7}
    junior_student = {"role": "Student", "department": "CSE", "semester": 1}

    senior_res = RelevanceScoringService.calculate_score(senior_student, placement_notice)
    junior_res = RelevanceScoringService.calculate_score(junior_student, placement_notice)

    print(f"Test 4 - Senior Placement Score: {senior_res['score']}, Junior Score: {junior_res['score']}")
    assert senior_res["score"] > junior_res["score"], "Senior score should exceed junior score for placements"
    assert any("Placement" in r for r in senior_res["reasons"])


def test_batch_relevance_calculation():
    user = {
        "role": "Student",
        "department": "AIML",
        "semester": 5,
    }
    notices = [
        {
            "id": 201,
            "title": "AIML 5th Sem Lab Exam",
            "description": "Lab test for AIML Sem 5",
            "department": "AIML",
            "category": "Examination",
            "priority": "HIGH",
        },
        {
            "id": 202,
            "title": "Hostel Mess Fee Payment Reminder",
            "description": "Hostel fee due date is Oct 31st for all resident students.",
            "department": "General",
            "category": "Fee Payment",
            "priority": "NORMAL",
        },
        {
            "id": 203,
            "title": "Mechanical Workshop for Sem 2",
            "description": "Lathe workshop for mechanical freshers.",
            "department": "ME",
            "target_audience": "1st Year Students",
            "category": "Workshop",
            "priority": "LOW",
        }
    ]

    results = RelevanceScoringService.calculate_batch(user, notices)
    assert len(results) == 3
    assert results[0]["score"] > results[2]["score"]
    assert results[0]["is_highly_relevant"] is True
    print("Test 5 - Batch scoring passed with 3 items.")


if __name__ == "__main__":
    test_student_direct_match_high_relevance()
    test_different_department_and_semester_low_relevance()
    test_emergency_notice_universal_boost()
    test_placement_drive_senior_vs_junior()
    test_batch_relevance_calculation()
    print("\n[SUCCESS] All 5 Backend Relevance Scoring tests passed successfully!")
