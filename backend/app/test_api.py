import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    print("[PASS] Health Check API Passed")

def test_ai_chat_endpoint():
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "prompt": "When are semester lab exams for CSE?",
            "user_role": "STUDENT",
            "department": "CSE",
            "full_name": "Student User"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "category_badge" in data
    assert "context_badge" in data
    print("[PASS] Context-Aware AI Chat API Endpoint Passed")

def test_ai_conversational_questions():
    # Test 'who r u?'
    r1 = client.post("/api/v1/ai/chat", json={"prompt": "who r u?", "user_role": "STUDENT", "department": "CSE", "full_name": "Harshith"})
    assert r1.status_code == 200
    assert "EchoSphere AI Assistant" in r1.json()["response"]
    assert "Harshith" in r1.json()["response"]

    # Test 'hello'
    r2 = client.post("/api/v1/ai/chat", json={"prompt": "hello", "user_role": "STUDENT", "department": "CSE", "full_name": "Harshith"})
    assert r2.status_code == 200
    assert "Hello Harshith!" in r2.json()["response"]

    # Test 'thank you'
    r3 = client.post("/api/v1/ai/chat", json={"prompt": "thank you!", "user_role": "STUDENT", "department": "CSE", "full_name": "Harshith"})
    assert r3.status_code == 200
    assert "welcome" in r3.json()["response"].lower()

    print("[PASS] AI Conversational & Simple Question Handler Passed")

def test_ai_draft_endpoint():
    response = client.post(
        "/api/v1/ai/draft",
        json={
            "topic": "Rainfall Alert",
            "category": "Emergency",
            "department": "CSE"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "title" in data
    assert "suggested_priority" in data
    print("[PASS] AI Notice Draft Endpoint Passed")

def test_ai_priority_endpoint():
    response = client.post(
        "/api/v1/ai/priority",
        json={
            "title": "Emergency Rainfall",
            "content": "Campus closed due to heavy flood",
            "user_role": "HOD"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "EMERGENCY"
    print("[PASS] AI Priority Recommendation Endpoint Passed")

def test_ai_extended_endpoints():
    r1 = client.post("/api/v1/ai/emergency", json={"text": "Heavy flood alert campus closed", "user_role": "HOD"})
    assert r1.status_code == 200 and r1.json()["is_emergency"] is True

    r2 = client.post("/api/v1/ai/spam", json={"text": "Win money now free cash crypto"})
    assert r2.status_code == 200 and r2.json()["is_spam"] is True

    r3 = client.post("/api/v1/ai/validate", json={"text": "Short notice", "title": "Test"})
    assert r3.status_code == 200 and r3.json()["is_valid"] is False

    r4 = client.post("/api/v1/ai/duplicate", json={"new_title": "Notice A", "new_text": "Notice A content", "department": "CSE"})
    assert r4.status_code == 200 and "is_duplicate" in r4.json()

    r5 = client.post("/api/v1/ai/classify", json={"announcement": "Placement drive for Google tomorrow"})
    assert r5.status_code == 200 and r5.json()["category"] == "Placements"

    r6 = client.post("/api/v1/ai/expand", json={"text": "Lab exam postponed", "category": "Examinations"})
    assert r6.status_code == 200 and "expanded_text" in r6.json()

    r7 = client.post("/api/v1/ai/grammar", json={"text": "lab exam starts tomorrow at 9 am"})
    assert r7.status_code == 200 and r7.json()["corrected_text"].startswith("Lab")

    print("[PASS] Extended AIML Microservice Endpoints (Emergency, Spam, Validation, Duplicate, Classifier, Expand, Grammar) Passed")

if __name__ == "__main__":
    test_health_check()
    test_ai_chat_endpoint()
    test_ai_conversational_questions()
    test_ai_draft_endpoint()
    test_ai_priority_endpoint()
    test_ai_extended_endpoints()
    print("\n[SUCCESS] ALL CONVERSATIONAL & AIML BACKEND API INTEGRATION TESTS PASSED SUCCESSFULLY!")
