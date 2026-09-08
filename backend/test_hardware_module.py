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

from app.db.database import SessionLocal
with SessionLocal() as db_session:
    r = Role(name="Dev Admin")
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    u = User(id=1, full_name="Admin Test User", username="admin_test", official_email="admin@echosphere.edu", role_id=r.id, password_hash="dummy")
    db_session.add(u)
    db_session.commit()

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
    assert "announcement_id" in res_ovr.json()

    print("--- 6. Testing Speaker Queue Fetch ---")
    res_q = client.get("/api/v1/hardware/queue")
    print(f"Queue status: {res_q.status_code}, items: {len(res_q.json())}")
    assert res_q.status_code == 200
    assert len(res_q.json()) >= 1
    queue_id = res_q.json()[0]["id"]

    print("--- 7. Testing Queue Action (Play/Pause/Resume/Cancel) ---")
    for act in ["play", "pause", "resume", "skip", "cancel"]:
        res_act = client.post(f"/api/v1/hardware/queue/{queue_id}/action?action={act}")
        print(f"Queue action '{act}' status: {res_act.status_code}, data: {res_act.json()}")
        assert res_act.status_code == 200
        assert res_act.json()["status"] == "success"

    print("--- 8. Testing Queue Reorder ---")
    res_reorder = client.post("/api/v1/hardware/queue/reorder", json={"queue_ids": [queue_id]})
    print(f"Reorder status: {res_reorder.status_code}, data: {res_reorder.json()}")
    assert res_reorder.status_code == 200
    assert res_reorder.json()["status"] == "success"

    print("--- 9. Testing Announcement Broadcast to Speaker Node ---")
    # Broadcast using the emergency announcement created earlier
    ann_id = res_ovr.json()["announcement_id"]
    res_bcast = client.post(f"/api/v1/hardware/speakers/{node_id}/broadcast", json={"announcement_id": ann_id})
    print(f"Broadcast status: {res_bcast.status_code}, data: {res_bcast.json()}")
    assert res_bcast.status_code == 200
    assert res_bcast.json()["status"] == "success"

    print("--- 10. Testing Auto-Playback on Empty Queue (Push Now) ---")
    # Clear queue items first to ensure clean state
    with SessionLocal() as db_session:
        from app.models.speaker_queue import SpeakerQueue
        db_session.query(SpeakerQueue).delete()
        db_session.commit()

    # Create announcement with deliver_speaker=True
    notice1_payload = {
        "title": "Automated Speaker Notice 1",
        "description": "This is a live broadcast testing auto-playback on empty queue.",
        "category_id": 1,
        "priority": "NORMAL",
        "emergency_level": "NORMAL",
        "deliver_speaker": True,
        "speaker_node_id": node_id
    }
    res_n1 = client.post("/api/v1/announcements", json=notice1_payload)
    print(f"Notice 1 Create status: {res_n1.status_code}")
    assert res_n1.status_code == 200
    n1_id = res_n1.json()["id"]

    # Verify queue immediately has item with status 'Playing' and played_at set
    res_q_auto = client.get("/api/v1/hardware/queue")
    assert res_q_auto.status_code == 200
    q_data = res_q_auto.json()
    assert len(q_data) >= 1
    first_item = q_data[0]
    print(f"First item in queue: id={first_item['id']}, status={first_item['status']}, played_at={first_item['played_at']}")
    assert first_item["status"] == "Playing"
    assert first_item["played_at"] is not None

    print("--- 11. Testing Auto-Enqueue for Second Notice (Next in Queue) ---")
    notice2_payload = {
        "title": "Automated Speaker Notice 2",
        "description": "Second notice queued behind active broadcast.",
        "category_id": 1,
        "priority": "NORMAL",
        "emergency_level": "NORMAL",
        "deliver_speaker": True,
        "speaker_node_id": node_id
    }
    res_n2 = client.post("/api/v1/announcements", json=notice2_payload)
    assert res_n2.status_code == 200
    n2_id = res_n2.json()["id"]

    res_q_auto2 = client.get("/api/v1/hardware/queue")
    q_data2 = res_q_auto2.json()
    assert len(q_data2) >= 2
    assert q_data2[0]["status"] == "Playing"
    assert q_data2[1]["status"] in ("Next in Queue", "Queued")
    print(f"Second item in queue: id={q_data2[1]['id']}, status={q_data2[1]['status']}")

    print("--- 12. Testing Automated Queue Progression (Advance) ---")
    res_adv = client.post("/api/v1/hardware/queue/advance")
    assert res_adv.status_code == 200
    print(f"Queue advance response: {res_adv.json()}")

    res_q_after = client.get("/api/v1/hardware/queue")
    q_after_data = res_q_after.json()
    # Item 2 should now be Playing!
    playing_items = [item for item in q_after_data if item["status"] == "Playing"]
    print(f"Currently playing items after advance: {len(playing_items)}")
    assert len(playing_items) >= 1
    assert playing_items[0]["announcement_id"] == n2_id
    print(f"  -> SUCCESS: Queue automatically advanced to Notice 2 (id: {n2_id}) as 'Playing'!")

    print("\nALL HARDWARE AND SPEAKER QUEUE AUTOMATION TESTS PASSED SUCCESSFULLY (100%)!")

if __name__ == "__main__":
    test_hardware_flow()


