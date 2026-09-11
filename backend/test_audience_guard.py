import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app.services.audience_guard_service import AudienceGuardService


def test_audience_guard():
    print("=== Testing EchoSphere AI Audience Pre-Flight Check (Anti-Spam Guard) ===")

    # Test 1: Department & Year specific notice addressed to Entire College (Spam warning)
    print("\n--- Test 1: Department-Specific Notice with Entire College ---")
    res_1 = AudienceGuardService.analyze_target_audience(
        title="Operating Systems Lab Internal Assessment",
        content="All 3rd Year CSE students must report to CS Lab 1 for the OS practical exam this Friday.",
        selected_audience="Entire College",
    )
    assert res_1["has_mismatch"] is True, f"Expected audience mismatch, got: {res_1}"
    assert "CSE Department" in res_1["suggested_audiences"] or "3rd Year Students" in res_1["suggested_audiences"]
    assert res_1["warning_message"] is not None
    print(f"[PASS] Detected overly broad audience: {res_1['warning_message']}")
    print(f"       Suggested narrowing chips: {res_1['suggested_audiences']}")

    # Test 2: Year-specific notice addressed to Entire College
    print("\n--- Test 2: Batch-Specific Notice with Entire College ---")
    res_2 = AudienceGuardService.analyze_target_audience(
        title="1st Year Induction Program & Physics Cycle Orientation",
        content="Orientation session for all incoming first year freshers in Central Auditorium on Monday 9 AM.",
        selected_audience="Entire College",
    )
    assert res_2["has_mismatch"] is True, f"Expected mismatch for freshers notice, got: {res_2}"
    assert "1st Year Students" in res_2["suggested_audiences"]
    print(f"[PASS] Detected batch mismatch: {res_2['warning_message']}")

    # Test 3: Faculty-only meeting addressed to Entire College
    print("\n--- Test 3: Faculty Meeting with Entire College ---")
    res_3 = AudienceGuardService.analyze_target_audience(
        title="Urgent Faculty & Staff Meeting with Principal",
        content="All faculty members, professors, and teaching staff must attend mandatory meeting on syllabus completion in Room 101.",
        selected_audience="Entire College",
    )
    assert res_3["has_mismatch"] is True, f"Expected mismatch for faculty notice, got: {res_3}"
    assert "Faculty Members" in res_3["suggested_audiences"]
    print(f"[PASS] Prevented spamming students with faculty meeting notice: {res_3['suggested_audiences']}")

    # Test 4: Genuine College-Wide Notice (Holiday / Fest / Bus Transport)
    print("\n--- Test 4: Legitimate College-Wide Notice ---")
    res_4 = AudienceGuardService.analyze_target_audience(
        title="Institutional Holiday Announcement: Kannada Rajyotsava",
        content="The college campus will remain closed on Friday in observance of Kannada Rajyotsava. All classes and offices suspended.",
        selected_audience="Entire College",
    )
    assert res_4["has_mismatch"] is False, f"Expected no mismatch for college-wide holiday, got: {res_4}"
    print("[PASS] Whitelisted college-wide holiday passed cleanly without false warnings.")

    # Test 5: Notice matching selected audience exactly
    print("\n--- Test 5: Matching Department Audience ---")
    res_5 = AudienceGuardService.analyze_target_audience(
        title="Thermodynamics & Fluid Mechanics Lab Schedule",
        content="Mechanical Department laboratory schedule for internal assessment in Lathe Lab.",
        selected_audience="Mechanical Department",
    )
    assert res_5["has_mismatch"] is False, f"Expected no mismatch when audience matches department, got: {res_5}"
    print("[PASS] Department notice matching selected audience passed cleanly.")

    # Test 6: Cross-Department Mismatch (Civil notice sent to CSE Department)
    print("\n--- Test 6: Cross-Department Mismatch ---")
    res_6 = AudienceGuardService.analyze_target_audience(
        title="Concrete Technology & Surveying Lab",
        content="Civil Department students must assemble at the surveying grounds on Wednesday morning.",
        selected_audience="CSE Department",
    )
    assert res_6["has_mismatch"] is True, f"Expected cross-department mismatch, got: {res_6}"
    assert "Civil Department" in res_6["suggested_audiences"]
    assert res_6["mismatch_type"] == "wrong_department"
    print(f"[PASS] Detected cross-department mismatch: {res_6['warning_message']}")

    print("\nAll 6 audience guard engine tests passed successfully!")


if __name__ == "__main__":
    test_audience_guard()
