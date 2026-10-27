"""AI chat: campus facts come only from real notices, and ordinary questions are not mistaken for 'who am I'."""
from fastapi.testclient import TestClient

from app.auth_test_helpers import bearer
from app.main import app

client = TestClient(app)
ADMIN = bearer("ESDev01")
STUDENT = bearer("1db23ci079")  # seeded student "Rakshitha S"


def _ask(prompt):
    res = client.post("/api/v1/ai/chat", headers=STUDENT, json={
        "prompt": prompt, "session_id": "t", "user_role": "Student", "full_name": "Test Student", "department": "CSE", "history": []})
    assert res.status_code == 200, res.text
    return res.json()


def test_a_campus_question_is_not_answered_with_the_profile_card():
    answer = _ask("What is the hostel curfew time?")["response"]
    assert "Verified Institutional Identity" not in answer, answer


def test_who_am_i_still_gets_the_profile_card():
    # The name comes from the signed-in account, not the request body.
    answer = _ask("who am i")["response"]
    assert "Rakshitha S" in answer and "Test Student" not in answer


def test_the_model_is_told_to_take_campus_facts_only_from_the_listed_notices(monkeypatch):
    from app.services.model_router import ModelRouter

    seen = {}

    def fake_route(self, **kwargs):
        seen.update(kwargs)
        return {"response": "ok", "category_badge": "", "context_badge": "", "suggested_actions": [],
                "navigation_target": None, "matched_announcements": [], "model_used": "fake", "copilot_action": None}

    monkeypatch.setattr(ModelRouter, "route_and_generate", fake_route)
    client.post("/api/v1/announcements", headers=ADMIN, json={
        "title": "Library closes at 4 PM on Friday", "description": "The library closes at 4 PM on Friday for maintenance.",
        "category_id": 1, "target_audience": "Entire College", "deliver_push": False, "deliver_in_app": False})
    _ask("When does the library close on Friday?")
    instruction = seen["system_instruction"]
    assert "Library closes at 4 PM on Friday" in instruction, "the matching notice must be given to the model"
    assert "ONLY from the notices listed" in instruction
    assert "couldn't find a notice" in instruction
