import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums.announcement import AnnouncementStatus
from app.models.announcement import Announcement
from app.models.announcement_delivery import AnnouncementDelivery
from app.models.announcement_repeat_schedule import (
    AnnouncementRepeatSchedule,
    RepeatSlotExecutionLog,
)
from app.models.delivery_type import DeliveryType
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.user import User
from app.schemas.repeat_schedule import (
    RepeatScheduleCreate,
    RepeatScheduleUpdate,
)
from app.services.hardware_speaker_service import (
    auto_advance_speaker_queue,
    enqueue_and_broadcast_announcement,
)
from app.services.tts_service import generate_announcement_audio_sync

logger = logging.getLogger("echosphere.repeat_schedule")

# Standard Break Window Timings
SHORT_BREAK_START = "11:00"
SHORT_BREAK_END = "11:15"
LUNCH_BREAK_START = "13:15"
LUNCH_BREAK_END = "14:00"


def configure_repeat_schedule(
    db: Session,
    announcement_id: int,
    data: RepeatScheduleCreate | RepeatScheduleUpdate,
    current_user: User,
) -> AnnouncementRepeatSchedule:
    """
    Configures or retrofits a repeat broadcast schedule for an announcement.
    Enforces speaker-only delivery, 48-hour event horizon, and 2-day lifespan bounds.
    """
    # 1. Fetch announcement
    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Announcement #{announcement_id} not found.",
        )

    # 2. Check permissions: creator, admin, or department authority
    user_role = getattr(current_user.role, "name", "").upper() if current_user and current_user.role else ""
    is_creator = current_user and current_user.id == announcement.created_by
    is_admin_or_lead = user_role in ("ADMIN", "SUPERADMIN", "HOD", "DEAN", "FACULTY", "COORDINATOR")
    if not is_creator and not is_admin_or_lead:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to configure repeat broadcasts for this notice.",
        )

    # 3. Rule Check: Repeat schedule is strictly permitted for speaker notices only
    has_speaker = announcement.deliver_speaker
    force_enable = getattr(data, "force_enable_speaker", False) or False

    if not has_speaker and not force_enable:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Repeat broadcasts are only permitted for audio speaker notices. "
                "Enable 'deliver_speaker' on this announcement or pass force_enable_speaker=true."
            ),
        )

    if not has_speaker and force_enable:
        # Retrofit announcement to enable speaker delivery
        speaker_type = db.query(DeliveryType).filter(DeliveryType.name.ilike("%speaker%")).first()
        if speaker_type:
            existing_deliv = (
                db.query(AnnouncementDelivery)
                .filter(
                    AnnouncementDelivery.announcement_id == announcement_id,
                    AnnouncementDelivery.delivery_type_id == speaker_type.id,
                )
                .first()
            )
            if not existing_deliv:
                db.add(
                    AnnouncementDelivery(
                        announcement_id=announcement_id,
                        delivery_type_id=speaker_type.id,
                    )
                )

        # Pre-synthesize TTS audio stream so it's ready for speaker queue playback
        voice_gender = getattr(announcement, "speaker_voice", "female") or "female"
        try:
            generate_announcement_audio_sync(
                announcement_id,
                f"{announcement.title}. {announcement.description}",
                gender=voice_gender,
            )
        except Exception as te:
            logger.warning(f"Could not pre-synthesize TTS audio during repeat configuration: {te}")

    # 4. Anti-Spam Validation: 48-hour event horizon and 2-day lifespan
    event_dt = data.event_datetime if data.event_datetime is not None else None
    start_dt = data.start_date if data.start_date is not None else None
    end_dt = data.end_date if data.end_date is not None else None

    # Retrieve existing schedule if update
    schedule = (
        db.query(AnnouncementRepeatSchedule)
        .filter(AnnouncementRepeatSchedule.announcement_id == announcement_id)
        .first()
    )

    if schedule:
        event_dt = event_dt or schedule.event_datetime
        start_dt = start_dt or schedule.start_date
        end_dt = end_dt or schedule.end_date

    if event_dt and start_dt:
        horizon_seconds = (event_dt - start_dt).total_seconds()
        if horizon_seconds > (48 * 3600 + 300):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anti-Spam Guard: Repeat schedule can only begin within 48 hours prior to the event date.",
            )

    if start_dt and end_dt:
        duration_seconds = (end_dt - start_dt).total_seconds()
        if duration_seconds > (2 * 86400 + 300):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Anti-Spam Guard: Repeat schedule lifespan cannot exceed 2 days (48 hours).",
            )
        if end_dt < start_dt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid schedule: end_date cannot be earlier than start_date.",
            )

    # 5. Resolve or validate target node if specified
    target_node_id = data.target_node_id if data.target_node_id is not None else (schedule.target_node_id if schedule else None)
    if target_node_id:
        node = db.query(SpeakerNode).filter(SpeakerNode.id == target_node_id).first()
        if not node:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target speaker node #{target_node_id} does not exist.",
            )

    # 6. Create or update record
    if not schedule:
        schedule = AnnouncementRepeatSchedule(
            announcement_id=announcement_id,
            selected_slots=data.selected_slots or ["SHORT_BREAK", "LUNCH_BREAK"],
            custom_start_time=data.custom_start_time,
            custom_end_time=data.custom_end_time,
            target_scope=data.target_scope or "DEPARTMENT",
            target_node_id=target_node_id,
            event_datetime=event_dt,
            start_date=start_dt,
            end_date=end_dt,
            is_active=True,
        )
        db.add(schedule)
    else:
        if data.selected_slots is not None:
            schedule.selected_slots = data.selected_slots
        if data.custom_start_time is not None:
            schedule.custom_start_time = data.custom_start_time
        if data.custom_end_time is not None:
            schedule.custom_end_time = data.custom_end_time
        if data.target_scope is not None:
            schedule.target_scope = data.target_scope
        if data.target_node_id is not None:
            schedule.target_node_id = target_node_id
        if data.event_datetime is not None:
            schedule.event_datetime = event_dt
        if data.start_date is not None:
            schedule.start_date = start_dt
        if data.end_date is not None:
            schedule.end_date = end_dt
        if getattr(data, "is_active", None) is not None:
            schedule.is_active = data.is_active

    db.commit()
    db.refresh(schedule)
    logger.info(f"🔁 Repeat schedule configured for Announcement #{announcement_id} (Slots: {schedule.selected_slots})")
    return schedule


