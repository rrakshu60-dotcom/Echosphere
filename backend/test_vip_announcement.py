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
from app.models.announcement_vip_protocol import AnnouncementVipProtocol
from app.models.delivery_type import DeliveryType
from app.models.department import Department
from app.models.role import Role
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.user import User
from app.services.chime_service import generate_chime_pcm, resolve_contextual_chime
from app.services.vip_announcement_service import (
    analyze_and_extract_vip,
    dispatch_vip_arrival_fanfare,
    evaluate_and_dispatch_vip_seating_calls,
    filter_suppressed_exam_nodes,
    is_potential_vip_notice,
)

# In-memory test SQLite DB
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed Departments
    dept_cse = Department(name="Computer Science & Engineering", code="CSE")
    dept_me = Department(name="Mechanical Engineering", code="ME")
    db.add_all([dept_cse, dept_me])
    db.commit()

    # Seed Role & User
    admin_role = Role(name="ADMIN")
    db.add(admin_role)
    db.commit()

    user = User(
        username="protocol_officer",
        official_email="protocol@test.edu",
        full_name="Col. Ramesh Sharma",
        password_hash="test",
        role_id=admin_role.id,
        department_id=dept_cse.id,
        is_active=True,
    )
    db.add(user)

    # Seed Category
    cat_symposium = AnnouncementCategory(name="Symposiums & Conferences", description="VIP Events")
    cat_exam = AnnouncementCategory(name="Examinations", description="Internal Tests")
    db.add_all([cat_symposium, cat_exam])

    # Seed Delivery Types
    deliv_speaker = DeliveryType(name="Speaker Broadcast")
    db.add(deliv_speaker)
    db.commit()

    # Seed Speaker Nodes
    node_portico = SpeakerNode(
        name="Main Portico & Entrance Horn",
        mac_address="24:0A:C4:00:01:20",
        department_id=None,
        zone="Portico",
        status="ONLINE",
    )
    node_audi = SpeakerNode(
        name="Central Auditorium PA System",
        mac_address="24:0A:C4:00:01:21",
        department_id=None,
        zone="Auditorium",
        status="ONLINE",
    )
    node_me_exam = SpeakerNode(
        name="Mechanical Block 2nd Floor Exam Corridor",
        mac_address="24:0A:C4:00:01:22",
        department_id=dept_me.id,
        zone="Academic Corridor",
        status="ONLINE",
    )
    db.add_all([node_portico, node_audi, node_me_exam])
    db.commit()

    return db, user, cat_symposium, cat_exam, deliv_speaker, node_portico, node_audi, node_me_exam


