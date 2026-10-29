"""AI cleanup (owner's decision, 2026-10-27): broken AI features are gone, and the chatbot, notice search
and emergency check give correct answers even when no cloud AI model is reachable."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")
STUDENT = bearer("1db23ci079")


def _notice(title, description, status=None):
    tag = uuid.uuid4().hex[:6]
    res = client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": f"{title} {tag}", "description": description, "category_id": 1,
        "target_audience": "Entire College", "deliver_push": False, "deliver_in_app": False})
    assert res.status_code in (200, 201), res.text
    notice = res.json()
    if status:
        from app.db.database import SessionLocal
        from app.models.announcement import Announcement
        with SessionLocal() as db:
            row = db.get(Announcement, notice["id"])
            row.status = status
            db.commit()
    return notice


def _ask(prompt, headers=STUDENT):
    res = client.post("/api/v1/ai/chat", headers=headers, json={"prompt": prompt, "session_id": "t", "history": []})
    assert res.status_code == 200, res.text
    return res.json()


# ---------------------------------------------------------------- removed features stay removed

@pytest.mark.parametrize("path", [
    "/api/v1/ai/expand", "/api/v1/ai/grammar", "/api/v1/ai/copilot/chat", "/api/v1/ai/classify",
    "/api/v1/ai/intent", "/api/v1/announcements/translate", "/api/v1/announcements/1/translate",
    "/api/v1/announcements/ocr-document",
    "/api/v1/announcements/voice-to-notice",  # voice dictation, removed on the owner's decision (2026-10-29)
])
def test_removed_ai_endpoints_are_gone(path):
    routes = {getattr(r, "path", "").replace("{announcement_id}", "1") for r in app.routes}
    assert path not in routes, f"{path} should no longer exist"
    assert client.post(path, headers=ADMIN, json={}).status_code in (404, 405)


# ---------------------------------------------------------------- chatbot

def test_chat_answers_a_campus_question_from_the_matching_notice():
    notice = _notice("Mid-semester exams for 3rd year CSE",
                     "Mid-semester exams for 3rd year CSE start on 12 November in Block A at 10 AM. Bring hall tickets.")
    reply = _ask("When are the CSE mid-sem exams?")
    assert reply["matched_announcements"], reply
    assert reply["matched_announcements"][0]["id"] == notice["id"]
    assert "12 November" in reply["response"], reply["response"]


def test_chat_says_it_found_no_notice_instead_of_inventing_facts():
    for question in ("What is the bus fee for this year?", "What is on the hostel mess menu on Sunday?"):
        text = _ask(question)["response"]
        assert "couldn't find a notice" in text.lower(), text


def test_chat_never_adds_campus_facts_that_no_notice_contains():
    # The only placement notice (seeded) is Microsoft's, CGPA 8.0. The old offline answer added
    # "CGPA >= 7.0" and a list of companies that came from no notice at all.
    text = _ask("Which companies are coming for placements?")["response"]
    for invented in ("7.0", "Google", "TCS", "Infosys", "Accenture"):
        assert invented not in text, f"{invented!r} is not from any notice: {text}"


def test_chat_does_not_list_unrelated_notices():
    _notice("Water supply interruption in hostel", "Water supply in the boys hostel will be off on Sunday from 9 AM.")
    exam = _notice("Lab internal exam for 2nd year ECE", "The ECE lab internal exam is on 20 November in the Analog Lab.")
    reply = _ask("when is the ECE lab internal exam?")
    titles = [m["title"] for m in reply["matched_announcements"]]
    assert titles and titles[0] == exam["title"], titles
    assert not any("Water supply" in t for t in titles), titles


def test_students_never_get_draft_notices_from_chat():
    _notice("Draft: canteen price revision", "Canteen meal prices change from 1 December.", status="Draft")
    reply = _ask("Are canteen prices changing?")
    assert not any("canteen price revision" in m["title"] for m in reply["matched_announcements"]), reply
    assert "1 December" not in reply["response"]


def test_chat_still_runs_app_commands():
    assert _ask("switch to dark mode")["copilot_action"]["action"] == "toggle_theme"
    assert _ask("open the speaker queue", headers=ADMIN)["navigation_target"] == "nav:hardware:speakers"


def test_the_campus_model_is_given_the_matching_notices(monkeypatch):
    from app.services import model_router

    router = model_router.ModelRouter.get_instance()
    seen = {}

    def fake_generate(prompt, system_instruction="", **kwargs):
        seen["system_instruction"] = system_instruction
        return "From the notice: the talk is in the Main Auditorium."

    monkeypatch.setattr(model_router, "USE_FINE_TUNED_GEMMA", True)
    monkeypatch.setattr(router.fine_tuned_gemma, "is_configured", lambda: True)
    monkeypatch.setattr(router.fine_tuned_gemma, "generate", fake_generate)
    # (Titles here must not start with "Seminar on": test_notice_records searches for that phrase.)
    notice = _notice("Robotics guest talk", "A guest talk about robotics is on 18 November in the Main Auditorium.")
    _ask("Where is the robotics guest talk?")
    assert notice["title"] in seen.get("system_instruction", ""), "the model must see the notice it answers from"


# ---------------------------------------------------------------- notice search

def test_search_finds_notices_with_different_wording():
    from app.db.database import SessionLocal
    from app.services.neural_rag import NeuralRAG

    notice = _notice("Semester examination timetable released",
                     "The timetable for the end semester examinations is now available for all branches.")
    with SessionLocal() as db:
        hits = NeuralRAG.get_instance().search_notices(db, "end sem exam time table", role="STUDENT")
    assert hits and hits[0]["id"] == notice["id"], hits


def test_search_returns_nothing_for_a_question_no_notice_answers():
    from app.db.database import SessionLocal
    from app.services.neural_rag import NeuralRAG

    with SessionLocal() as db:
        assert NeuralRAG.get_instance().search_notices(db, "quantum teleportation lecture", role="STUDENT") == []


def test_search_sees_new_notices_immediately():
    from app.db.database import SessionLocal
    from app.services.neural_rag import NeuralRAG

    rag = NeuralRAG.get_instance()
    with SessionLocal() as db:
        rag.search_notices(db, "anything", role="STUDENT")
    notice = _notice("Blood donation camp", "A blood donation camp is in the Seminar Hall on 22 November.")
    with SessionLocal() as db:
        hits = rag.search_notices(db, "blood donation camp", role="STUDENT")
    assert hits and hits[0]["id"] == notice["id"], hits


def test_grounding_context_includes_live_notices():
    from app.db.database import SessionLocal
    from app.services.neural_rag import NeuralRAG

    notice = _notice("Library extended hours", "The central library stays open until 10 PM during exam week.")
    with SessionLocal() as db:
        context = NeuralRAG.get_instance().build_grounding_context("library hours", db_session=db, department="CSE")
    assert notice["title"] in context, context


# ---------------------------------------------------------------- emergency check

def _emergency(text, headers=STUDENT):
    res = client.post("/api/v1/ai/emergency", headers=headers, json={"text": text})
    assert res.status_code == 200, res.text
    return res.json()


@pytest.mark.parametrize("text", [
    "Fire in Block B, evacuate the building now",
    "Gas leak near the chemistry lab, leave the area immediately",
    "Earthquake tremors felt, assemble on the main ground",
    "College closed today due to heavy rain red alert",
    "Medical emergency in the library, ambulance on the way",
])
def test_real_emergencies_are_flagged_whoever_asks(text):
    assert _emergency(text)["is_emergency"] is True, text


@pytest.mark.parametrize("text", [
    "Placement training session on Monday in Seminar Hall",
    "Fire safety awareness workshop next Friday",
    "Mock fire drill scheduled for 25 November at 11 AM",
    "Latest brain-teaser contest results are out",
    "Cultural fest registrations are closed",
])
def test_ordinary_notices_are_not_flagged(text):
    assert _emergency(text)["is_emergency"] is False, text


def test_only_authorised_roles_may_publish_an_emergency():
    text = "Fire in Block B, evacuate the building now"
    assert _emergency(text, headers=STUDENT)["can_publish_emergency"] is False
    assert _emergency(text, headers=ADMIN)["can_publish_emergency"] is True


def test_priority_suggestion_does_not_mistake_training_for_rain():
    res = client.post("/api/v1/ai/priority", headers=ADMIN, json={
        "title": "Placement training", "content": "Aptitude training for final years on Monday."})
    assert res.status_code == 200, res.text
    assert res.json()["priority"] != "EMERGENCY" and res.json()["category"] != "Emergency", res.json()
