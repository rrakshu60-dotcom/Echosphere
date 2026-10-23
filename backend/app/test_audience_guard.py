"""Audience check: student notices addressed to Faculty Members are flagged too (only the reverse was checked)."""
from app.services.audience_guard_service import AudienceGuardService as Guard


def check(title, content, audience):
    return Guard.analyze_target_audience(title=title, content=content, selected_audience=audience)


def test_a_final_year_notice_sent_to_faculty_is_flagged():
    r = check("Final year project submission", "All final year students must submit their project reports by Friday.", "Faculty Members")
    assert r["has_mismatch"] and r["suggested_audiences"][0] == "4th Year Students", r


def test_a_hostel_notice_sent_to_faculty_is_flagged():
    r = check("Hostel water supply", "Hostel residents: there will be no water supply from 6 PM to 8 PM today.", "Faculty Members")
    assert r["has_mismatch"], r


def test_a_faculty_notice_sent_to_faculty_is_fine():
    r = check("Faculty meeting", "All faculty members must attend the staff meeting at 3 PM in the staff room.", "Faculty Members")
    assert not r["has_mismatch"], r


def test_existing_checks_still_work():
    assert check("CSE lab change", "CSE department students: the DBMS lab moves to Lab 4 from Monday.", "ECE Department")["has_mismatch"]
    assert check("Faculty meeting", "All faculty members must attend the staff meeting at 3 PM.", "1st Year Students")["has_mismatch"]
