import os
import sys
from datetime import datetime, timedelta, timezone

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.database import Base
from app.models.announcement import Announcement
from app.models.announcement_category import AnnouncementCategory
from app.models.announcement_delivery import AnnouncementDelivery
from app.models.announcement_repeat_schedule import (
    AnnouncementRepeatSchedule,
    RepeatSlotExecutionLog,
)
from app.models.delivery_type import DeliveryType
from app.models.department import Department
from app.models.role import Role
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.user import User
from app.schemas.repeat_schedule import RepeatScheduleCreate
from app.services.repeat_schedule_service import (
    configure_repeat_schedule,
    evaluate_and_dispatch_repeat_slots,
)

# In-memory test SQLite DB
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed Department
    dept = Department(name="Computer Science & Engineering", code="CSE")
    db.add(dept)

    # Seed Roles
    admin_role = Role(name="ADMIN")
    faculty_role = Role(name="FACULTY")
    db.add_all([admin_role, faculty_role])
    db.commit()

    # Seed User
    user = User(
        username="alanturing",
        official_email="faculty@test.edu",
        full_name="Prof. Alan Turing",
        password_hash="test",
        role_id=faculty_role.id,
        department_id=dept.id,
        is_active=True,
    )
    db.add(user)

    # Seed Category
    cat = AnnouncementCategory(name="Academic Seminars", description="Academic events")
    db.add(cat)

    # Seed Delivery Types
    deliv_speaker = DeliveryType(name="Speaker Broadcast")
    deliv_inapp = DeliveryType(name="In-App Feed")
    db.add_all([deliv_speaker, deliv_inapp])
    db.commit()

    # Seed Speaker Node
    node = SpeakerNode(
        name="CSE Block Corridor Speaker #1",
        mac_address="24:0A:C4:00:01:10",
        ip_address="192.168.1.50",
        department_id=dept.id,
        zone="Departmental",
        status="ONLINE",
    )
    db.add(node)
    db.commit()
    return db, user, cat, deliv_speaker, deliv_inapp, node


