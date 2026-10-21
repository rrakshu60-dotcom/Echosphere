import os
import unittest
from datetime import datetime, timezone, timedelta
from app.db.database import SessionLocal
from app.models.user import User
from app.models.announcement import Announcement
from app.models.speaker_queue import SpeakerQueue
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
from app.services.auth_service import authenticate_user
from app.services.hardware_speaker_service import (
    enqueue_and_broadcast_announcement,
    auto_advance_speaker_queue,
    restore_paused_queue_items,
    utc_now,
)

def run_tests():
    print("==================================================")
    print("  RUNNING QUEUE LATENCY & REPEAT RESUMPTION TESTS ")
    print("==================================================")

    with SessionLocal() as db:
        # Test 1: Case-insensitive login with ESDEV01
        print("\n[Test 1] Testing case-insensitive admin login with 'ESDEV01'...")
        token, user = authenticate_user(db, "ESDEV01", os.environ.get("ES_PASSWORD_ESDEV01", ""))
        assert user is not None, "User should not be None"
        assert user.employee_id.upper() == "ESDEV01", "Employee ID match"
        print(f"✅ Login SUCCESS: Logged in as '{user.full_name}' ({user.role.name})")

        # Clean test queues
        db.query(SpeakerQueue).delete()
        db.commit()

        ann1 = db.query(Announcement).filter(Announcement.id == 1).first()
        ann2 = db.query(Announcement).filter(Announcement.id == 4).first()

        now = utc_now()

        # Configure Repeat Schedule for Ann 1
        sched1 = db.query(AnnouncementRepeatSchedule).filter(AnnouncementRepeatSchedule.announcement_id == ann1.id).first()
        if not sched1:
            sched1 = AnnouncementRepeatSchedule(
                announcement_id=ann1.id,
                repeat_mode="INTERVAL",
                interval_minutes=15,
                max_repeats=5,
                event_datetime=now,
                start_date=now - timedelta(days=1),
                end_date=now + timedelta(days=1),
                is_active=True,
                total_played_count=0,
            )
            db.add(sched1)
        else:
            sched1.is_active = True
            sched1.repeat_mode = "INTERVAL"
            sched1.max_repeats = 5
            sched1.total_played_count = 0
        db.commit()

        # Enqueue Ann 1: It should start Playing
        print(f"\n[Test 2] Enqueuing Repeat Notice #{ann1.id} ('{ann1.title}')...")
        res1 = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann1.id,
            title=ann1.title,
            content=ann1.description,
            is_emergency=False,
        )
        q1 = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann1.id).first()
        assert q1.status == "Playing", f"Ann 1 should be Playing, got: {q1.status}"
        print(f"✅ Ann #{ann1.id} is actively Playing in speaker queue.")

        # Test 3: Push a newly broadcasted Notice Ann 2 while Ann 1 is playing
        print(f"\n[Test 3] Pushing newly broadcasted Notice #{ann2.id} while Ann 1 is playing...")
        res2 = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=ann2.id,
            title=ann2.title,
            content=ann2.description,
            is_emergency=False,
        )
        db.refresh(q1)
        q2 = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann2.id).first()
        db.refresh(sched1)

        print(f"  -> Notice 1 status: {q1.status} (Repeat Schedule is_active: {sched1.is_active})")
        print(f"  -> Notice 2 status: {q2.status}")
        assert q1.status == "Paused", f"Notice 1 should be Paused, got: {q1.status}"
        assert sched1.is_active == True, f"Repeat schedule for Notice 1 MUST remain True, got: {sched1.is_active}"
        assert q2.status == "Playing", f"Notice 2 should be Playing, got: {q2.status}"
        print("✅ PREEMPTION SUCCESSFUL: Notice 2 plays immediately, Notice 1 paused with schedule intact!")

        # Test 4: Notice 2 completes audio playback -> Notice 1 should resume for remainder of window
        print("\n[Test 4] Notice 2 completes playback. Checking resumption of Repeat Notice 1...")
        # Simulate notice 2 duration completion
        setattr(q2, "status", "Completed")
        db.commit()

        # Call auto_advance_speaker_queue
        adv = auto_advance_speaker_queue(db, force_advance=True)
        db.refresh(q1)
        db.refresh(sched1)

        print(f"  -> Adv result: {adv}")
        print(f"  -> Notice 1 status: {q1.status}")
        print(f"  -> Notice 1 scheduled_time: {q1.scheduled_time}")
        print(f"  -> Repeat schedule is_active: {sched1.is_active}")

        assert q1.status == "Playing", f"Notice 1 should have resumed to Playing, got: {q1.status}"
        assert sched1.is_active == True, "Schedule must still be active for whole window"
        print("✅ RESUMPTION SUCCESSFUL: Preempted repeat broadcast resumed immediately for scheduled window!")

        # Test 5: Back-to-back notices with close schedules (e.g. 45 seconds apart)
        print("\n[Test 5] Testing close schedule latency (< 90 seconds)...")
        # Complete notice 1
        setattr(q1, "status", "Completed")
        # Put notice 2 in queue scheduled 45 seconds in future
        setattr(q2, "status", "Queued")
        setattr(q2, "scheduled_time", utc_now() + timedelta(seconds=45))
        setattr(q2, "played_at", None)
        db.commit()

        adv_close = auto_advance_speaker_queue(db, force_advance=False)
        db.refresh(q2)
        print(f"  -> Notice 2 status after advance: {q2.status}")
        assert q2.status == "Playing", f"Close-schedule notice should advance immediately (< 90s), got: {q2.status}"
        print("✅ ZERO-LATENCY CLOSE SCHEDULES SUCCESSFUL: Advanced immediately without 1-2 min delay!")

        print("\n==================================================")
        print("     ALL LATENCY & REPEAT UNIT TESTS PASSED!      ")
        print("==================================================")

if __name__ == "__main__":
    run_tests()
