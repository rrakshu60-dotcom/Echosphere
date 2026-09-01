import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.db.database import get_db, Base, engine
from app.seeders.role import seed_roles
from app.seeders.user import seed_users
from app.seeders.department import seed_departments
from app.seeders.category import seed_categories
from app.seeders.delivery_type import seed_delivery_types

# Re-create fresh schema for test environment
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

# Initialize DB seeders for testing
db = next(get_db())
seed_roles(db)
seed_departments(db)
seed_categories(db)
seed_delivery_types(db)
seed_users(db)

client = TestClient(app)

def test_rbac_require_roles_fix():
    print("\n--- Testing RBAC & Require Roles Fixes ---")
    
    # 1. Login as Dev Admin
    r_login = client.post("/api/v1/auth/login", json={
        "identifier": "ESDev01",
        "password": "rakshitha@1228"
    })
    assert r_login.status_code == 200, f"Dev Admin login failed: {r_login.text}"
    dev_token = r_login.json()["access_token"]
    headers_dev = {"Authorization": f"Bearer {dev_token}"}

    # 2. Test User Management List (Previously threw 403 due to list param bug)
    r_users = client.get("/api/v1/users/", headers=headers_dev)
    assert r_users.status_code == 200, f"List users failed for Dev Admin: {r_users.text}"
    users_data = r_users.json()
    assert len(users_data) > 0
    print("[PASS] User List API works for Dev Admin (Fixed require_roles bug)")

    # 3. Test Create User API (POST /users/)
    new_user_payload = {
        "full_name": "Test RBAC Teacher",
        "official_email": "test.rbac.teacher@echosphere.edu",
        "password": "Password@123",
        "role_name": "Teacher",
        "employee_id": "EMP_RBAC_999"
    }
    r_create = client.post("/api/v1/users/", json=new_user_payload, headers=headers_dev)
    assert r_create.status_code == 201, f"Create user failed: {r_create.text}"
    created_user = r_create.json()
    created_id = created_user["id"]
    assert created_user["full_name"] == "Test RBAC Teacher"
    print(f"[PASS] User Creation API (POST /users/) passed. Created User ID: {created_id}")

    # 4. Test Update User Role / Status API (PUT /users/{id})
    r_update = client.put(f"/api/v1/users/{created_id}", json={"is_active": False}, headers=headers_dev)
    assert r_update.status_code == 200
    assert r_update.json()["is_active"] is False
    print(f"[PASS] User Update API (PUT /users/{created_id}) passed")

    # 5. Test Delete User API (DELETE /users/{id})
    r_del_user = client.delete(f"/api/v1/users/{created_id}", headers=headers_dev)
    assert r_del_user.status_code == 200
    print(f"[PASS] User Delete API (DELETE /users/{created_id}) passed")

def test_hardware_crud():
    print("\n--- Testing Hardware & Speaker Queue CRUD ---")
    
    # Login as Dev Admin
    r_login = client.post("/api/v1/auth/login", json={
        "identifier": "ESDev01",
        "password": "rakshitha@1228"
    })
    dev_token = r_login.json()["access_token"]
    headers_dev = {"Authorization": f"Bearer {dev_token}"}

    # 1. Register Speaker Node
    node_payload = {
        "name": "Test Lab Horn Speaker",
        "mac_address": "99:88:77:66:55:44",
        "ip_address": "192.168.1.250",
        "zone": "Lab-Block"
    }
    r_reg = client.post("/api/v1/hardware/speakers/register", json=node_payload, headers=headers_dev)
    assert r_reg.status_code in [201, 400], f"Register speaker failed: {r_reg.text}"
    
    # 2. Get Speaker Nodes
    r_nodes = client.get("/api/v1/hardware/speakers", headers=headers_dev)
    assert r_nodes.status_code == 200
    nodes = r_nodes.json()
    assert len(nodes) > 0
    test_node_id = nodes[0]["id"]
    print(f"[PASS] List Speaker Nodes passed. Node ID: {test_node_id}")

    # 3. Delete Speaker Node API
    r_del_node = client.delete(f"/api/v1/hardware/speakers/{test_node_id}", headers=headers_dev)
    assert r_del_node.status_code == 200
    print(f"[PASS] Delete Speaker Node API (DELETE /hardware/speakers/{test_node_id}) passed")

def test_executive_auto_publish_privilege():
    print("\n--- Testing Executive Auto-Publish Privilege (No Approval Required) ---")
    
    # 1. Login as Dev Admin
    r_login = client.post("/api/v1/auth/login", json={
        "identifier": "ESDev01",
        "password": "rakshitha@1228"
    })
    dev_token = r_login.json()["access_token"]
    headers_dev = {"Authorization": f"Bearer {dev_token}"}

    # 2. Dev Admin creates announcement
    ann_payload = {
        "title": "Executive Policy Update Notice",
        "description": "This notice is published directly by Dev Admin without requiring approval.",
        "category_id": 1,
        "priority": "High"
    }
    r_ann = client.post("/api/v1/announcements", json=ann_payload, headers=headers_dev)
    assert r_ann.status_code == 200, f"Dev Admin announcement creation failed: {r_ann.text}"
    created = r_ann.json()
    assert created["status"].upper() == "PUBLISHED", f"Expected PUBLISHED status for Dev Admin, got: {created['status']}"
    print(f"[PASS] Dev Admin announcement auto-published directly (Status: {created['status']})")


def test_swagger_token_endpoint():
    print("\n--- Testing Swagger OAuth2 Token Endpoint (/api/v1/auth/token) ---")
    r_token = client.post("/api/v1/auth/token", data={
        "username": "ESDev01",
        "password": "rakshitha@1228"
    })
    assert r_token.status_code == 200, f"OAuth2 token login failed: {r_token.text}"
    token_data = r_token.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["role"] == "Dev Admin"
    print("[PASS] Swagger OAuth2 Token Endpoint (/api/v1/auth/token) passed successfully!")


if __name__ == "__main__":
    test_rbac_require_roles_fix()
    test_hardware_crud()
    test_executive_auto_publish_privilege()
    test_swagger_token_endpoint()
    print("\n[SUCCESS] ALL RBAC & CRUD INTEGRATION TESTS PASSED SUCCESSFULLY!")


