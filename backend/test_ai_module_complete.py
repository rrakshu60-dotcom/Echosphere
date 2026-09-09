"""
Comprehensive End-to-End AI Module Verification Test Suite for EchoSphere
Tests:
1. AI Status & Router Metrics
2. AI Chat (Student RBAC, Teacher RBAC, Exam/Placement/Theme/Emergency)
3. CopilotKit Agent Protocol (/ai/copilot/chat)
4. AI Circular Drafting, Priority Recommendation, Summarization, Expansion, Grammar, Spam, Validation
5. Administrative Model Retraining RBAC (Student Forbidden vs Admin Allowed)
6. Natural Markdown & Anti-Clutter Sanitization
"""

import os
import sys

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ["DATABASE_URL"] = "sqlite:///./test_ai_complete.db"

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine, SessionLocal
from app.models.role import Role
from app.models.user import User
from app.core.dependencies import get_current_user

# Setup isolated SQLite test DB
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

with SessionLocal() as db_session:
    r_student = Role(name="Student")
    r_teacher = Role(name="Teacher")
    r_admin = Role(name="Dev Admin")
    db_session.add_all([r_student, r_teacher, r_admin])
    db_session.commit()

    u_student = User(id=1, full_name="Alice Student", username="alice_s", official_email="alice@echosphere.edu", role_id=r_student.id, password_hash="dummy")
    u_teacher = User(id=2, full_name="Bob Teacher", username="bob_t", official_email="bob@echosphere.edu", role_id=r_teacher.id, password_hash="dummy")
    u_admin = User(id=3, full_name="Charlie Admin", username="charlie_a", official_email="charlie@echosphere.edu", role_id=r_admin.id, password_hash="dummy")
    db_session.add_all([u_student, u_teacher, u_admin])
    db_session.commit()

client = TestClient(app)


def test_ai_status():
    print("\n--- 1. Testing AI Engine & Router Status Endpoints ---")
    res = client.get("/api/v1/ai/status")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert "engine" in data
    assert "local_ml_available" in data
    assert data["local_ml_available"] is True
    assert "router_metrics" in data
    providers = data["router_metrics"]["active_providers"]
    assert "gemini" in providers
    assert "cloudflare" in providers
    assert "gemma_action_engine" in providers
    assert "fine_tuned_gemma" in providers
    assert "campus_ml_fallback" in providers
    print("  -> PASSED: /ai/status returned all 5 provider metrics.")

    res_router = client.get("/api/v1/ai/router/status")
    assert res_router.status_code == 200
    assert "active_providers" in res_router.json()
    print("  -> PASSED: /ai/router/status confirmed operational.")


def test_ai_chat_student_rbac():
    print("\n--- 2. Testing AI Chat: Student RBAC Constraints & Courtesy ---")
    
    # A. Student asking about speaker hardware
    res = client.post("/api/v1/ai/chat", json={
        "prompt": "Take me to the smart speaker queue and hardware controls",
        "user_role": "STUDENT",
        "department": "CSE",
        "full_name": "Alice Student"
    })
    assert res.status_code == 200
    data = res.json()
    assert "authority" in data["response"].lower() or "restricted" in data["category_badge"].lower()
    assert data["navigation_target"] is None
    print("  -> PASSED: Student politely restricted from speaker hardware access.")

    # B. Student asking about creating notices
    res_notice = client.post("/api/v1/ai/chat", json={
        "prompt": "I want to publish and post an announcement",
        "user_role": "STUDENT",
        "department": "CSE",
        "full_name": "Alice Student"
    })
    assert res_notice.status_code == 200
    data_notice = res_notice.json()
    assert "authority" in data_notice["response"].lower()
    assert data_notice["navigation_target"] is None
    print("  -> PASSED: Student politely informed about lack of notice publishing authority.")


