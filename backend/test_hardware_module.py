import sys
import os
from fastapi.testclient import TestClient


# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set SQLite test database URL
os.environ["DATABASE_URL"] = "sqlite:///./test_hardware.db"

# Update database engine to SQLite for testing
from app.db.database import Base, engine, get_db
from app.main import app

from app.core.dependencies import get_current_user
from app.models.role import Role
from app.models.user import User

def mock_get_current_user():
    return User(
        id=1,
        full_name="Admin Test User",
        official_email="admin@echosphere.edu",
        role=Role(name="Dev Admin"),
    )

app.dependency_overrides[get_current_user] = mock_get_current_user

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

client = TestClient(app)



def test_hardware_flow():
    print("--- 1. Testing Speaker Node Registration ---")
    reg_payload = {
        "name": "CSE Main Horn 1",
        "mac_address": "AA:BB:CC:11:22:33",
        "ip_address": "192.168.1.150",
        "zone": "Block A",
        "volume": 85
    }
    res = client.post("/api/v1/hardware/speakers/register", json=reg_payload)
    print(f"Register status: {res.status_code}, data: {res.json()}")
    assert res.status_code in (200, 201)
    node_id = res.json()["id"]

    print("--- 2. Testing Speaker List ---")
    res_list = client.get("/api/v1/hardware/speakers")
    print(f"List status: {res_list.status_code}, count: {len(res_list.json())}")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    print("--- 3. Testing Speaker Heartbeat ---")
    hb_payload = {
        "mac_address": "AA:BB:CC:11:22:33",
        "ip_address": "192.168.1.150",
        "cpu_usage": 22.4,
        "memory_usage": 45.1,
        "disk_space": 60.0,
        "status": "ONLINE"
    }
    res_hb = client.post("/api/v1/hardware/speakers/heartbeat", json=hb_payload)
    print(f"Heartbeat status: {res_hb.status_code}, data: {res_hb.json()}")
    assert res_hb.status_code == 200

    print("--- 4. Testing Control Command ---")
    ctrl_payload = {
        "command": "TEST_SPEAKER",
        "volume": 90
    }
    res_ctrl = client.post(f"/api/v1/hardware/speakers/{node_id}/control", json=ctrl_payload)
    print(f"Control status: {res_ctrl.status_code}, data: {res_ctrl.json()}")
    assert res_ctrl.status_code == 200

    print("--- 5. Testing Emergency Override ---")
    ovr_payload = {
        "title": "TEST EMERGENCY ADVISORY",
        "message": "Immediate campus evacuation test signal.",
        "zone": "College-Wide"
    }
    res_ovr = client.post("/api/v1/hardware/speakers/override", json=ovr_payload)
    print(f"Emergency override status: {res_ovr.status_code}, data: {res_ovr.json()}")
    assert res_ovr.status_code == 200

    print("--- 6. Testing Speaker Queue Fetch ---")
    res_q = client.get("/api/v1/hardware/queue")
    print(f"Queue status: {res_q.status_code}, items: {len(res_q.json())}")
    assert res_q.status_code == 200

    print("\nALL HARDWARE BACKEND TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_hardware_flow()