def test_vip_protocol_suite():
    db, user, cat_symp, cat_exam, deliv_speaker, node_portico, node_audi, node_me = setup_test_db()
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    print("\n=======================================================")
    print("  RUNNING ECHOSPHERE AI VIP DIGNITARY TEST SUITE")
    print("=======================================================\n")

    # -------------------------------------------------------------
    # TEST 1: Pre-Filter & False-Alarm Shield
    # -------------------------------------------------------------
    print("[TEST 1] Testing Pre-Filter & False-Alarm Shield...")
    real_vip_text = "National Space Science Symposium: Dr. K. Sivan, Former Chairman of ISRO, will be the Chief Guest."
    false_alarm_1 = "Please collect your guest pass coupon from the hostel mess office."
    false_alarm_2 = "Guest room booking charges for alumni meet."
    
    assert is_potential_vip_notice(real_vip_text) is True, "Real VIP text should pass filter"
    assert is_potential_vip_notice(false_alarm_1) is False, "False alarm 1 should be rejected"
    assert is_potential_vip_notice(false_alarm_2) is False, "False alarm 2 should be rejected"
    print("  ✓ False alarms ('guest pass', 'guest room') successfully blocked.")

    # -------------------------------------------------------------
    # TEST 2: Ceremonial Fanfare Chime Synthesis
    # -------------------------------------------------------------
    print("\n[TEST 2] Testing Ceremonial Chime Synthesis & Auto-Selection...")
    # Contextual chime auto-selection
    resolved = resolve_contextual_chime(
        priority="NORMAL",
        category="General",
        title="Inauguration by Chief Guest",
        content="Honorable dignitary visiting campus",
    )
    assert resolved == "ceremonial", f"Expected 'ceremonial' chime, got '{resolved}'"
    print("  ✓ Chime selector automatically chose 'ceremonial' fanfare for VIP notice.")

    # Generate 16-bit PCM bytes
    pcm_bytes = generate_chime_pcm("ceremonial", sample_rate=24000)
    assert len(pcm_bytes) > 2000, "Ceremonial chime PCM must contain valid audio samples"
    print(f"  ✓ Ceremonial 4-tone harmonic fanfare synthesized ({len(pcm_bytes)} bytes PCM).")

    # -------------------------------------------------------------
    # TEST 3: AI Entity Extraction & Radio Broadcast Scripting
    # -------------------------------------------------------------
    print("\n[TEST 3] Testing AI Entity Extraction & Radio Script Generation...")
    ann_vip = Announcement(
        title="National Space Science Symposium 2026",
        description=(
            "The Department of CSE cordially invites all students to the National Space Science Symposium. "
            "Dr. K. Sivan, Former Chairman of ISRO, will be the Chief Guest and deliver the keynote address. "
            "Venue: Central Auditorium. Inauguration time: 10:30 AM."
        ),
        category_id=cat_symp.id,
        created_by=user.id,
        status="PUBLISHED",
        scheduled_at=now + timedelta(hours=2),
    )
    db.add(ann_vip)
    db.commit()

    db.add(AnnouncementDelivery(announcement_id=ann_vip.id, delivery_type_id=deliv_speaker.id))
    db.commit()

    protocol = analyze_and_extract_vip(db, ann_vip.id)
    assert protocol is not None, "VIP protocol should be detected and extracted"
    assert "Sivan" in protocol.guest_name or "Dr." in protocol.guest_name, f"Unexpected guest name: {protocol.guest_name}"
    assert "Auditorium" in protocol.venue, f"Unexpected venue: {protocol.venue}"
    assert len(protocol.spoken_script) > 40, "Spoken radio script should be generated"
    assert "Attention" in protocol.spoken_script, "Radio script should follow formal institutional PA conventions"
    print(f"  ✓ Extracted Guest: {protocol.guest_name} ({protocol.guest_title})")
    print(f"  ✓ Venue: {protocol.venue}")
    print(f"  ✓ Radio PA Script: '{protocol.spoken_script[:85]}...'")

    # -------------------------------------------------------------
    # TEST 4: Acoustic Exam Hall Shield (Noise Suppression)
    # -------------------------------------------------------------
    print("\n[TEST 4] Testing Acoustic Exam Hall Suppression...")
    # Add active exam in ME department
    ann_exam = Announcement(
        title="Mechanical Dept Internal Assessment Exam 2",
        description="Semester examination in progress across ME classrooms.",
        category_id=cat_exam.id,
        created_by=user.id,
        status="PUBLISHED",
        scheduled_at=now,
    )
    db.add(ann_exam)
    db.commit()

    all_nodes = [node_portico, node_audi, node_me]
    safe_nodes, muted_nodes = filter_suppressed_exam_nodes(db, all_nodes)
    
    assert node_portico in safe_nodes, "Portico should remain active"
    assert node_audi in safe_nodes, "Auditorium should remain active"
    assert node_me not in safe_nodes, "ME Exam Corridor must be muted during tests!"
    assert node_me.name in muted_nodes
    print(f"  ✓ Muted Exam Block Speaker: '{node_me.name}'")
    print(f"  ✓ Active Broadcast Speakers: {[n.name for n in safe_nodes]}")

    # -------------------------------------------------------------
    # TEST 5: Speaker Queue Fast-Track (Priority 1 Insertion)
    # -------------------------------------------------------------
    print("\n[TEST 5] Testing Speaker Queue Fast-Track Preemption...")
    # Create routine announcement currently playing
    ann_routine = Announcement(
        title="Sports Club Badminton Auditions",
        description="Trials today at indoor court",
        category_id=cat_symp.id,
        created_by=user.id,
        status="PUBLISHED",
    )
    db.add(ann_routine)
    db.commit()

    # Queue standard items
    q_playing = SpeakerQueue(
        announcement_id=ann_routine.id,
        queue_position=1,
        status="Playing",
        scheduled_time=now,
        played_at=now,
        duration_seconds=30,
    )
    db.add(q_playing)
    db.commit()

    # Trigger live arrival fanfare for VIP
    print("  -> Triggering On-Demand Chief Guest Arrival Fanfare...")
    fanfare_res = dispatch_vip_arrival_fanfare(
        db=db,
        announcement_id=ann_vip.id,
        current_user=user,
        target_zone="Portico-Auditorium",
    )

    db.refresh(protocol)
    assert protocol.is_arrival_announced is True
    vip_queue_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann_vip.id).first()
    assert vip_queue_item is not None
    # Must be positioned at #2 (Next in Queue right after currently playing)
    assert vip_queue_item.queue_position == 2, f"VIP notice must be fast-tracked to Position #2, got {vip_queue_item.queue_position}"
    assert vip_queue_item.status == "Next in Queue"
    print(f"  ✓ VIP Notice slotted at Queue Position #{vip_queue_item.queue_position} ('{vip_queue_item.status}')")

    # -------------------------------------------------------------
    # TEST 6: T-15 Assembly & Seating Call Trigger
    # -------------------------------------------------------------
    print("\n[TEST 6] Testing T-15 Assembly & Seating Call Milestone...")
    protocol.is_seating_announced = False
    protocol.event_datetime = now + timedelta(minutes=14)  # 14 minutes away (T-15 window)
    db.commit()

    seating_calls = evaluate_and_dispatch_vip_seating_calls(db=db, simulated_now=now)
    assert len(seating_calls) == 1, "Seating call should be dispatched at T-15"
    assert seating_calls[0]["announcement_id"] == ann_vip.id
    db.refresh(protocol)
    assert protocol.is_seating_announced is True
    print("  ✓ T-15 Assembly Seating Call successfully enqueued to speakers!")

    print("\n=======================================================")
    print("  ✅ ALL AI VIP DIGNITARY PROTOCOL TESTS PASSED (100%)!")
    print("=======================================================\n")


if __name__ == "__main__":
    test_vip_protocol_suite()
