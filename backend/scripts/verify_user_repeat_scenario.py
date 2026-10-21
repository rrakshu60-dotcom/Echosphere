import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from test_repeat_schedule import setup_test_db
from app.models.announcement import Announcement
from app.models.speaker_queue import SpeakerQueue
from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
from app.models.delivery_type import DeliveryType
from app.models.announcement_delivery import AnnouncementDelivery
from app.core.enums.announcement import AnnouncementPriority, EmergencyLevel, AnnouncementStatus
from app.schemas.repeat_schedule import RepeatScheduleCreate
from app.services.repeat_schedule_service import configure_repeat_schedule, get_current_ist_datetime
from app.services.hardware_speaker_service import auto_advance_speaker_queue, _is_future_time

def test_exact_user_scenario():
    db, user, cat, deliv_speaker, deliv_inapp, node = setup_test_db()
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    ist_now = get_current_ist_datetime()

    print("\n=======================================================")
    print("  TESTING USER SCENARIO: Publish Now + Future Repeat")
    print("=======================================================\n")

    # 1. User configures a repeat schedule for 45 minutes in the future
    future_start = (ist_now + timedelta(minutes=45)).strftime("%H:%M")
    future_end = (ist_now + timedelta(minutes=75)).strftime("%H:%M")

    ann = Announcement(
        title="ML Exam Schedule Notice",
        description="ML Exam is postponed to next Monday as per notification.",
        priority=AnnouncementPriority.NORMAL,
        emergency_level=EmergencyLevel.NORMAL,
        created_by=user.id,
        category_id=cat.id,
        status=AnnouncementStatus.PUBLISHED,
    )
    db.add(ann)
    db.commit()
    db.add(AnnouncementDelivery(announcement_id=ann.id, delivery_type_id=deliv_speaker.id))
    db.commit()

    # User selects "Publish Now" (play_on_publish=True) + Custom Window in future
    sched_payload = RepeatScheduleCreate(
        repeat_mode="BREAK_SLOTS",
        selected_slots=["CUSTOM_WINDOW"],
        custom_start_time=future_start,
        custom_end_time=future_end,
        play_on_publish=True,
        max_repeats=3,
        start_date=now_utc - timedelta(hours=1),
        end_date=now_utc + timedelta(hours=24),
    )
    sched = configure_repeat_schedule(db, ann.id, sched_payload, current_user=user)
    db.refresh(sched)

    # Verify initial queue item was enqueued immediately for Publish Now
    q_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == ann.id).first()
    assert q_item is not None
    assert q_item.status in ("Playing", "Queued")
    print(f"  ✓ Initial notice enqueued for immediate publish (status: {q_item.status})")

    # Ensure it is currently playing
    q_item.status = "Playing"
    q_item.played_at = now_utc
    db.commit()

    # 2. Hardware completes playback of Round 1
    # Hardware calls complete action (simulated via update_queue_action logic)
    print("  -> Notice finishes playing Round 1. Hardware signals 'complete'...")
    from app.services.repeat_schedule_service import get_next_slot_datetime, _utc_to_ist_naive

    sched.total_played_count += 1
    sched.last_repeat_at = now_utc
    next_cand, cand_slot = get_next_slot_datetime(sched, _utc_to_ist_naive(now_utc), db)
    assert next_cand is not None, "Next slot datetime must be calculated!"
    print(f"  ✓ Next repeat calculated at: {next_cand} (target slot: {cand_slot})")

    # Set queue status to Queued with future scheduled_time
    q_item.status = "Queued"
    q_item.scheduled_time = next_cand
    q_item.played_at = None
    sched.next_repeat_at = next_cand
    db.commit()
    db.refresh(q_item)

    # 3. auto_advance_speaker_queue is triggered with force_advance=True
    print("  -> Triggering auto_advance_speaker_queue(force_advance=True)...")
    adv_res = auto_advance_speaker_queue(db, force_advance=True)

    # CRITICAL CHECK: Queue MUST NOT advance! It must stay idle!
    db.refresh(q_item)
    assert adv_res is None, f"Expected None (queue idle), but got {adv_res}!"
    assert q_item.status == "Queued", f"Expected 'Queued', but got {q_item.status}!"
    assert _is_future_time(q_item.scheduled_time, now_utc) == True, "scheduled_time must be in the future!"
    print("  ✓ SUCCESS: Queue remained IDLE! Did NOT re-trigger prematurely before repeat time!")

    # 4. Now simulate arrival of the scheduled repeat time
    print(f"  -> Simulating arrival of scheduled repeat time ({future_start})...")
    q_item.scheduled_time = now_utc - timedelta(seconds=5)
    db.commit()

    # Now auto-advance SHOULD pick the notice and play Round 2!
    adv_res2 = auto_advance_speaker_queue(db, force_advance=False)
    db.refresh(q_item)
    assert adv_res2 is not None, "Expected notice to be promoted when scheduled time arrived!"
    assert q_item.status == "Playing", f"Expected 'Playing', but got {q_item.status}!"
    print("  ✓ SUCCESS: Notice successfully started Round 2 when scheduled time arrived!")

    print("\n=======================================================")
    print("  ✅ VERIFICATION 100% COMPLETE & PASSING!")
    print("=======================================================\n")

if __name__ == "__main__":
    test_exact_user_scenario()
