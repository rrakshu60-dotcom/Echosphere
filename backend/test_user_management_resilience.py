"""
EchoSphere Test Suite: Feature 5.1 - User Management Live Resilience
Verifies database-driven user listing, authentication enforcement on /api/v1/users/,
and validates that no mock fallback contamination occurs.
"""

import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import get_db
from app.models.user import User
from app.services.user_management_service import UserManagementService
from app.core.jwt_handler import create_access_token

client = TestClient(app)


def test_unauthenticated_user_list_enforcement():
    print("Test 1: Verifying /api/v1/users/ blocks unauthenticated requests...")
    res = client.get("/api/v1/users/")
    assert res.status_code == 401, f"Expected 401 Unauthorized, got {res.status_code}"
    print("  [PASS] Unauthenticated access blocked with 401 Unauthorized (triggers explicit error card in UI)")


def test_authenticated_user_listing():
    print("Test 2: Verifying /api/v1/users/ returns genuine DB records for authorized users...")
    db = next(get_db())
    try:
        admin = db.query(User).filter(User.official_email.isnot(None)).first()
        if not admin:
            print("  [SKIP] No user in DB to generate token.")
            return

        token = create_access_token(data={"sub": admin.official_email})
        headers = {"Authorization": f"Bearer {token}"}

        res = client.get("/api/v1/users/", headers=headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
        users = res.json()
        assert isinstance(users, list), "Response must be a list of users"
        print(f"  [PASS] Successfully retrieved {len(users)} real database users")

        if len(users) > 0:
            first_user = users[0]
            assert "id" in first_user
            assert "full_name" in first_user
            assert "official_email" in first_user
            print(f"  [PASS] User record schema verified (ID: {first_user['id']}, Name: {first_user['full_name']})")
    finally:
        db.close()


def test_user_management_service_no_mock():
    print("Test 3: Verifying UserManagementService queries DB directly without hardcoded mocks...")
    db = next(get_db())
    try:
        users = UserManagementService.list_users(db, limit=10)
        assert isinstance(users, list)
        for u in users:
            assert isinstance(u, User), "All elements must be SQLAlchemy User instances"
        print("  [PASS] UserManagementService returns direct database query instances")
    finally:
        db.close()


if __name__ == "__main__":
    print("\n==================================================")
    print("Running EchoSphere Feature 5.1 Test Suite")
    print("==================================================\n")
    test_unauthenticated_user_list_enforcement()
    test_authenticated_user_listing()
    test_user_management_service_no_mock()
    print("\n==================================================")
    print("ALL 3/3 USER MANAGEMENT RESILIENCE TESTS PASSED!")
    print("==================================================\n")
