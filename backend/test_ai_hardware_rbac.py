"""
Comprehensive RBAC and Speaker Queue Access Verification Test
Tests:
1. Hardware endpoints RBAC enforcement (Student blocked with 403 Forbidden)
2. AI features RBAC enforcement (Speaker queue questions blocked for Student)
3. AI priority enforcement (Emergency priority blocked/capped for Student)
4. AI train endpoint RBAC enforcement (Student blocked with 403 Forbidden)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.jwt_handler import create_access_token
from app.db.database import get_db, SessionLocal
from app.models.user import User
from app.models.role import Role
from app.services.ai_service import AIService
from app.services.echosphere_ml_engine import EchoSphereMLEngine, CampusMLEngine
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("RUNNING RBAC & HARDWARE ACCESS VERIFICATION TESTS")
    print("=" * 60)

    db = SessionLocal()
    try:
        # Create or find a test student and a test teacher/admin
        student_user = db.query(User).join(Role).filter(Role.name == "Student").first()
        admin_user = db.query(User).join(Role).filter(Role.name.in_(["Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher"])).first()

        student_token = create_access_token(data={"sub": student_user.official_email, "role": "Student"}) if student_user else None
        admin_token = create_access_token(data={"sub": admin_user.official_email, "role": admin_user.role.name}) if admin_user else None

        student_headers = {"Authorization": f"Bearer {student_token}"} if student_token else {}
        admin_headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else {}

        # TEST 1: Student GET /hardware/queue -> Expect 403
        res = client.get("/api/v1/hardware/queue", headers=student_headers)
        print(f"[TEST 1] Student GET /hardware/queue: Status {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for student on /hardware/queue, got {res.status_code}"
        print("  -> PASSED: Student receives 403 Forbidden on /hardware/queue")

        # TEST 2: Student GET /hardware/speakers -> Expect 403
        res = client.get("/api/v1/hardware/speakers", headers=student_headers)
        print(f"[TEST 2] Student GET /hardware/speakers: Status {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for student on /hardware/speakers, got {res.status_code}"
        print("  -> PASSED: Student receives 403 Forbidden on /hardware/speakers")

        # TEST 3: Student POST /hardware/speakers/override -> Expect 403
        res = client.post("/api/v1/hardware/speakers/override", json={"title": "Test", "message": "Emergency"}, headers=student_headers)
        print(f"[TEST 3] Student POST /hardware/speakers/override: Status {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for student on /hardware/speakers/override, got {res.status_code}"
        print("  -> PASSED: Student receives 403 Forbidden on /hardware/speakers/override")

        # TEST 4: Student POST /ai/train -> Expect 403
        res = client.post("/api/v1/ai/train", headers=student_headers)
        print(f"[TEST 4] Student POST /ai/train: Status {res.status_code}")
        assert res.status_code == 403, f"Expected 403 for student on /ai/train, got {res.status_code}"
        print("  -> PASSED: Student receives 403 Forbidden on /ai/train")

        # TEST 5: Student asks AI chat about speaker queue -> Expect Access Restricted & navigation_target None
        chat_student = AIService.process_chat(
            prompt="What is playing on the speaker queue right now?",
            user_role="STUDENT",
            full_name="Alice Student",
            department="CSE",
            db=db
        )
        print(f"[TEST 5] Student AI Chat for Speaker Queue: Category = '{chat_student['category_badge']}', Target = '{chat_student['navigation_target']}'")
        assert chat_student['category_badge'] == "Access Restricted", f"Expected 'Access Restricted', got {chat_student['category_badge']}"
        assert chat_student['navigation_target'] is None, f"Expected navigation_target to be None, got {chat_student['navigation_target']}"
        assert "don't have the authority" in chat_student['response'].lower() or "authority" in chat_student['response'].lower()
        print("  -> PASSED: AI politely states it doesn't have the authority to disclose speaker queue information")

        # TEST 6: Admin/Teacher asks AI chat about speaker queue -> Expect allowed navigation
        chat_admin = AIService.process_chat(
            prompt="What is playing on the speaker queue right now?",
            user_role="TEACHER",
            full_name="Prof. Sharma",
            department="CSE",
            db=db
        )
        print(f"[TEST 6] Teacher AI Chat for Speaker Queue: Category = '{chat_admin['category_badge']}', Target = '{chat_admin['navigation_target']}'")
        assert chat_admin['category_badge'] == "Smart Speaker Hardware"
        assert chat_admin['navigation_target'] == "nav:hardware:speakers"
        print("  -> PASSED: Teacher is granted access to speaker hardware navigation")

        # TEST 7: AI Priority Recommendation for Student with Emergency Text -> Expect Capped
        prio_student = AIService.recommend_priority(
            title="Fire outbreak in chemistry lab evacuate immediately",
            content="Evacuate the main building",
            user_role="STUDENT"
        )
        print(f"[TEST 7] Student Emergency Priority: Recommended = {prio_student['priority']}, Allowed = {prio_student['is_allowed']}")
        assert prio_student['is_allowed'] is False, "Student should not be allowed to set Emergency priority"
        assert prio_student['priority'] != "EMERGENCY", "Student priority should be capped below EMERGENCY"
        print("  -> PASSED: Emergency priority is blocked/capped for student role")

        # TEST 8: AI Priority Recommendation for Principal with Emergency Text -> Expect Allowed
        prio_admin = AIService.recommend_priority(
            title="Fire outbreak in chemistry lab evacuate immediately",
            content="Evacuate the main building",
            user_role="PRINCIPAL"
        )
        print(f"[TEST 8] Principal Emergency Priority: Recommended = {prio_admin['priority']}, Allowed = {prio_admin['is_allowed']}")
        assert prio_admin['is_allowed'] is True, "Principal should be allowed to set Emergency priority"
        assert prio_admin['priority'] == "EMERGENCY"
        print("  -> PASSED: Principal is permitted to broadcast EMERGENCY priority")

        print("=" * 60)
        print("ALL 8 RBAC & HARDWARE SECURITY TESTS PASSED SUCCESSFULLY (100%)!")
        print("=" * 60)
    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