def get_repeat_schedule_by_announcement(
    db: Session,
    announcement_id: int,
) -> Optional[AnnouncementRepeatSchedule]:
    """Retrieves the repeat schedule and execution logs for an announcement."""
    return (
        db.query(AnnouncementRepeatSchedule)
        .filter(AnnouncementRepeatSchedule.announcement_id == announcement_id)
        .first()
    )


def delete_repeat_schedule(
    db: Session,
    announcement_id: int,
    current_user: User,
) -> bool:
    """Deletes or deactivates an announcement's repeat schedule."""
    schedule = (
        db.query(AnnouncementRepeatSchedule)
        .filter(AnnouncementRepeatSchedule.announcement_id == announcement_id)
        .first()
    )
    if not schedule:
        return False

    db.delete(schedule)
    db.commit()
    logger.info(f"🗑️ Repeat schedule removed for Announcement #{announcement_id}")
    return True


def get_active_break_slots(time_str: str) -> List[str]:
    """Identifies which standard campus break slot is currently active."""
    active = []
    if SHORT_BREAK_START <= time_str <= SHORT_BREAK_END:
        active.append("SHORT_BREAK")
    if LUNCH_BREAK_START <= time_str <= LUNCH_BREAK_END:
        active.append("LUNCH_BREAK")
    return active


