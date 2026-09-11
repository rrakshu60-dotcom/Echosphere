import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app
from app.db.database import Base, engine, get_db
from app.seeders.role import seed_roles
from app.seeders.department import seed_departments
from app.seeders.category import seed_categories
from app.seeders.delivery_type import seed_delivery_types
from app.seeders.user import seed_users

client = TestClient(app)

def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        from app.models.role import Role
        if db.query(Role).count() == 0:
            seed_roles(db)
            seed_departments(db)
            seed_categories(db)
            seed_delivery_types(db)
            seed_users(db)
    finally:
        db.close()

def test_full_approval_workflow():
    print("\n--- [1/6] Setting Up Database & Testing User Authentication ---")
    setup_test_db()

    # 1. Login as Teacher (Dr. B Kursheed)
    r_teach = client.post("/api/v1/auth/login", json={
        "identifier": "dbitaimlt022022",
        "password": "Kursh@2022"
    })
    assert r_teach.status_code == 200, f"Teacher login failed: {r_teach.text}"
    teacher_token = r_teach.json()["access_token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    print("  [PASS] Teacher authenticated successfully.")

    # 2. Login as HoD (Dr. AIML HoD)
    r_hod = client.post("/api/v1/auth/login", json={
        "identifier": "hod_aiml",
        "password": "Hod@123"
    })
    assert r_hod.status_code == 200, f"HoD login failed: {r_hod.text}"
    hod_token = r_hod.json()["access_token"]
    hod_headers = {"Authorization": f"Bearer {hod_token}"}
    print("  [PASS] HoD authenticated successfully.")

    # 3. Login as Student (Rakshitha S)
    r_stud = client.post("/api/v1/auth/login", json={
        "identifier": "1db23ci079",
        "password": "rakshitha@1228"
    })
    assert r_stud.status_code == 200, f"Student login failed: {r_stud.text}"
    student_token = r_stud.json()["access_token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("  [PASS] Student authenticated successfully.")

    print("\n--- [2/6] Teacher Submits Notice Requiring Approval ---")
    notice_payload = {
        "title": "Machine Learning Lab Practical Test Schedule",
        "description": "The 5th Semester AIML practical tests will commence on Monday in Lab 3.",
        "category_id": 1,
        "priority": "High",
        "target_audience": "AIML Department",
        "deliver_in_app": True,
        "deliver_push": True
    }
    r_create = client.post("/api/v1/announcements", json=notice_payload, headers=teacher_headers)
    assert r_create.status_code == 200, f"Notice creation failed: {r_create.text}"
    notice = r_create.json()
    notice_id = notice["id"]
    status_str = str(notice["status"]).upper().replace(" ", "_")
    assert "PENDING" in status_str, f"Expected pending status, got: {notice['status']}"
    assert notice["creator_name"] == "Dr. B Kursheed"
    assert notice["department_name"] == "AIML"
    print(f"  [PASS] Notice #{notice_id} created with initial status: {notice['status']}")

    print("\n--- [3/6] Testing RBAC & Approval Queue Visibility ---")
    # Student cannot access approval queue
    r_queue_stud = client.get("/api/v1/announcements/approval-queue", headers=student_headers)
    assert r_queue_stud.status_code == 403, f"Student should be forbidden from approval queue: {r_queue_stud.status_code}"
    print("  [PASS] RBAC check passed: Student cannot access approval queue (403 Forbidden).")

    # Teacher sees their submitted notice
    r_queue_teach = client.get("/api/v1/announcements/approval-queue", headers=teacher_headers)
    assert r_queue_teach.status_code == 200
    teach_queue = r_queue_teach.json()
    assert any(a["id"] == notice_id for a in teach_queue), "Teacher should see own submitted notice"
    print(f"  [PASS] Teacher sees submitted notice in tracking queue (Count: {len(teach_queue)}).")

    # HoD sees notice in approval queue
    r_queue_hod = client.get("/api/v1/announcements/approval-queue", headers=hod_headers)
    assert r_queue_hod.status_code == 200
    hod_queue = r_queue_hod.json()
    assert any(a["id"] == notice_id for a in hod_queue), "HoD should see notice from AIML teacher"
    print(f"  [PASS] HoD sees pending notice in departmental queue (Count: {len(hod_queue)}).")

    print("\n--- [4/6] HoD Approves Notice with Remarks ---")
    approval_payload = {
        "remarks": "Verified and approved by AIML HoD for immediate campus publication."
    }
    r_approve = client.post(f"/api/v1/announcements/{notice_id}/approve", json=approval_payload, headers=hod_headers)
    assert r_approve.status_code == 200, f"Approval failed: {r_approve.text}"
    print("  [PASS] HoD approved notice successfully.")

    # Verify announcement status updated to Published
    r_check = client.get(f"/api/v1/announcements/{notice_id}", headers=teacher_headers)
    assert r_check.status_code == 200
    updated_notice = r_check.json()
    updated_status = str(updated_notice["status"]).upper().replace(" ", "_")
    assert "PUBLISHED" in updated_status, f"Expected PUBLISHED, got: {updated_notice['status']}"
    assert updated_notice["remarks"] == "Verified and approved by AIML HoD for immediate campus publication."
    print(f"  [PASS] Notice updated on backend to: {updated_notice['status']} with remark: '{updated_notice['remarks']}'")

    print("\n--- [5/6] Teacher Submits Notice and HoD Rejects with Reason ---")
    notice2_payload = {
        "title": "Weekend Extra Class Proposal",
        "description": "Proposal for Sunday 8 AM online session.",
        "category_id": 1,
        "priority": "Normal",
        "target_audience": "AIML Department"
    }
    r_create2 = client.post("/api/v1/announcements", json=notice2_payload, headers=teacher_headers)
    notice2_id = r_create2.json()["id"]

    rejection_payload = {
        "remarks": "Sunday classes are prohibited per college calendar. Please schedule on a weekday."
    }
    r_reject = client.post(f"/api/v1/announcements/{notice2_id}/reject", json=rejection_payload, headers=hod_headers)
    assert r_reject.status_code == 200, f"Rejection failed: {r_reject.text}"

    r_check2 = client.get(f"/api/v1/announcements/{notice2_id}", headers=teacher_headers)
    notice2_updated = r_check2.json()
    status2 = str(notice2_updated["status"]).upper().replace(" ", "_")
    assert "REJECTED" in status2, f"Expected REJECTED status, got: {notice2_updated['status']}"
    assert "Sunday classes are prohibited" in notice2_updated["remarks"]
    print(f"  [PASS] Notice #{notice2_id} rejected with status: {notice2_updated['status']} and remarks preserved.")

    print("\n--- [6/6] Testing WebSocket Live Realtime Endpoint ---")
    with client.websocket_connect("/api/v1/ws/live") as websocket:
        init_data = websocket.receive_json()
        assert init_data["event"] == "CONNECTED"
        websocket.send_text("ping")
        pong_data = websocket.receive_text()
        assert "pong" in pong_data
    print("  [PASS] WebSocket real-time live synchronization stream active and responsive.")

    print("\n==================================================================")
    print("  [SUCCESS] ALL APPROVAL WORKFLOW & REAL-TIME SYNC TESTS PASSED!  ")
    print("==================================================================")

if __name__ == "__main__":
    test_full_approval_workflow()
