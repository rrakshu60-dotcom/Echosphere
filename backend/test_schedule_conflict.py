import datetime
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.services.conflict_service import ConflictService


def test_schedule_conflict_detector():
    print("=== Testing EchoSphere AI Schedule Conflict & Overlap Detector ===")

    # Mock candidate active circulars
    active_circulars = [
        {
            "id": 214,
            "title": "Robotics & Automation Workshop",
            "description": "Mechanical Department is organizing a hands-on workshop in Seminar Hall B on Oct 25, 2:00 PM.",
            "department": "Mechanical Dept",
            "scheduled_at": None,
        },
        {
            "id": 215,
            "title": "Campus Placement Drive: Infosys",
            "description": "Final year recruitment drive in Placement Cell on Oct 28, 9:30 AM.",
            "department": "Placement Cell",
            "scheduled_at": None,
        },
        {
            "id": 216,
            "title": "End-Semester Theory Examination",
            "description": "Mandatory semester exam for 3rd year students in Central Auditorium on Nov 12, 2:00 PM.",
            "department": "Examination Cell",
            "scheduled_at": None,
        },
    ]

    # Test 1: Direct Venue Collision in Seminar Hall B
    print("\n--- Test 1: Direct Venue Collision ---")
    draft_1 = {
        "title": "Civil Engineering Symposium 2026",
        "content": "Join us for the annual symposium in Seminar Hall B on Oct 25, 2:30 PM.",
    }
    res_1 = ConflictService.detect_schedule_conflicts(
        db=None,
        title=draft_1["title"],
        content=draft_1["content"],
        active_notices_override=active_circulars,
    )
    assert res_1["has_conflict"] is True, "Expected conflict for Seminar Hall B double booking"
    assert len(res_1["conflicts"]) == 1
    c1 = res_1["conflicts"][0]
    assert c1["conflict_type"] == "venue_collision"
    assert c1["conflicting_notice_id"] == 214
    assert "Mechanical Dept" in c1["conflicting_department"]
    assert "Seminar Hall B" in c1["conflicting_venue"]
    assert len(res_1["suggested_alternatives"]) > 0, "Expected suggested alternative time slots"
    print(f"[PASS] Detected venue collision: {c1['conflict_message']}")
    print(f"       Suggested alternative: {res_1['suggested_alternatives'][0]['label']}")

    # Test 2: Same venue, different non-overlapping time
    print("\n--- Test 2: Same Venue, Non-Overlapping Time ---")
    draft_2 = {
        "title": "Morning Guest Lecture on AI",
        "content": "Guest lecture in Seminar Hall B on Oct 25, 9:00 AM.",
    }
    res_2 = ConflictService.detect_schedule_conflicts(
        db=None,
        title=draft_2["title"],
        content=draft_2["content"],
        active_notices_override=active_circulars,
    )
    assert res_2["has_conflict"] is False, f"Expected no conflict for morning session, got {res_2}"
    print("[PASS] No collision detected for morning slot in Seminar Hall B.")

    # Test 3: Different venue at the same time
    print("\n--- Test 3: Different Venue at Same Time ---")
    draft_3 = {
        "title": "Coding Competition Prelims",
        "content": "Hackathon prelims in CS Lab 1 on Oct 25, 2:00 PM.",
    }
    res_3 = ConflictService.detect_schedule_conflicts(
        db=None,
        title=draft_3["title"],
        content=draft_3["content"],
        active_notices_override=active_circulars,
    )
    assert res_3["has_conflict"] is False, "Expected no conflict for different venue (CS Lab 1 vs Seminar Hall B)"
    print("[PASS] No collision detected when different venue is used at same time.")

    # Test 4: Critical Academic Event Clash (Exam vs Sports Fest)
    print("\n--- Test 4: Critical Academic Event Clash ---")
    draft_4 = {
        "title": "Inter-Department Cricket Fest & Tournament",
        "content": "All students must attend annual sports meet and tournament on Nov 12, 2:00 PM.",
    }
    res_4 = ConflictService.detect_schedule_conflicts(
        db=None,
        title=draft_4["title"],
        content=draft_4["content"],
        active_notices_override=active_circulars,
    )
    assert res_4["has_conflict"] is True, "Expected critical academic clash between exam and sports fest"
    c4 = res_4["conflicts"][0]
    assert c4["conflict_type"] == "academic_clash"
    assert c4["conflicting_notice_id"] == 216
    print(f"[PASS] Detected academic clash: {c4['conflict_message']}")

    # Test 5: Exclude notice ID when author edits their own existing notice
    print("\n--- Test 5: Exclude Notice ID (Editing Self) ---")
    res_5 = ConflictService.detect_schedule_conflicts(
        db=None,
        title="Robotics & Automation Workshop (Updated)",
        content="Mechanical Department is organizing a hands-on workshop in Seminar Hall B on Oct 25, 2:00 PM.",
        exclude_notice_id=214,
        active_notices_override=active_circulars,
    )
    assert res_5["has_conflict"] is False, "Expected self-notice to be excluded from collision check"
    print("[PASS] Self-notice properly excluded when updating circular.")

    print("\nAll 5 schedule conflict engine tests passed successfully!")


if __name__ == "__main__":
    test_schedule_conflict_detector()