def evaluate_and_dispatch_repeat_slots(
    db: Session,
    simulated_time_str: Optional[str] = None,
    simulated_date_str: Optional[str] = None,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> Dict[str, any]:
    """
    Evaluates current time against configured repeat schedules:
    1. Determines active campus break or custom window.
    2. Enqueues eligible repeat broadcasts with independent execution signatures.
    3. Protects class lecture hours with slot end cutoff TTLs.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_str = simulated_time_str or now.strftime("%H:%M")
    date_str = simulated_date_str or now.strftime("%Y-%m-%d")

    active_standard_slots = get_active_break_slots(time_str)

    dispatched = []
    skipped = []

    # 1. Fetch all active repeat schedules within valid date window
    query = db.query(AnnouncementRepeatSchedule).filter(
        AnnouncementRepeatSchedule.is_active == True,
        AnnouncementRepeatSchedule.start_date <= now,
        AnnouncementRepeatSchedule.end_date >= now,
    )
    schedules = query.all()

    for sched in schedules:
        ann = sched.announcement
        # Cascade guard: If parent announcement was archived, cancelled, or rejected, disable repeat
        ann_status = getattr(ann, "status", "")
        status_val = ann_status.value if hasattr(ann_status, "value") else str(ann_status)
        if status_val.upper() not in ("PUBLISHED", "SCHEDULED"):
            sched.is_active = False
            db.commit()
            continue

        # Check which of the schedule's chosen slots match current time
        matched_slots: List[str] = []
        for slot in sched.selected_slots:
            if slot in active_standard_slots:
                matched_slots.append(slot)
            elif slot == "CUSTOM_WINDOW":
                if sched.custom_start_time and sched.custom_end_time:
                    if sched.custom_start_time <= time_str <= sched.custom_end_time:
                        matched_slots.append("CUSTOM_WINDOW")

        if not matched_slots:
            continue

        for slot_name in matched_slots:
            slot_key = f"{sched.announcement_id}:{slot_name}:{date_str}"

            # Slot Idempotency Check: Has this specific slot already played today?
            existing_log = (
                db.query(RepeatSlotExecutionLog)
                .filter(RepeatSlotExecutionLog.slot_key == slot_key)
                .first()
            )
            if existing_log:
                skipped.append({"announcement_id": sched.announcement_id, "slot": slot_name, "reason": "Already played in this slot today"})
                continue

            # 2. Determine target nodes and audience scope
            dept_code = "ALL"
            target_zone = "College-Wide"
            target_node_id = sched.target_node_id

            if sched.target_scope == "DEPARTMENT":
                if ann.creator and ann.creator.department:
                    dept_code = ann.creator.department.code or "ALL"
                target_zone = "Departmental"
            elif sched.target_scope == "HOSTEL":
                target_zone = "Hostel"
                dept_code = "ALL"

            # 3. Re-activate / Enqueue in Speaker Queue following all queue rules
            enqueue_result = enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=sched.announcement_id,
                title=f"[Repeat] {ann.title}",
                content=ann.description,
                department_code=dept_code,
                zone=target_zone,
                is_emergency=False,
                speaker_node_id=target_node_id,
                speaker_voice=ann.speaker_voice or "female",
                base_url=base_url,
            )

            # 4. Record execution log for independent replay tracking
            exec_log = RepeatSlotExecutionLog(
                schedule_id=sched.id,
                slot_key=slot_key,
                slot_name=slot_name,
                played_at=now,
            )
            db.add(exec_log)
            sched.total_played_count += 1
            db.commit()

            dispatched.append({
                "announcement_id": sched.announcement_id,
                "title": ann.title,
                "slot": slot_name,
                "scope": sched.target_scope,
                "queue_status": enqueue_result.get("queue_status"),
                "queue_position": enqueue_result.get("queue_position"),
            })
            logger.info(f"📢 [REPEAT BROADCAST DISPATCHED] Announcement #{sched.announcement_id} in {slot_name} slot ({sched.target_scope})")

    # 5. Class Lecture Protection (TTL Expiration):
    # If we are currently outside of all break slots and custom windows,
    # inspect any queued repeats and mark unplayed items as 'Expired_Slot_Ended'
    # so they never blare inside classrooms when lectures are in session.
    is_in_any_standard_break = bool(active_standard_slots)
    if not is_in_any_standard_break:
        # Check if there are unplayed queue items whose scheduled_time was during a break that has now elapsed
        unplayed_repeat_items = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.status.in_(["Queued", "Next in Queue"]),
            )
            .all()
        )
        for item in unplayed_repeat_items:
            sched_time = getattr(item, "scheduled_time", None)
            if sched_time:
                sched_time_str = sched_time.strftime("%H:%M")
                # If item was scheduled during short break but now past 11:15
                if (SHORT_BREAK_START <= sched_time_str <= SHORT_BREAK_END) and (time_str > SHORT_BREAK_END):
                    item.status = "Expired_Slot_Ended"
                    db.commit()
                    logger.info(f"⏸️ Speaker Queue Item #{item.id} expired: Short Break ended, protected lecture hours.")
                # If item was scheduled during lunch break but now past 14:00
                elif (LUNCH_BREAK_START <= sched_time_str <= LUNCH_BREAK_END) and (time_str > LUNCH_BREAK_END):
                    item.status = "Expired_Slot_Ended"
                    db.commit()
                    logger.info(f"⏸️ Speaker Queue Item #{item.id} expired: Lunch Break ended, protected lecture hours.")

    return {
        "active_slots": active_standard_slots,
        "current_time": time_str,
        "dispatched_count": len(dispatched),
        "dispatched": dispatched,
        "skipped": skipped,
    }
