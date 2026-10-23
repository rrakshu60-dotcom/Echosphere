import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """Safely normalizes any datetime to timezone-naive UTC to avoid TypeError comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


BROADCAST_GAP_SECONDS = 4

SLOT_BOUNDS = {
    "SHORT_BREAK": (SHORT_BREAK_START, SHORT_BREAK_END),
    "LUNCH_BREAK": (LUNCH_BREAK_START, LUNCH_BREAK_END),
    "EVENING_BREAK": (EVENING_BREAK_START, EVENING_BREAK_END),
    "HOSTEL_WINDOW": (HOSTEL_WINDOW_START, HOSTEL_WINDOW_END),
}

SLOT_LABELS = {
    "SHORT_BREAK": "Short Break (11:00 AM – 11:15 AM)",
    "LUNCH_BREAK": "Lunch Break (1:15 PM – 2:00 PM)",
    "EVENING_BREAK": "Evening Break (4:30 PM – 5:30 PM)",
    "HOSTEL_WINDOW": "Hostel Window (7:30 PM – 9:00 PM)",
}

SLOT_DURATIONS = {
    "SHORT_BREAK": 15,
    "LUNCH_BREAK": 45,
    "EVENING_BREAK": 60,
    "HOSTEL_WINDOW": 90,
}


def calculate_time_window_duration(start_hhmm: Optional[str], end_hhmm: Optional[str]) -> Dict[str, Any]:
    """Calculates duration in minutes and a formatted 12-hour display string for a time window."""
    if not start_hhmm or not end_hhmm:
        return {
            "duration_minutes": 0,
            "duration_str": "",
            "display_range": "",
            "formatted_summary": "",
        }
    try:
        sh, sm = map(int, start_hhmm.strip().split(":"))
        eh, em = map(int, end_hhmm.strip().split(":"))
        start_mins = sh * 60 + sm
        end_mins = eh * 60 + em
        diff_mins = end_mins - start_mins
        if diff_mins < 0:
            diff_mins += 24 * 60

        hrs = diff_mins // 60
        mins = diff_mins % 60
        parts = []
        if hrs > 0:
            parts.append(f"{hrs} hr" if hrs == 1 else f"{hrs} hrs")
        if mins > 0:
            parts.append(f"{mins} mins")
        dur_str = " ".join(parts) if parts else "0 mins"

        def _fmt12(h: int, m: int) -> str:
            mer = "PM" if h >= 12 else "AM"
            h12 = 12 if h in (0, 12) else (h - 12 if h > 12 else h)
            return f"{h12}:{m:02d} {mer}"

        display_range = f"{_fmt12(sh, sm)} – {_fmt12(eh, em)}"
        return {
            "duration_minutes": diff_mins,
            "duration_str": dur_str,
            "display_range": display_range,
            "formatted_summary": f"Custom Window: {display_range} ({dur_str})",
        }
    except Exception:
        return {
            "duration_minutes": 0,
            "duration_str": "",
            "display_range": f"{start_hhmm} – {end_hhmm}",
            "formatted_summary": f"Custom Window: {start_hhmm} – {end_hhmm}",
        }


def get_schedule_time_summary(sched: Any) -> Dict[str, Any]:
    """Computes aggregate time range and duration summary across all selected break slots and custom window."""
    if not sched:
        return {"summary": "", "total_duration_minutes": 0}

    slots = getattr(sched, "selected_slots", None) or []
    summaries = []
    total_minutes = 0

    for slot in slots:
        if slot in SLOT_LABELS:
            summaries.append(SLOT_LABELS[slot])
            total_minutes += SLOT_DURATIONS.get(slot, 0)
        elif slot == "CUSTOM_WINDOW":
            c_start = getattr(sched, "custom_start_time", None)
            c_end = getattr(sched, "custom_end_time", None)
            c_info = calculate_time_window_duration(c_start, c_end)
            if c_info.get("formatted_summary"):
                summaries.append(c_info["formatted_summary"])
                total_minutes += c_info.get("duration_minutes", 0)

    return {
        "summary": ", ".join(summaries) if summaries else "Standard Campus Break Schedule",
        "total_duration_minutes": total_minutes,
    }



def _ist_to_utc_naive(dt_ist: datetime) -> datetime:
    """Converts an IST datetime (naive or aware) to a naive UTC datetime."""
    if dt_ist.tzinfo is not None:
        return dt_ist.astimezone(timezone.utc).replace(tzinfo=None)
    return dt_ist - timedelta(hours=5, minutes=30)


def _utc_to_ist_naive(dt_utc: datetime) -> datetime:
    """Converts a UTC datetime (naive or aware) to a naive IST datetime."""
    if dt_utc.tzinfo is not None:
        try:
            from zoneinfo import ZoneInfo
            return dt_utc.astimezone(ZoneInfo("Asia/Kolkata")).replace(tzinfo=None)
        except Exception:
            return dt_utc.astimezone(timezone.utc).replace(tzinfo=None) + timedelta(hours=5, minutes=30)
    return dt_utc + timedelta(hours=5, minutes=30)


def get_next_slot_datetime(
    sched: Any,
    from_ist_dt: Optional[datetime] = None,
    db: Optional[Session] = None,
) -> tuple[Optional[datetime], Optional[str]]:
    """
    Computes the exact next upcoming repeat datetime for a BREAK_SLOTS or CUSTOM schedule.
    Returns: (next_repeat_datetime_utc_naive, matched_slot_name) or (None, None) if schedule concluded.
    """
    if not sched:
        return None, None

    if from_ist_dt is None:
        from_ist_dt = get_current_ist_datetime()
    if from_ist_dt.tzinfo is not None:
        from_ist_dt = from_ist_dt.replace(tzinfo=None)

    # Determine schedule end date in IST
    sched_end_ist: Optional[datetime] = None
    if getattr(sched, "end_date", None):
        end_naive = _normalize_dt(sched.end_date)
        if end_naive:
            sched_end_ist = _utc_to_ist_naive(end_naive)

    if sched_end_ist and from_ist_dt > sched_end_ist:
        return None, None

    candidates: List[tuple[datetime, str]] = []
    slots = [s for s in (getattr(sched, "selected_slots", None) or []) if s != "INTERVAL"]
    if not slots and getattr(sched, "custom_start_time", None):
        slots = ["CUSTOM_WINDOW"]

    for slot_name in slots:
        start_hhmm = None
        end_hhmm = None

        if slot_name in SLOT_BOUNDS:
            start_hhmm, end_hhmm = SLOT_BOUNDS[slot_name]
        elif slot_name == "CUSTOM_WINDOW":
            start_hhmm = (getattr(sched, "custom_start_time", None) or "").strip()
            end_hhmm = (getattr(sched, "custom_end_time", None) or "").strip()
            if not end_hhmm and start_hhmm:
                try:
                    sh_tmp, sm_tmp = map(int, start_hhmm.split(":"))
                    end_m = (sh_tmp * 60 + sm_tmp + 30) % (24 * 60)
                    end_hhmm = f"{end_m // 60:02d}:{end_m % 60:02d}"
                except Exception:
                    end_hhmm = start_hhmm

        if not start_hhmm:
            continue

        try:
            sh, sm = map(int, start_hhmm.split(":"))
            eh, em = map(int, end_hhmm.split(":")) if end_hhmm else (sh, sm + 30)
        except Exception:
            continue

        today_d = from_ist_dt.date()
        slot_start_today = datetime(today_d.year, today_d.month, today_d.day, sh, sm)
        slot_end_today = datetime(today_d.year, today_d.month, today_d.day, eh, em)
        if slot_end_today < slot_start_today:
            slot_end_today += timedelta(days=1)

        # 1. Currently inside this slot window
        if slot_start_today <= from_ist_dt <= slot_end_today:
            times_played_in_slot = 0
            if db and getattr(sched, "id", None):
                date_str = from_ist_dt.strftime("%Y-%m-%d")
                prefix_key = f"{sched.announcement_id}:{slot_name}:{date_str}"
                if slot_name == "CUSTOM_WINDOW":
                    prefix_key = f"{sched.announcement_id}:CUSTOM_WINDOW:{sched.custom_start_time or 'WIN'}:{date_str}"
                slot_logs = (
                    db.query(RepeatSlotExecutionLog)
                    .filter(
                        RepeatSlotExecutionLog.schedule_id == sched.id,
                        RepeatSlotExecutionLog.slot_name == slot_name,
                    )
                    .all()
                )
                times_played_in_slot = sum(
                    1 for log in slot_logs
                    if log.slot_key == prefix_key or log.slot_key.startswith(f"{prefix_key}:")
                )

            # If announcement already played at least once (e.g. publish now or in-progress playback)
            total_played = getattr(sched, "total_played_count", 0) or 0
            effective_played_in_slot = max(times_played_in_slot, 1 if total_played > 0 else 0)

            # Resolve repeat cap for this slot
            ann = getattr(sched, "announcement", None)
            prio_weight, default_reps, prio_tier = get_notice_priority_info(ann) if ann else (200, 2, "MEDIUM")
            slot_max_repeats = 999999 if prio_tier == "EMERGENCY" else (sched.max_repeats if (sched.max_repeats and sched.max_repeats > 0) else default_reps)

            if prio_tier == "EMERGENCY":
                candidate_repeat = from_ist_dt + timedelta(seconds=BROADCAST_GAP_SECONDS)
                if candidate_repeat + timedelta(seconds=15) <= slot_end_today:
                    candidates.append((candidate_repeat, slot_name))
                else:
                    candidates.append((slot_start_today + timedelta(days=1), slot_name))
            elif effective_played_in_slot == 0:
                # Has not played yet in this active window: play now
                candidates.append((from_ist_dt, slot_name))
            else:
                interval_m = getattr(sched, "interval_minutes", 0) or 0
                if interval_m > 0 and effective_played_in_slot < slot_max_repeats:
                    candidate_repeat = from_ist_dt + timedelta(minutes=interval_m)
                    if candidate_repeat + timedelta(seconds=15) <= slot_end_today:
                        candidates.append((candidate_repeat, slot_name))
                    else:
                        candidates.append((slot_start_today + timedelta(days=1), slot_name))
                else:
                    # In standard break slots (or custom window without interval, or after max repeats in this slot):
                    # The notice has completed its broadcast for this slot window today.
                    # Its next repetition for this slot is tomorrow.
                    candidates.append((slot_start_today + timedelta(days=1), slot_name))

        # 2. Slot is upcoming today
        elif from_ist_dt < slot_start_today:
            candidates.append((slot_start_today, slot_name))

        # 3. Slot has already passed today
        else:
            candidates.append((slot_start_today + timedelta(days=1), slot_name))

    valid_candidates = []
    for cand_dt, sname in candidates:
        if cand_dt >= (from_ist_dt - timedelta(seconds=10)):
            if sched_end_ist is None or cand_dt <= sched_end_ist:
                valid_candidates.append((cand_dt, sname))

    if not valid_candidates:
        return None, None

    valid_candidates.sort(key=lambda c: c[0])
    earliest_ist, matched_slot = valid_candidates[0]
    return _ist_to_utc_naive(earliest_ist), matched_slot




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
    event_dt = _normalize_dt(data.event_datetime) if data.event_datetime is not None else None
    start_dt = _normalize_dt(data.start_date) if data.start_date is not None else None
    end_dt = _normalize_dt(data.end_date) if data.end_date is not None else None

    # Retrieve existing schedule if update
    schedule = (
        db.query(AnnouncementRepeatSchedule)
        .filter(AnnouncementRepeatSchedule.announcement_id == announcement_id)
        .first()
    )

    if schedule:
        event_dt = event_dt or _normalize_dt(schedule.event_datetime)
        start_dt = start_dt or _normalize_dt(schedule.start_date)
        end_dt = end_dt or _normalize_dt(schedule.end_date)

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

    # Extract mode and interval parameters
    rep_mode = getattr(data, "repeat_mode", None) or (schedule.repeat_mode if schedule else "BREAK_SLOTS")
    rep_interval = getattr(data, "interval_minutes", None) or (schedule.interval_minutes if schedule else 0)
    rep_max = getattr(data, "max_repeats", None) if getattr(data, "max_repeats", None) is not None else (schedule.max_repeats if schedule else 15)
    rep_publish = getattr(data, "play_on_publish", None) if getattr(data, "play_on_publish", None) is not None else (schedule.play_on_publish if schedule else True)

    # For BREAK_SLOTS / CUSTOM_WINDOW mode, ensure rep_max has ample capacity to rotate throughout the time window
    if rep_mode != "INTERVAL":
        active_slots = data.selected_slots or (schedule.selected_slots if schedule else []) or ["SHORT_BREAK"]
        slots_len = len(active_slots)
        custom_duration = 0
        c_start = getattr(data, "custom_start_time", None) or (schedule.custom_start_time if schedule else None)
        c_end = getattr(data, "custom_end_time", None) or (schedule.custom_end_time if schedule else None)
        if "CUSTOM_WINDOW" in active_slots or (c_start and c_end):
            c_info = calculate_time_window_duration(c_start, c_end)
            custom_duration = c_info.get("duration_minutes", 0)

        # Allocate sufficient repeat rotation capacity (at least 5 per preset break + 1 per 5 mins of custom window, min 10)
        calculated_cap = max(slots_len * 5 + (custom_duration // 5) + (1 if rep_publish else 0), 10)
        if rep_max is None or rep_max < calculated_cap:
            rep_max = calculated_cap

    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    ist_now = get_current_ist_datetime()

    # Calculate initial next_repeat_at
    if rep_mode == "INTERVAL":
        if rep_publish:
            initial_next = now_utc + timedelta(minutes=rep_interval)
        else:
            initial_next = start_dt if (start_dt and start_dt > now_utc) else (now_utc + timedelta(minutes=rep_interval))
    else:
        # Build mock/temp schedule to calculate next upcoming slot occurrence
        calc_sched = schedule or AnnouncementRepeatSchedule(
            announcement_id=announcement_id,
            selected_slots=data.selected_slots or (["INTERVAL"] if rep_mode == "INTERVAL" else ["SHORT_BREAK"]),
            custom_start_time=data.custom_start_time,
            custom_end_time=data.custom_end_time,
            start_date=start_dt,
            end_date=end_dt,
            max_repeats=rep_max,
        )
        if data.selected_slots is not None:
            calc_sched.selected_slots = data.selected_slots
        if data.custom_start_time is not None:
            calc_sched.custom_start_time = data.custom_start_time
        if data.custom_end_time is not None:
            calc_sched.custom_end_time = data.custom_end_time

        slot_dt, _ = get_next_slot_datetime(calc_sched, from_ist_dt=ist_now, db=db)
        initial_next = slot_dt or start_dt or now_utc

    # 6. Create or update record
    if not schedule:
        schedule = AnnouncementRepeatSchedule(
            announcement_id=announcement_id,
            repeat_mode=rep_mode,
            interval_minutes=rep_interval,
            max_repeats=rep_max,
            play_on_publish=rep_publish,
            next_repeat_at=initial_next,
            selected_slots=data.selected_slots or (["INTERVAL"] if rep_mode == "INTERVAL" else ["SHORT_BREAK"]),
            custom_start_time=data.custom_start_time,
            custom_end_time=data.custom_end_time,
            target_scope=data.target_scope or (schedule.target_scope if schedule else "COLLEGE_WIDE"),
            target_node_id=target_node_id,
            event_datetime=event_dt,
            start_date=start_dt,
            end_date=end_dt,
            is_active=True,
        )
        db.add(schedule)
    else:
        schedule.repeat_mode = rep_mode
        schedule.interval_minutes = rep_interval
        schedule.max_repeats = rep_max
        schedule.play_on_publish = rep_publish
        if getattr(data, "next_repeat_at", None) is not None:
            schedule.next_repeat_at = data.next_repeat_at
        elif not schedule.next_repeat_at:
            schedule.next_repeat_at = initial_next

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

    # 7. Queue synchronization for Published and Scheduled notices
    ann_status_val = getattr(announcement, "status", "")
    ann_status_str = ann_status_val.value if hasattr(ann_status_val, "value") else str(ann_status_val)
    if ann_status_str.upper() in ("PUBLISHED", "APPROVED", "SCHEDULED"):
        from app.models.speaker_queue import SpeakerQueue
        active_q: Any = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
        sched_time_target = getattr(announcement, "scheduled_at", None) or initial_next
        if not active_q:
            # Enqueue initial broadcast if play_on_publish (and not scheduled for later), or schedule for future
            if rep_publish and ann_status_str.upper() != "SCHEDULED":
                enqueue_and_broadcast_announcement(
                    db=db,
                    announcement_id=announcement_id,
                    title=announcement.title,
                    content=announcement.description,
                    department_code=announcement.creator.department.code if (announcement.creator and announcement.creator.department) else "ALL",
                    zone="Departmental" if schedule.target_scope == "DEPARTMENT" else "College-Wide",
                    is_emergency=False,
                    speaker_node_id=schedule.target_node_id,
                    speaker_voice=announcement.speaker_voice or "female",
                )
            else:
                max_pos = db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(["Queued", "Next in Queue"])).count()
                new_q = SpeakerQueue(
                    announcement_id=announcement_id,
                    queue_position=max_pos + 1,
                    status="Queued",
                    scheduled_time=sched_time_target or now_utc,
                    played_at=None,
                    duration_seconds=15,
                )
                db.add(new_q)
                db.commit()
        elif getattr(active_q, "status", None) == "Completed" and rep_publish and ann_status_str.upper() != "SCHEDULED":
            # Re-activate queue for next scheduled repeat round if upcoming slot exists
            if initial_next and initial_next > (now_utc - timedelta(seconds=15)):
                setattr(active_q, "status", "Queued")
                setattr(active_q, "scheduled_time", initial_next)
                setattr(active_q, "played_at", None)
                db.commit()
        elif ann_status_str.upper() == "SCHEDULED" and active_q:
            setattr(active_q, "status", "Queued")
            setattr(active_q, "scheduled_time", sched_time_target or now_utc)
            setattr(active_q, "played_at", None)
            db.commit()

    logger.info(
        f"🔁 Repeat schedule configured for Announcement #{announcement_id} "
        f"({schedule.repeat_mode} every {schedule.interval_minutes}m, max: {schedule.max_repeats}, next: {schedule.next_repeat_at})"
    )
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
        return 300, 3, "HIGH"
    elif "LOW" in prio_str or any(
        w in combined for w in ["lost and found", "lost & found", "lost item", "found item", "lost", "found", "canteen", "maintenance", "bus timing", "reminder"]
    ):
        return 100, 3, "LOW"
    else:  # NORMAL or MEDIUM (sports, volleyball, events, cultural, hackathons)
        return 200, 3, "MEDIUM"


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

        # Check if the emergency notice is actually in the speaker queue in an active state today
        from app.models.speaker_queue import SpeakerQueue
        active_q = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.announcement_id == sched.announcement_id,
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
            )
            .first()
        )
        if not active_q and getattr(sched, "total_played_count", 0) > 0:
            # If the emergency announcement was already played and is not actively queued, don't lock down
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
) -> Dict[str, Any]:
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
    else:
        # If no emergency schedule is active, ensure any notices paused during a previous emergency
        # are safely restored to "Queued" so playback proceeds normally!
        # Not while a one-off emergency is still on the speaker: they resume once it has finished.
        from app.services.hardware_speaker_service import is_emergency_announcement, restore_paused_queue_items
        emergency_on_air = any(
            is_emergency_announcement(q.announcement)
            for q in db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"])).all()
        )
        if not emergency_on_air:
            restore_paused_queue_items(db)

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

        prio_weight, default_reps, prio_tier = get_notice_priority_info(ann)
        is_em = (prio_tier == "EMERGENCY")
        if is_em:
            has_active_emergency_scheduled = True

        rep_mode = getattr(sched, "repeat_mode", "BREAK_SLOTS") or "BREAK_SLOTS"

        # Case A: INTERVAL Repeat Mode
        if rep_mode == "INTERVAL":
            if has_active_emergency_scheduled and not is_em:
                skipped.append({
                    "announcement_id": sched.announcement_id,
                    "slot": "INTERVAL",
                    "reason": "Suppressed by active Emergency Broadcast Override",
                })
                continue

            max_reps = getattr(sched, "max_repeats", 3) or 3
            if max_reps > 0 and sched.total_played_count >= max_reps:
                sched.is_active = False
                db.commit()
                continue

            is_due = False
            if sched.next_repeat_at:
                if simulated_time_str or simulated_date_str:
                    try:
                        sim_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
                        is_due = (sim_dt >= sched.next_repeat_at)
                    except Exception:
                        is_due = True
                else:
                    is_due = (utc_now >= sched.next_repeat_at)
            else:
                is_due = True

            if not is_due:
                continue

            active_q = (
                db.query(SpeakerQueue)
                .filter(
                    SpeakerQueue.announcement_id == sched.announcement_id,
                    SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
                )
                .first()
            )
            if active_q and active_q.status == "Playing":
                curr_played_at = getattr(active_q, "played_at", None)
                curr_dur = getattr(active_q, "duration_seconds", 15) or 15
                if curr_played_at and (utc_now - curr_played_at).total_seconds() < curr_dur and not simulated_time_str:
                    continue

            candidates.append({
                "sched": sched,
                "ann": ann,
                "slot_name": f"INTERVAL_{sched.interval_minutes}M",
                "prefix_key": f"{sched.announcement_id}:INTERVAL:{date_str}",
                "weight": prio_weight,
                "max_repeats": max_reps,
                "tier": prio_tier,
                "times_played_today": sched.total_played_count,
                "is_emergency": is_em,
                "created_at": getattr(ann, "created_at", None) or datetime.min,
            })
            continue

        # Case B: BREAK_SLOTS or CUSTOM Window Mode
        matched_slots = is_slot_active_at_time(sched, time_str, active_standard_slots)

        if not matched_slots:
            continue

        # If an emergency broadcast override is active, strictly skip and suppress all non-emergency notices!
        if has_active_emergency_scheduled and not is_em:
            for slot_name in matched_slots:
                skipped.append({
                    "announcement_id": sched.announcement_id,
                    "slot": slot_name,
                    "reason": "Suppressed by active Emergency Broadcast Override (e.g. Earthquake/Evacuation alert active)",
                })
            continue

        slot_max_repeats = 999999 if is_em else (sched.max_repeats if (sched.max_repeats is not None and sched.max_repeats > 0) else default_reps)

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
            if times_played_today >= slot_max_repeats:
                skipped.append({
                    "announcement_id": sched.announcement_id,
                    "slot": slot_name,
                    "reason": f"Max repeats ({times_played_today}/{slot_max_repeats}) reached for {prio_tier} priority in this slot today",
                })
                continue

            # Check if notice is currently active in the speaker queue for this slot
            active_q: Any = (
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
                if getattr(active_q, "status", None) == "Playing" and curr_played_at:
                    elapsed = (utc_now - curr_played_at).total_seconds()
                    if elapsed < curr_dur and not simulated_time_str:
                        is_currently_speaking = True

                if is_currently_speaking:
                    skipped.append({
                        "announcement_id": sched.announcement_id,
                        "slot": slot_name,
                        "reason": f"Already actively broadcasting in speaker queue (status: {getattr(active_q, 'status', None)})",
                    })
                    continue

                if times_played_today > 0:
                    skipped.append({
                        "announcement_id": sched.announcement_id,
                        "slot": slot_name,
                        "reason": f"Already active in speaker queue rotation (status: {getattr(active_q, 'status', None)})",
                    })
                    continue
                elif getattr(active_q, "status", None) == "Playing":
                    # Item was left Playing from an earlier broadcast; mark completed so new slot begins fresh
                    setattr(active_q, "status", "Completed")
                    db.commit()

            candidates.append({
                "sched": sched,
                "ann": ann,
                "slot_name": slot_name,
                "prefix_key": prefix_key,
                "weight": prio_weight,
                "max_repeats": slot_max_repeats,
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
        sched.last_repeat_at = utc_now

        if getattr(sched, "repeat_mode", "INTERVAL") == "INTERVAL":
            sched.next_repeat_at = utc_now + timedelta(minutes=sched.interval_minutes)
            if sched.max_repeats > 0 and sched.total_played_count >= sched.max_repeats:
                sched.is_active = False

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
            sched_ist = sched_time
            try:
                sched_ist = sched_time + timedelta(hours=5, minutes=30)
                sched_time_candidates.append(sched_ist.strftime("%H:%M"))
            except Exception:
                pass

            # CRITICAL: Only evaluate slot cutoff TTL expiration if the scheduled date is TODAY or in the past in campus IST!
            # If the item is scheduled for tomorrow or a future date, it must NEVER be marked expired today!
            if sched_ist.date() > ist_now.date():
                continue

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
