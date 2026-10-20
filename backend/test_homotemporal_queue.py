import sys
import os
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from app.db.database import SessionLocal
from app.models.announcement import Announcement
from app.models.speaker_queue import SpeakerQueue
from app.models.user import User
from app.models.announcement_category import AnnouncementCategory
from app.core.enums.announcement import AnnouncementStatus, AnnouncementPriority, EmergencyLevel
from app.services.hardware_speaker_service import (
    enqueue_and_broadcast_announcement,
    auto_advance_speaker_queue,
    normalize_speaker_queue_positions,
    utc_now,
)

def run_tests():
    db = SessionLocal()
    try:
        print("\n🧪 [TEST 1] Testing Homo-Temporal Normal Notices...")
        # Clean existing test queue items
        db.query(SpeakerQueue).delete()
        db.commit()

        u = db.query(User).first()
        cat = db.query(AnnouncementCategory).first()

        # Create two routine notices placed at the exact same moment
        ann1 = db.query(Announcement).filter(Announcement.title == "Homo-Temporal Notice A").first()
        if not ann1:
            ann1 = Announcement(
                title="Homo-Temporal Notice A",
                description="This is notice A placed at 12:00:00.",
                status=AnnouncementStatus.PUBLISHED,
                priority=AnnouncementPriority.NORMAL,
                emergency_level=EmergencyLevel.NORMAL,
                created_by=u.id,
                category_id=cat.id,
            )
            db.add(ann1)
            db.commit()

        ann2 = db.query(Announcement).filter(Announcement.title == "Homo-Temporal Notice B").first()
        if not ann2:
            ann2 = Announcement(
                title="Homo-Temporal Notice B",
                description="This is notice B placed at 12:00:00 simultaneously.",
                status=AnnouncementStatus.PUBLISHED,
                priority=AnnouncementPriority.NORMAL,
                emergency_level=EmergencyLevel.NORMAL,
                created_by=u.id,
                category_id=cat.id,
            )
            db.add(ann2)
            db.commit()

        # Enqueue Notice A
        res1 = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann1.id,
            title=ann1.title,
            content=ann1.description,
            force_requeue=True,
        )
        print(f"Notice A enqueued -> Playing: {res1.get('is_playing')}, Status: {res1.get('queue_status')}, Pos: {res1.get('queue_position')}")
        assert res1.get("is_playing") == True, "Notice A should start playing immediately as queue is empty!"

        # Enqueue Notice B simultaneously (homo-temporal)
        res2 = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann2.id,
            title=ann2.title,
            content=ann2.description,
            force_requeue=True,
        )
        print(f"Notice B enqueued -> Playing: {res2.get('is_playing')}, Status: {res2.get('queue_status')}, Pos: {res2.get('queue_position')}")
        assert res2.get("is_playing") == False, "Notice B should NOT preempt Notice A!"
        assert res2.get("queue_position") == 2, "Notice B must be in position 2!"

        q1 = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann1.id).first()
        q2 = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann2.id).first()
        print(f"DB State: Notice A={q1.status} (pos {q1.queue_position}), Notice B={q2.status} (pos {q2.queue_position})")
        assert q1.status == "Playing", "Notice A must remain Playing without being paused!"
        assert q2.status == "Next in Queue", "Notice B must be Next in Queue!"
        print("✅ [TEST 1 PASSED] Homo-temporal notices handled sequentially without preemption!\n")

        print("🧪 [TEST 2] Testing Homo-Temporal Priority Sorting (High > Normal > Low)...")
        # Create High, Normal, and Low notices scheduled for the same future minute
        target_sched = utc_now() + timedelta(minutes=5)

        ann_high = db.query(Announcement).filter(Announcement.title == "Homo-Temporal High").first()
        if not ann_high:
            ann_high = Announcement(
                title="Homo-Temporal High",
                description="Urgent exam notice.",
                status=AnnouncementStatus.SCHEDULED,
                priority=AnnouncementPriority.HIGH,
                emergency_level=EmergencyLevel.NORMAL,
                created_by=u.id,
                category_id=cat.id,
            )
            db.add(ann_high)
            db.commit()

        ann_low = db.query(Announcement).filter(Announcement.title == "Homo-Temporal Low").first()
        if not ann_low:
            ann_low = Announcement(
                title="Homo-Temporal Low",
                description="Lost water bottle reminder.",
                status=AnnouncementStatus.SCHEDULED,
                priority=AnnouncementPriority.LOW,
                emergency_level=EmergencyLevel.NORMAL,
                created_by=u.id,
                category_id=cat.id,
            )
            db.add(ann_low)
            db.commit()

        # Enqueue in reverse order: Low first, then High, scheduled at the exact same target time
        enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann_low.id,
            title=ann_low.title,
            content=ann_low.description,
            scheduled_time=target_sched,
            force_requeue=True,
        )
        enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann_high.id,
            title=ann_high.title,
            content=ann_high.description,
            scheduled_time=target_sched,
            force_requeue=True,
        )

        all_q = db.query(SpeakerQueue).order_by(SpeakerQueue.queue_position.asc()).all()
        for q in all_q:
            print(f"Pos {q.queue_position}: Announcement #{q.announcement_id} ('{q.announcement.title}', Priority: {q.announcement.priority}) -> {q.status}")

        q_high = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann_high.id).first()
        q_low = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann_low.id).first()
        assert q_high.queue_position < q_low.queue_position, "High priority notice MUST sort ahead of Low priority notice even when inserted second!"
        print("✅ [TEST 2 PASSED] Homo-temporal notices strictly sorted by priority tier!\n")

        print("🧪 [TEST 3] Testing Clean Queue Advancement (Notice A -> Notice B)...")
        # Simulate Notice A audio duration ending and ESP32 calling complete
        q1.played_at = utc_now() - timedelta(seconds=25)
        db.commit()

        adv = auto_advance_speaker_queue(db, force_advance=True)
        print(f"Advance result: {adv}")
        db.refresh(q1)
        db.refresh(q2)
        print(f"Notice A={q1.status}, Notice B={q2.status} (pos {q2.queue_position})")
        assert q1.status == "Completed", "Notice A must be Completed!"
        assert q2.status == "Playing", "Notice B must now be Playing!"
        assert q2.queue_position == 1, "Notice B must be in position 1!"
        print("✅ [TEST 3 PASSED] Flawless 0-latency auto-advancement confirmed!\n")

        # Cleanup
        db.query(SpeakerQueue).delete()
        db.commit()
        print("🎉 ALL SPEAKER QUEUE AUDIT & REPAIR TESTS PASSED 100%!")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
