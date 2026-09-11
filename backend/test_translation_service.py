import sys
import os
import re

# Ensure backend root is in sys.path and disable live network LLM calls for deterministic fast tests
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["GEMINI_API_KEY"] = ""

from app.services.translation_service import TranslationService


def test_kannada_translation():
    text = "Important Notice: Examination schedule and fee payment deadline for 5th Sem AIML students in Room 302."
    result = TranslationService.translate_announcement(
        title="Examination Schedule Notice",
        content=text,
        summary="IA-1 exams begin next week.",
        target_language="kn"
    )
    safe_title = result['translated_title'].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"Kannada Title: {safe_title}")
    assert result["target_language"] == "kn"
    assert result["language_name"] == "Kannada"
    # Check for Kannada Unicode script range (\u0C80-\u0CFF)
    assert bool(re.search(r'[\u0C80-\u0CFF]', result['translated_content'])), "Expected Kannada script"
    # Check course code / entity preservation
    assert any(k in result['translated_content'] for k in ["AIML", "5th Sem", "5", "302", "Room"])


def test_hindi_translation():
    text = "Notice: All students must attend the technical workshop on machine learning in the Auditorium."
    result = TranslationService.translate_announcement(
        title="Technical Workshop",
        content=text,
        summary="Workshop on ML in Auditorium.",
        target_language="hi"
    )
    safe_title = result['translated_title'].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"Hindi Title: {safe_title}")
    assert result["target_language"] == "hi"
    assert result["language_name"] == "Hindi"
    # Check for Devanagari Unicode script range (\u0900-\u097F)
    assert bool(re.search(r'[\u0900-\u097F]', result['translated_content'])), "Expected Devanagari script"


def test_telugu_translation():
    text = "Holiday circular: College campus will be closed tomorrow. Classes suspended."
    result = TranslationService.translate_announcement(
        title="College Holiday Notice",
        content=text,
        summary="College closed tomorrow.",
        target_language="te"
    )
    safe_title = result['translated_title'].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"Telugu Title: {safe_title}")
    assert result["target_language"] == "te"
    assert result["language_name"] == "Telugu"
    # Check for Telugu Unicode script range (\u0C00-\u0C7F)
    assert bool(re.search(r'[\u0C00-\u0C7F]', result['translated_content'])), "Expected Telugu script"


def test_tamil_translation():
    text = "Campus placement drive: Google placement interview in Placement Cell with fee Rs. 500."
    result = TranslationService.translate_announcement(
        title="Placement Drive Notice",
        content=text,
        summary="Placement interviews in Placement Cell.",
        target_language="ta"
    )
    safe_title = result['translated_title'].encode('ascii', 'backslashreplace').decode('ascii')
    print(f"Tamil Title: {safe_title}")
    assert result["target_language"] == "ta"
    assert result["language_name"] == "Tamil"
    # Check for Tamil Unicode script range (\u0B80-\u0BFF)
    assert bool(re.search(r'[\u0B80-\u0BFF]', result['translated_content'])), "Expected Tamil script"


def test_english_passthrough():
    text = "Normal English notice text."
    result = TranslationService.translate_announcement(
        title="English Title",
        content=text,
        target_language="en"
    )
    assert result["translated_title"] == "English Title"
    assert result["translated_content"] == text


if __name__ == "__main__":
    test_kannada_translation()
    test_hindi_translation()
    test_telugu_translation()
    test_tamil_translation()
    test_english_passthrough()
    print("\n[SUCCESS] All 5 Translation Engine tests passed successfully!", flush=True)
    os._exit(0)