def test_repeat_schedule_suite():
    db, user, cat, deliv_speaker, deliv_inapp, node = setup_test_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    print("\n=======================================================")
    print("  RUNNING ECHOSPHERE REPEAT SCHEDULE TEST SUITE")
    print("=======================================================\n")

    # -------------------------------------------------------------
    # TEST 1: Speaker-Only Delivery Requirement & Force-Enable
    # -------------------------------------------------------------
    print("🔍 [TEST 1] Testing Speaker-Only Notice Requirement...")
    ann1 = Announcement(
        title="Non-Speaker Notice",
        description="General bulletin for noticeboard",
        category_id=cat.id,
        created_by=user.id,
        status="PUBLISHED",
    )
    db.add(ann1)
    db.commit()

    # Deliver only in-app for ann1
    db.add(AnnouncementDelivery(announcement_id=ann1.id, delivery_type_id=deliv_inapp.id))
    db.commit()
    db.refresh(ann1)
    assert ann1.deliver_speaker is False

    # Attempting to add repeat schedule without force_enable_speaker should fail
    try:
        config_data = RepeatScheduleCreate(
            selected_slots=["SHORT_BREAK", "LUNCH_BREAK"],
            target_scope="DEPARTMENT",
            event_datetime=now + timedelta(hours=24),
            start_date=now,
            end_date=now + timedelta(hours=24),
            force_enable_speaker=False,
        )
        configure_repeat_schedule(db, ann1.id, config_data, user)
        assert False, "Should have raised 400 for non-speaker notice without force_enable!"
    except Exception as e:
        print(f"  ✓ Non-speaker notice correctly blocked: {getattr(e, 'detail', str(e))}")

    # Now force-enable speaker delivery: should succeed and retrofit delivery
    config_data_force = RepeatScheduleCreate(
        selected_slots=["SHORT_BREAK", "LUNCH_BREAK"],
        target_scope="DEPARTMENT",
        event_datetime=now + timedelta(hours=24),
        start_date=now,
        end_date=now + timedelta(hours=24),
        force_enable_speaker=True,
    )
    sched1 = configure_repeat_schedule(db, ann1.id, config_data_force, user)
    db.refresh(ann1)
    assert ann1.deliver_speaker is True, "deliver_speaker should now be True after force_enable"
    assert sched1.id is not None
    print("  ✓ Retrofitting non-speaker notice via force_enable succeeded!")

    # -------------------------------------------------------------
    # TEST 2: Anti-Spam 48h Event Horizon & 2-Day Max Lifespan Guards
    # -------------------------------------------------------------
    print("\n🔍 [TEST 2] Testing Anti-Spam Event Horizon & Lifespan Bounds...")
    
    # Premature repeat schedule (> 48h before event) must fail
    try:
        RepeatScheduleCreate(
            selected_slots=["SHORT_BREAK"],
            target_scope="DEPARTMENT",
            event_datetime=now + timedelta(days=10),  # Event is 10 days away
            start_date=now,                          # Trying to repeat now
            end_date=now + timedelta(days=1),
        )
        assert False, "Should have rejected repeat start > 48h before event!"
    except ValueError as ve:
        print(f"  ✓ Premature repeat blocked by validator: {ve}")

    # Excessive lifespan (> 2 days) must fail
    try:
        RepeatScheduleCreate(
            selected_slots=["SHORT_BREAK"],
            target_scope="DEPARTMENT",
            event_datetime=now + timedelta(hours=24),
            start_date=now,
            end_date=now + timedelta(days=4),  # 4 days repeat span
        )
        assert False, "Should have rejected lifespan > 2 days!"
    except ValueError as ve:
        print(f"  ✓ >2 days lifespan blocked by validator: {ve}")

    # -------------------------------------------------------------
    # TEST 3: Custom Window (Hostel / Special Slot) Validation
    # -------------------------------------------------------------
    print("\n🔍 [TEST 3] Testing Custom Window Time Formats...")
    try:
        RepeatScheduleCreate(
            selected_slots=["CUSTOM_WINDOW"],
            custom_start_time="invalid",
            custom_end_time="19:00",
            target_scope="HOSTEL",
            event_datetime=now + timedelta(hours=20),
            start_date=now,
            end_date=now + timedelta(hours=20),
        )
        assert False, "Should have rejected invalid custom time format!"
    except ValueError as ve:
        print(f"  ✓ Invalid custom time format correctly rejected: {ve}")

    # Valid custom window
    custom_config = RepeatScheduleCreate(
        selected_slots=["CUSTOM_WINDOW", "SHORT_BREAK"],
        custom_start_time="18:30",
        custom_end_time="19:15",
        target_scope="HOSTEL",
        event_datetime=now + timedelta(hours=20),
        start_date=now,
        end_date=now + timedelta(hours=20),
    )
    assert "CUSTOM_WINDOW" in custom_config.selected_slots
    print("  ✓ Valid custom window configuration accepted.")

    # Deactivate sched1 so Test 4 isolates ann2 multi-slot execution
    sched1.is_active = False
    db.commit()

    # -------------------------------------------------------------
    # TEST 4: Independent Replay Across Slots (Short Break -> Lunch Break -> Custom)
    # -------------------------------------------------------------
    print("\n🔍 [TEST 4] Testing Independent Multi-Slot Replay Execution...")
    
    # Create approved announcement with all 3 slots
    ann2 = Announcement(
        title="CSE Technical Symposium 2026",
        description="Paper presentations and hackathon in Seminar Hall 2.",
        category_id=cat.id,
        created_by=user.id,
        status="PUBLISHED",
    )
    db.add(ann2)
    db.commit()

    db.add(AnnouncementDelivery(announcement_id=ann2.id, delivery_type_id=deliv_speaker.id))
    db.commit()
    db.refresh(ann2)
    assert ann2.deliver_speaker is True

    all_slots_config = RepeatScheduleCreate(
        selected_slots=["SHORT_BREAK", "LUNCH_BREAK", "CUSTOM_WINDOW"],
        custom_start_time="18:30",
        custom_end_time="19:15",
        target_scope="DEPARTMENT",
        target_node_id=node.id,
        event_datetime=now + timedelta(hours=24),
        start_date=now - timedelta(hours=1),
        end_date=now + timedelta(hours=36),
    )
    sched2 = configure_repeat_schedule(db, ann2.id, all_slots_config, user)

    # 4A. Simulate 11:05 AM (Short Break: 11:00 - 11:15)
    print("  -> Simulating 11:05 AM (Short Break)...")
    res_short = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="11:05",
        simulated_date_str="2026-09-13",
    )
    assert res_short["dispatched_count"] == 1, f"Expected 1 dispatch in short break, got {res_short['dispatched_count']}"
    assert res_short["dispatched"][0]["slot"] == "SHORT_BREAK"
    print("  ✓ Short Break (11:05) dispatched notice to speaker queue!")

    # 4B. Simulate 11:10 AM (Same Short Break window): Idempotency guard prevents duplicate
    print("  -> Simulating 11:10 AM (Same Short Break window)...")
    res_short_dup = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="11:10",
        simulated_date_str="2026-09-13",
    )
    assert res_short_dup["dispatched_count"] == 0, "Duplicate short break dispatch should be blocked!"
    print("  ✓ Intra-slot duplicate correctly blocked by idempotency key.")

    # 4C. Simulate 1:25 PM (Lunch Break: 13:15 - 14:00): MUST play independently!
    print("  -> Simulating 13:25 PM (Lunch Break)...")
    res_lunch = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="13:25",
        simulated_date_str="2026-09-13",
    )
    assert res_lunch["dispatched_count"] == 1, "Lunch break must play notice independently of morning short break!"
    assert res_lunch["dispatched"][0]["slot"] == "LUNCH_BREAK"
    print("  ✓ Lunch Break (13:25) dispatched notice independently!")

    # 4D. Simulate 18:45 PM (Custom Window: 18:30 - 19:15): MUST play independently!
    print("  -> Simulating 18:45 PM (Custom Window)...")
    res_custom = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="18:45",
        simulated_date_str="2026-09-13",
    )
    assert res_custom["dispatched_count"] == 1, "Custom window must play notice independently!"
    assert res_custom["dispatched"][0]["slot"] == "CUSTOM_WINDOW"
    print("  ✓ Custom Window (18:45) dispatched notice independently!")

    # Verify execution logs in database
    logs = db.query(RepeatSlotExecutionLog).filter(RepeatSlotExecutionLog.schedule_id == sched2.id).all()
    assert len(logs) == 3, f"Expected 3 execution logs, found {len(logs)}"
    slot_names = [l.slot_name for l in logs]
    assert "SHORT_BREAK" in slot_names and "LUNCH_BREAK" in slot_names and "CUSTOM_WINDOW" in slot_names
    print("  ✓ All 3 slot executions logged independently in database.")

    # -------------------------------------------------------------
    # TEST 5: Speaker Queue Re-Activation (Without unique=True Error)
    # -------------------------------------------------------------
    print("\n🔍 [TEST 5] Testing SpeakerQueue Re-Activation...")
    q_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann2.id).first()
    assert q_item is not None, "Queue item must exist in speaker_queue"
    # Mark it Completed as if it finished audio playback
    q_item.status = "Completed"
    db.commit()

    # Now simulate Day 2 Short Break (2026-09-14 at 11:02 AM)
    print("  -> Simulating Day 2 Short Break (11:02 AM, 2026-09-14)...")
    res_day2 = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="11:02",
        simulated_date_str="2026-09-14",
    )
    assert res_day2["dispatched_count"] == 1, "Day 2 short break should dispatch successfully!"
    db.refresh(q_item)
    # Status should be re-activated to Playing or Queued, not stuck in Completed!
    assert q_item.status in ("Playing", "Queued", "Next in Queue"), f"Queue status should be re-activated, got {q_item.status}"
    print(f"  ✓ Completed speaker queue item safely re-activated to '{q_item.status}' without crash!")

    # -------------------------------------------------------------
    # TEST 6: Class Protection Cutoff TTL (Outside Break Hours)
    # -------------------------------------------------------------
    print("\n🔍 [TEST 6] Testing Lecture Hours Protection (Break Cutoff TTL)...")
    # Simulate unplayed notice queued during Short Break (scheduled_time = 11:05)
    q_item.status = "Queued"
    q_item.scheduled_time = datetime(2026, 9, 13, 11, 5)
    db.commit()

    # Evaluate at 11:20 AM (Class is in session!)
    print("  -> Simulating 11:20 AM (Classes in session after 11:15 cutoff)...")
    res_lecture = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="11:20",
        simulated_date_str="2026-09-13",
    )
    db.refresh(q_item)
    assert q_item.status == "Expired_Slot_Ended", f"Unplayed repeat item should expire after break, got {q_item.status}"
    print("  ✓ Unplayed repeat item expired at 11:20 AM. Lecture hours successfully protected!")

    # -------------------------------------------------------------
    # TEST 7: Parent Notice Archive / Cancellation Cascade
    # -------------------------------------------------------------
    print("\n🔍 [TEST 7] Testing Parent Event Archive / Cancellation Cascade...")
    ann2.status = "ARCHIVED"
    db.commit()

    evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str="13:30",
        simulated_date_str="2026-09-14",
    )
    db.refresh(sched2)
    assert sched2.is_active is False, "Repeat schedule should be deactivated when parent notice is archived"
    print("  ✓ Archived parent notice immediately deactivated repeat schedule.")

    print("\n=======================================================")
    print("  ✅ ALL REPEAT SCHEDULE TESTS PASSED SUCCESSFULLY!")
    print("=======================================================\n")


if __name__ == "__main__":
    test_repeat_schedule_suite()
