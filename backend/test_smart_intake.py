import sys
import os
import base64

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["GEMINI_API_KEY"] = ""

from app.services.smart_intake_service import SmartIntakeService


def test_voice_dictation_lab_postponement():
    print("Testing Voice Dictation: Lab Postponement...")
    spoken_transcript = (
        "Hey everyone, this is regarding 3rd year CSE lab exam. "
        "Tomorrow's lab in Turing Lab at 2 PM is postponed to Friday at 2 PM due to the faculty meeting. "
        "Make sure to bring your hall tickets."
    )
    result = SmartIntakeService.voice_to_notice(
        audio_base64=None,
        raw_transcript=spoken_transcript,
    )

    print("Title:", result["title"])
    print("Category:", result["suggested_category"])
    print("Priority:", result["suggested_priority"])
    print("Audience:", result["suggested_audience"])
    print("Event:", result["extracted_event"])

    assert "Lab" in result["title"] or "Examination" in result["title"] or "Notice" in result["title"]
    assert result["suggested_category"] in ["Examination", "Academic"]
    assert result["suggested_priority"] in ["HIGH", "URGENT", "NORMAL"]
    assert "CSE" in result["suggested_audience"] or "3rd Year" in result["suggested_audience"]
    assert "Turing Lab" in result["content"] or "Turing Lab" in str(result.get("extracted_event"))
    assert result["transcription"] == spoken_transcript
    print("[PASS] test_voice_dictation_lab_postponement passed!")


def test_voice_dictation_emergency():
    print("\nTesting Voice Dictation: Emergency Evacuation Alert...")
    spoken_transcript = "Urgent emergency alert: Fire alarm triggered in Central Block. Evacuate immediately to ground."
    result = SmartIntakeService.voice_to_notice(
        raw_transcript=spoken_transcript,
    )

    print("Title:", result["title"])
    print("Category:", result["suggested_category"])
    print("Priority:", result["suggested_priority"])

    assert result["suggested_category"] == "Emergency"
    assert result["suggested_priority"] == "URGENT"
    print("[PASS] test_voice_dictation_emergency passed!")


def test_document_ocr_circular_structuring():
    print("\nTesting Document OCR Auto-Digitizer...")
    # Simulate a circular document with reference number and text
    simulated_doc_text = (
        "RV COLLEGE OF ENGINEERING\n"
        "OFFICIAL CIRCULAR\n"
        "Ref No: RVCE/EXAM/2026/088\n"
        "Date: 15 October 2026\n"
        "Subject: Mid-Semester Examination Timetable and Hall Allocations\n"
        "All 5th Semester AIML and CSE students must report to Room 302 at 09:30 AM.\n"
        "Fee payment deadline: October 20th."
    )
    doc_b64 = base64.b64encode(simulated_doc_text.encode('utf-8')).decode('ascii')

    result = SmartIntakeService.ocr_document_to_notice(
        file_base64=doc_b64,
        mime_type="application/pdf",
        filename="mid_sem_exam_timetable.pdf",
    )

    print("OCR Title:", result["title"])
    print("OCR Category:", result["suggested_category"])
    print("OCR Reference No:", result["reference_number"])
    print("OCR Content snippet:", result["content"][:100])

    assert "Timetable" in result["title"] or "Exam" in result["title"] or "Official Circular" in result["title"]
    assert result["suggested_category"] == "Examination"
    assert "Ref" in str(result["reference_number"]) or "CIR" in str(result["reference_number"])
    assert "official" in result["content"].lower() or "circular" in result["content"].lower()
    print("[PASS] test_document_ocr_circular_structuring passed!")


if __name__ == "__main__":
    test_voice_dictation_lab_postponement()
    test_voice_dictation_emergency()
    test_document_ocr_circular_structuring()
    print("\n[SUCCESS] All Smart Intake Service backend tests passed successfully!")
    os._exit(0)