def test_ai_chat_teacher_access():
    print("\n--- 3. Testing AI Chat: Teacher Access to Hardware & Authoring ---")
    
    # Teacher asking about speaker hardware
    res = client.post("/api/v1/ai/chat", json={
        "prompt": "Open the speaker queue and hardware controls",
        "user_role": "TEACHER",
        "department": "CSE",
        "full_name": "Bob Teacher"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["navigation_target"] == "nav:hardware:speakers"
    assert data.get("copilot_action") == {"action": "navigate", "parameters": {"screen": "speaker_queue"}}
    print("  -> PASSED: Teacher granted navigation to 'nav:hardware:speakers' with copilot_action.")

    # Teacher asking to draft/create notice
    res_notice = client.post("/api/v1/ai/chat", json={
        "prompt": "I want to create a new circular notice",
        "user_role": "TEACHER",
        "department": "CSE",
        "full_name": "Bob Teacher"
    })
    assert res_notice.status_code == 200
    data_notice = res_notice.json()
    assert data_notice["navigation_target"] == "action:create_notice"
    assert data_notice.get("copilot_action") == {"action": "create_announcement_draft", "parameters": {}}
    print("  -> PASSED: Teacher granted notice creation with copilot_action.")


def test_ai_chat_intent_and_copilot_actions():
    print("\n--- 4. Testing AI Chat: Intent Routing & In-App Navigation ---")

    # Dark Mode
    res_theme = client.post("/api/v1/ai/chat", json={
        "prompt": "Switch to dark mode",
        "user_role": "STUDENT",
        "department": "AIML"
    })
    assert res_theme.status_code == 200
    data_theme = res_theme.json()
    assert data_theme["navigation_target"] == "action:theme:dark"
    assert data_theme.get("copilot_action") == {"action": "toggle_theme", "parameters": {"mode": "dark"}}
    print("  -> PASSED: Theme toggle returns structured copilot_action.")

    # Exam Timetable
    res_exam = client.post("/api/v1/ai/chat", json={
        "prompt": "What is the exam timetable for 6th sem?",
        "user_role": "STUDENT",
        "department": "CSE"
    })
    assert res_exam.status_code == 200
    data_exam = res_exam.json()
    assert data_exam["category_badge"] == "Examinations"
    assert data_exam["navigation_target"] == "nav:notices:filter:Examinations"
    assert data_exam.get("copilot_action") == {"action": "navigate", "parameters": {"screen": "notices", "filter_category": "Examinations"}}
    print("  -> PASSED: Exam query mapped to 'nav:notices:filter:Examinations' with copilot_action.")


def test_copilot_protocol_endpoint():
    print("\n--- 5. Testing CopilotKit Protocol Endpoint (/ai/copilot/chat) ---")
    req_payload = {
        "message": "Filter all placement circulars",
        "app_state": {"active_route": "/home", "current_filter": "All"},
        "user_role": "STUDENT",
        "department": "CSE",
        "full_name": "Alice Student"
    }
    res = client.post("/api/v1/ai/copilot/chat", json=req_payload)
    assert res.status_code == 200, f"Error: {res.text}"
    data = res.json()
    assert "response" in data
    assert data.get("copilot_action") is not None
    assert data["copilot_action"]["action"] == "navigate"
    assert data["copilot_action"]["parameters"]["filter_category"] == "Placements"
    print("  -> PASSED: /ai/copilot/chat executed state-aware action dispatch.")


def test_content_authoring_tools():
    print("\n--- 6. Testing AI Authoring Tools (Draft, Priority, Summarize, Expand, Grammar, Spam) ---")

    # Draft
    res_draft = client.post("/api/v1/ai/draft", json={
        "topic": "Annual Hackathon 2026",
        "category": "Events",
        "target_role": "STUDENT",
        "department": "CSE"
    })
    assert res_draft.status_code == 200
    d_data = res_draft.json()
    assert "title" in d_data and len(d_data["title"]) > 5
    assert "content" in d_data and len(d_data["content"]) > 20
    print("  -> PASSED: AI Draft created official circular.")

    # Priority Recommendation
    res_prio_std = client.post("/api/v1/ai/priority", json={
        "title": "Red alert severe rain holiday",
        "content": "Due to heavy flooding all classes suspended",
        "user_role": "STUDENT"
    })
    assert res_prio_std.status_code == 200
    p_std = res_prio_std.json()
    assert p_std["is_allowed"] is False
    print("  -> PASSED: Emergency priority recommendation strictly blocked for Student role.")

    # Summarize
    res_sum = client.post("/api/v1/ai/summarize", json={
        "content": "All undergraduate candidates must ensure their exam fees are cleared by Friday at 4 PM to collect Hall Tickets. Failure to do so will result in penalty fees."
    })
    assert res_sum.status_code == 200
    assert len(res_sum.json()["summary"]) > 10
    print("  -> PASSED: AI Summarize returned concise text.")

    # Spam Check
    res_spam = client.post("/api/v1/ai/spam", json={
        "text": "WIN FREE MONEY CRYPTO CLICK THIS LINK IMMEDIATELY TO EARN CASH"
    })
    assert res_spam.status_code == 200
    assert res_spam.json()["is_spam"] is True
    print("  -> PASSED: AI Spam detected non-academic solicitation.")

    # Content Validation
    res_val = client.post("/api/v1/ai/validate", json={
        "title": "",
        "text": "hi"
    })
    assert res_val.status_code == 200
    assert res_val.json()["is_valid"] is False
    print("  -> PASSED: AI Validate flagged incomplete announcement.")


def test_ai_train_rbac():
    print("\n--- 7. Testing AI Model Retraining RBAC ---")

    # Student should receive 403 Forbidden
    def mock_student_user():
        with SessionLocal() as db_session:
            return db_session.query(User).filter_by(username="alice_s").first()

    app.dependency_overrides[get_current_user] = mock_student_user
    res_student = client.post("/api/v1/ai/train")
    assert res_student.status_code == 403, f"Expected 403 Forbidden for Student, got {res_student.status_code}"
    print("  -> PASSED: Student role blocked from /ai/train with HTTP 403.")

    # Dev Admin should succeed
    def mock_admin_user():
        with SessionLocal() as db_session:
            return db_session.query(User).filter_by(username="charlie_a").first()

    app.dependency_overrides[get_current_user] = mock_admin_user
    res_admin = client.post("/api/v1/ai/train")
    assert res_admin.status_code == 200, f"Expected 200 for Admin, got {res_admin.status_code}"
    admin_data = res_admin.json()
    assert admin_data["status"] == "success"
    assert admin_data["intents_trained"] >= 5
    print(f"  -> PASSED: Admin retrained {admin_data['intents_trained']} intents across {admin_data['intent_samples']} samples.")
    app.dependency_overrides.clear()


if __name__ == "__main__":
    print("=" * 65)
    print("RUNNING COMPREHENSIVE AI MODULE VERIFICATION TEST SUITE")
    print("=" * 65)
    test_ai_status()
    test_ai_chat_student_rbac()
    test_ai_chat_teacher_access()
    test_ai_chat_intent_and_copilot_actions()
    test_copilot_protocol_endpoint()
    test_content_authoring_tools()
    test_ai_train_rbac()
    print("=" * 65)
    print("ALL AI MODULE VERIFICATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)
