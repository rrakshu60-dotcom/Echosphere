import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums.announcement import (
    AnnouncementPriority,
    AnnouncementStatus,
    EmergencyLevel,
)
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

# Standard Campus Acoustic Break Window Timings (IST)
SHORT_BREAK_START = "11:00"
SHORT_BREAK_END = "11:15"
LUNCH_BREAK_START = "13:15"
LUNCH_BREAK_END = "14:00"
EVENING_BREAK_START = "16:30"
EVENING_BREAK_END = "17:30"
HOSTEL_WINDOW_START = "19:30"
HOSTEL_WINDOW_END = "21:00"


def get_current_ist_datetime() -> datetime:
    """Returns the current datetime in Indian Standard Time (IST, UTC+05:30)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        from datetime import timedelta
        return datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)



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
    is_admin_or_lead = any(
        kw in user_role for kw in ("ADMIN", "SUPERADMIN", "HOD", "DEAN", "FACULTY", "COORDINATOR", "PRINCIPAL", "DEVELOPER", "TEACHER")
    )
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

    announcement = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    user_role = getattr(current_user.role, "name", "").upper() if current_user and current_user.role else ""
    is_creator = current_user and announcement and current_user.id == announcement.created_by
    is_admin_or_lead = any(
        kw in user_role for kw in ("ADMIN", "SUPERADMIN", "HOD", "DEAN", "FACULTY", "COORDINATOR", "PRINCIPAL", "DEVELOPER", "TEACHER")
    )
    if not is_creator and not is_admin_or_lead:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete repeat broadcasts for this notice.",
        )

    db.delete(schedule)
    db.commit()
    logger.info(f"🗑️ Repeat schedule removed for Announcement #{announcement_id}")
    return True


from app.core.emergency_utils import is_emergency_announcement


def get_active_break_slots(time_str: str) -> List[str]:
    """Identifies which standard campus acoustic break slot is currently active in IST."""
    active = []
    if SHORT_BREAK_START <= time_str <= SHORT_BREAK_END:
        active.append("SHORT_BREAK")
    if LUNCH_BREAK_START <= time_str <= LUNCH_BREAK_END:
        active.append("LUNCH_BREAK")
    if EVENING_BREAK_START <= time_str <= EVENING_BREAK_END:
        active.append("EVENING_BREAK")
    if HOSTEL_WINDOW_START <= time_str <= HOSTEL_WINDOW_END:
        active.append("HOSTEL_WINDOW")
    return active


def get_notice_priority_info(ann: Announcement) -> tuple[int, int, str]:
    """
    Evaluates announcement priority and emergency posture.
    Returns: (priority_weight, max_repeats_in_slot, priority_tier)

    Emergency Notice:
      - Weight: 1000, max_repeats: 999999 (Overrides ALL other notices and loops continuously)

    Standard Notices in Repeat Slot:
      - In the configured repeat time period (e.g. 11:00-11:15 or custom window), all notices
        assigned to that slot rotate continuously throughout the entire window as much as can play.
      - Priority weights dictate initial queue ordering (High 300 > Medium 200 > Low 100),
        and all notices rotate in round-robin sequence until the slot concludes.
    """
    if is_emergency_announcement(ann):
        return 1000, 999999, "EMERGENCY"

    prio = getattr(ann, "priority", None)
    prio_str = str(getattr(prio, "value", prio) or "NORMAL").upper()
    title = str(getattr(ann, "title", "") or "").lower()
    desc = str(getattr(ann, "description", "") or "").lower()
    combined = f"{title} {desc}"

    if "HIGH" in prio_str or "URGENT" in prio_str or any(
        w in combined for w in ["exam", "examination", "test", "timetable", "hall ticket", "viva", "semester", "sem exam", "placement", "interview", "deadline", "fee payment"]
    ):
        return 300, 999999, "HIGH"
    elif "LOW" in prio_str or any(
        w in combined for w in ["lost and found", "lost & found", "lost item", "found item", "lost", "found", "canteen", "maintenance", "bus timing", "reminder"]
    ):
        return 100, 999999, "LOW"
    else:  # NORMAL or MEDIUM (sports, volleyball, events, cultural, hackathons)
        return 200, 999999, "MEDIUM"


def is_slot_active_at_time(
    sched: AnnouncementRepeatSchedule,
    time_str: str,
    active_standard_slots: List[str],
) -> List[str]:
    """Checks whether the given repeat schedule has slots matching current time_str."""
    matched_slots: List[str] = []
    for slot in (sched.selected_slots or []):
        if slot in active_standard_slots:
            matched_slots.append(slot)
        elif slot == "CUSTOM_WINDOW":
            c_start = (sched.custom_start_time or "").strip()
            c_end = (sched.custom_end_time or "").strip()
            if not c_end and c_start:
                try:
                    sh, sm = map(int, c_start.split(":"))
                    end_minutes = (sh * 60 + sm + 30) % (24 * 60)
                    eh, em = end_minutes // 60, end_minutes % 60
                    c_end = f"{eh:02d}:{em:02d}"
                except Exception:
                    c_end = c_start
            if c_start and c_end:
                if c_start <= c_end:
                    if c_start <= time_str <= c_end:
                        matched_slots.append("CUSTOM_WINDOW")
                else:
                    # Midnight wraparound (e.g. 23:45 to 00:15)
                    if time_str >= c_start or time_str <= c_end:
                        matched_slots.append("CUSTOM_WINDOW")
            elif c_start and c_start == time_str:
                matched_slots.append("CUSTOM_WINDOW")
    return matched_slots


def get_active_emergency_repeat_schedule(
    db: Session,
    simulated_time_str: Optional[str] = None,
    simulated_date_str: Optional[str] = None,
) -> Optional[AnnouncementRepeatSchedule]:
    """
    Checks if there is ANY active emergency announcement with a repeat schedule
    matching the current acoustic window (break slot or custom window).
    Returns the matching AnnouncementRepeatSchedule if found, else None.
    """
    ist_now = get_current_ist_datetime()
    ist_now_naive = ist_now.replace(tzinfo=None)
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_str = simulated_time_str or ist_now.strftime("%H:%M")

    active_standard_slots = get_active_break_slots(time_str)

    from sqlalchemy import and_, or_
    query = db.query(AnnouncementRepeatSchedule).filter(
        AnnouncementRepeatSchedule.is_active == True,
    )
    if not simulated_date_str:
        query = query.filter(
            or_(
                and_(
                    AnnouncementRepeatSchedule.start_date <= (utc_now + timedelta(minutes=5)),
                    AnnouncementRepeatSchedule.end_date >= (utc_now - timedelta(minutes=5)),
                ),
                and_(
                    AnnouncementRepeatSchedule.start_date <= (ist_now_naive + timedelta(minutes=5)),
                    AnnouncementRepeatSchedule.end_date >= (ist_now_naive - timedelta(minutes=5)),
                ),
            )
        )
    schedules = query.all()
    for sched in schedules:
        ann = sched.announcement
        if not ann:
            continue
        ann_status = getattr(ann, "status", "")
        status_val = ann_status.value if hasattr(ann_status, "value") else str(ann_status)
        if status_val.upper() not in ("PUBLISHED", "SCHEDULED"):
            continue

        if not is_emergency_announcement(ann):
            continue

        matched = is_slot_active_at_time(sched, time_str, active_standard_slots)
        if matched:
            return sched

    return None


def evaluate_and_dispatch_repeat_slots(
    db: Session,
    simulated_time_str: Optional[str] = None,
    simulated_date_str: Optional[str] = None,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> Dict[str, any]:
    """
    Evaluates current time against configured repeat schedules:
    1. Determines active campus break or custom window in Indian Standard Time (IST).
    2. Enforces Emergency Broadcast Lockdown: If ANY emergency notice is active for this break
       or custom window, it plays CONTINUOUSLY for the entire window and completely SUPPRESSES
       all other notices!
    3. Ranks eligible notices by AI-assigned priority (Emergency -> High -> Medium -> Low).
    4. Repeats according to priority tier:
       - Emergency: Repeats throughout the whole break / custom window
       - High: Repeats up to 3 times
       - Medium / Normal: Repeats up to 2 times
       - Low: Repeats 1 time
    5. Protects class lecture hours with hard cutoff slot end TTLs, expiring unplayed items.
    """
    ist_now = get_current_ist_datetime()
    ist_now_naive = ist_now.replace(tzinfo=None)
    utc_now = datetime.now(timezone.utc).replace(tzinfo=None)
    time_str = simulated_time_str or ist_now.strftime("%H:%M")
    date_str = simulated_date_str or ist_now.strftime("%Y-%m-%d")

    active_standard_slots = get_active_break_slots(time_str)

    dispatched = []
    skipped = []

    # Priority Check: Detect active emergency repeat schedule for this acoustic window
    active_emerg_sched = get_active_emergency_repeat_schedule(
        db, simulated_time_str=time_str, simulated_date_str=date_str
    )
    has_active_emergency_scheduled = (active_emerg_sched is not None)

    # 1. Fetch all active repeat schedules within valid date window
    query = db.query(AnnouncementRepeatSchedule).filter(
        AnnouncementRepeatSchedule.is_active == True,
    )
    if not simulated_date_str:
        from sqlalchemy import and_, or_
        query = query.filter(
            or_(
                # Valid under UTC timestamps
                and_(
                    AnnouncementRepeatSchedule.start_date <= (utc_now + timedelta(minutes=5)),
                    AnnouncementRepeatSchedule.end_date >= (utc_now - timedelta(minutes=5)),
                ),
                # Valid under local IST timestamps
                and_(
                    AnnouncementRepeatSchedule.start_date <= (ist_now_naive + timedelta(minutes=5)),
                    AnnouncementRepeatSchedule.end_date >= (ist_now_naive - timedelta(minutes=5)),
                ),
            )
        )
    schedules = query.all()

    # If an emergency broadcast schedule is actively ongoing, enforce total pause of all other notices
    if has_active_emergency_scheduled and active_emerg_sched:
        active_non_em = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.announcement_id != active_emerg_sched.announcement_id,
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
            )
            .all()
        )
        for item in active_non_em:
            item.status = "Paused"
        db.commit()

    # 2. Phase 1: Collect & validate candidates matching active acoustic window
    candidates = []

    for sched in schedules:
        ann = sched.announcement
        if not ann:
            continue

        # Cascade guard: If parent announcement was archived, cancelled, or rejected, disable repeat
        ann_status = getattr(ann, "status", "")
        status_val = ann_status.value if hasattr(ann_status, "value") else str(ann_status)
        if status_val.upper() not in ("PUBLISHED", "SCHEDULED"):
            sched.is_active = False
            db.commit()
            continue

        # Check which of the schedule's chosen slots match current time
        matched_slots = is_slot_active_at_time(sched, time_str, active_standard_slots)

        if not matched_slots:
            continue

        prio_weight, max_repeats, prio_tier = get_notice_priority_info(ann)
        is_em = (prio_tier == "EMERGENCY")
        if is_em:
            has_active_emergency_scheduled = True

        # If an emergency broadcast override is active, strictly skip and suppress all non-emergency notices!
        if has_active_emergency_scheduled and not is_em:
            for slot_name in matched_slots:
                skipped.append({
                    "announcement_id": sched.announcement_id,
                    "slot": slot_name,
                    "reason": "Suppressed by active Emergency Broadcast Override (e.g. Earthquake/Evacuation alert active)",
                })
            continue

        for slot_name in matched_slots:
            prefix_key = f"{sched.announcement_id}:{slot_name}:{date_str}"
            if slot_name == "CUSTOM_WINDOW":
                prefix_key = f"{sched.announcement_id}:CUSTOM_WINDOW:{sched.custom_start_time or 'WIN'}:{date_str}"

            # Query existing execution logs for this slot today
            slot_logs = (
                db.query(RepeatSlotExecutionLog)
                .filter(
                    RepeatSlotExecutionLog.schedule_id == sched.id,
                    RepeatSlotExecutionLog.slot_name == slot_name,
                )
                .all()
            )
            times_played_today = sum(
                1 for log in slot_logs
                if log.slot_key == prefix_key or log.slot_key.startswith(f"{prefix_key}:")
            )

            # Check if repeat cap reached (emergency has cap 999999 so repeats whole break)
            if times_played_today >= max_repeats:
                skipped.append({
                    "announcement_id": sched.announcement_id,
                    "slot": slot_name,
                    "reason": f"Max repeats ({times_played_today}/{max_repeats}) reached for {prio_tier} priority in this slot today",
                })
                continue

            # Check if notice is currently active in the speaker queue for this slot
            active_q = (
                db.query(SpeakerQueue)
                .filter(
                    SpeakerQueue.announcement_id == sched.announcement_id,
                    SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
                )
                .first()
            )
            if active_q:
                curr_played_at = getattr(active_q, "played_at", None)
                curr_dur = getattr(active_q, "duration_seconds", 15) or 15
                is_currently_speaking = False
                if active_q.status == "Playing" and curr_played_at:
                    elapsed = (utc_now - curr_played_at).total_seconds()
                    if elapsed < curr_dur and not simulated_time_str:
                        is_currently_speaking = True

                if is_currently_speaking:
                    skipped.append({
                        "announcement_id": sched.announcement_id,
                        "slot": slot_name,
                        "reason": f"Already actively broadcasting in speaker queue (status: {active_q.status})",
                    })
                    continue

                if times_played_today > 0:
                    skipped.append({
                        "announcement_id": sched.announcement_id,
                        "slot": slot_name,
                        "reason": f"Already active in speaker queue rotation (status: {active_q.status})",
                    })
                    continue
                else:
                    # Item was left from an earlier slot/broadcast; mark completed so new slot begins fresh
                    active_q.status = "Completed"
                    db.commit()

            candidates.append({
                "sched": sched,
                "ann": ann,
                "slot_name": slot_name,
                "prefix_key": prefix_key,
                "weight": prio_weight,
                "max_repeats": max_repeats,
                "tier": prio_tier,
                "times_played_today": times_played_today,
                "is_emergency": is_em,
                "created_at": getattr(ann, "created_at", None) or datetime.min,
            })

    # 3. Phase 2: Emergency Override Lock
    # If ANY emergency notice (e.g. Earthquake, Evacuation, Fire Alert) is scheduled for this break/custom window,
    # it completely supersedes and suppresses ALL other announcements.
    # ONLY the emergency notice broadcasts, repeating continuously for the entire break or custom window!
    emergency_candidates = [c for c in candidates if c["is_emergency"]]
    if emergency_candidates or has_active_emergency_scheduled:
        non_emergency_candidates = [c for c in candidates if not c["is_emergency"]]
        for nec in non_emergency_candidates:
            skipped.append({
                "announcement_id": nec["sched"].announcement_id,
                "slot": nec["slot_name"],
                "reason": "Suppressed by active Emergency Broadcast Override (e.g. Earthquake/Evacuation alert active)",
            })

        # Pause any non-emergency notices currently in the speaker queue
        active_non_em = (
            db.query(SpeakerQueue)
            .filter(SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]))
            .all()
        )
        for item in active_non_em:
            if item.announcement and is_emergency_announcement(item.announcement):
                continue
            item.status = "Paused"
        db.commit()

        candidates = emergency_candidates
        if candidates:
            logger.warning(
                f"🚨 [EMERGENCY LOCKDOWN] Active emergency notice detected. "
                f"Ignoring all {len(non_emergency_candidates)} other notices. "
                f"Broadcasting Announcement #{candidates[0]['sched'].announcement_id} continuously for the entire break/custom window!"
            )
    else:
        # If no emergency, sort standard candidates by Priority (High 300 > Medium 200 > Low 100) and Recency
        candidates.sort(
            key=lambda c: (
                c["weight"],
                c["created_at"],
            ),
            reverse=True,
        )

    # 4. Phase 3: Enqueue and Broadcast in Ranked Priority Order
    for cand in candidates:
        sched = cand["sched"]
        ann = cand["ann"]
        slot_name = cand["slot_name"]
        tier = cand["tier"]
        is_em = cand["is_emergency"]
        next_repeat_num = cand["times_played_today"] + 1

        slot_key = f"{cand['prefix_key']}:{next_repeat_num}"

        # Resolve audience scope
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

        repeat_title = f"[EMERGENCY REPEAT] {ann.title}" if is_em else f"[Repeat - {tier}] {ann.title}"

        enqueue_result = enqueue_and_broadcast_announcement(
            db=db,
            announcement_id=sched.announcement_id,
            title=repeat_title,
            content=ann.description,
            department_code=dept_code,
            zone=target_zone,
            is_emergency=is_em,
            speaker_node_id=target_node_id,
            speaker_voice=ann.speaker_voice or "female",
            base_url=base_url,
        )

        exec_log = RepeatSlotExecutionLog(
            schedule_id=sched.id,
            slot_key=slot_key,
            slot_name=slot_name,
            played_at=utc_now,
        )
        db.add(exec_log)
        sched.total_played_count += 1
        db.commit()

        dispatched.append({
            "announcement_id": sched.announcement_id,
            "title": ann.title,
            "slot": slot_name,
            "priority": tier,
            "repeat_round": next_repeat_num,
            "max_repeats": "WHOLE_BREAK" if is_em else cand["max_repeats"],
            "scope": sched.target_scope,
            "queue_status": enqueue_result.get("queue_status"),
            "queue_position": enqueue_result.get("queue_position"),
        })
        logger.info(
            f"📢 [REPEAT BROADCAST DISPATCHED] Announcement #{sched.announcement_id} [{tier} Round {next_repeat_num}] in {slot_name} slot ({sched.target_scope})"
        )

    # 5. Class Lecture Protection (TTL Expiration):
    # Hard cutoff TTLs expire unplayed repeat notices when a break window concludes
    # to safeguard classroom tranquility and prevent blaring during academic lectures.
    expired_count = 0
    unplayed_items = (
        db.query(SpeakerQueue)
        .filter(
            SpeakerQueue.status.in_(["Queued", "Next in Queue"]),
        )
        .all()
    )

    for item in unplayed_items:
        # Check if item has repeat schedule
        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(AnnouncementRepeatSchedule.announcement_id == item.announcement_id)
            .first()
        )
        if not sched:
            continue

        sched_time = getattr(item, "scheduled_time", None)
        if sched_time:
            # Gather potential candidates for scheduled time in HH:MM (raw and IST-converted)
            sched_time_candidates = [sched_time.strftime("%H:%M")]
            try:
                sched_ist = sched_time + timedelta(hours=5, minutes=30)
                sched_time_candidates.append(sched_ist.strftime("%H:%M"))
            except Exception:
                pass

            expired = False
            # Short Break Cutoff: 11:15 sharp
            if any(SHORT_BREAK_START <= st <= SHORT_BREAK_END for st in sched_time_candidates) and (time_str > SHORT_BREAK_END):
                expired = True
                logger.info(f"⏸️ Speaker Queue #{item.id} expired: Short Break ended at {SHORT_BREAK_END}. Classroom silence protected.")
            # Lunch Break Cutoff: 14:00 sharp
            elif any(LUNCH_BREAK_START <= st <= LUNCH_BREAK_END for st in sched_time_candidates) and (time_str > LUNCH_BREAK_END):
                expired = True
                logger.info(f"⏸️ Speaker Queue #{item.id} expired: Lunch Break ended at {LUNCH_BREAK_END}. Classroom silence protected.")
            # Evening Break Cutoff: 17:30 sharp
            elif any(EVENING_BREAK_START <= st <= EVENING_BREAK_END for st in sched_time_candidates) and (time_str > EVENING_BREAK_END):
                expired = True
                logger.info(f"⏸️ Speaker Queue #{item.id} expired: Evening Break ended at {EVENING_BREAK_END}. Campus quiet hours protected.")
            # Hostel Window Cutoff: 21:00 sharp
            elif any(HOSTEL_WINDOW_START <= st <= HOSTEL_WINDOW_END for st in sched_time_candidates) and (time_str > HOSTEL_WINDOW_END):
                expired = True
                logger.info(f"⏸️ Speaker Queue #{item.id} expired: Hostel Window ended at {HOSTEL_WINDOW_END}. Night quiet hours protected.")
            # Custom Window Cutoff: custom_end_time
            elif sched.custom_start_time:
                c_start = sched.custom_start_time
                c_end = sched.custom_end_time
                if not c_end:
                    try:
                        sh, sm = map(int, c_start.split(":"))
                        end_minutes = (sh * 60 + sm + 30) % (24 * 60)
                        c_end = f"{end_minutes // 60:02d}:{end_minutes % 60:02d}"
                    except Exception:
                        c_end = c_start
                if any(c_start <= st <= c_end for st in sched_time_candidates) and (time_str > c_end):
                    prio_weight, max_repeats, prio_tier = get_notice_priority_info(item.announcement) if item.announcement else (200, 2, "MEDIUM")
                    if sched.total_played_count < max_repeats:
                        expired = False
                    else:
                        expired = True
                        logger.info(f"⏸️ Speaker Queue #{item.id} expired: Custom Window ended at {c_end}. Quiet hours protected.")

            if expired:
                item.status = "Expired_Slot_Ended"
                db.commit()
                expired_count += 1

    if expired_count > 0:
        try:
            auto_advance_speaker_queue(db, base_url=base_url)
        except Exception as ae:
            logger.debug(f"Queue auto-advance note after TTL expiry: {ae}")

    return {
        "active_slots": active_standard_slots,
        "current_time_ist": time_str,
        "current_date": date_str,
        "dispatched_count": len(dispatched),
        "expired_ttl_count": expired_count,
        "dispatched": dispatched,
        "skipped": skipped,
    }
