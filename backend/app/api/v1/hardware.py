from typing import Any, List, Optional
import re
import threading
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

from app.services.speaker_playback import serialized, try_serialized

from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.models.announcement_category import AnnouncementCategory
from app.core.enums.announcement import AnnouncementPriority, AnnouncementStatus, EmergencyLevel
from app.core.emergency_utils import is_emergency_announcement
from app.repositories.hardware_repository import (
    add_to_speaker_queue,
    create_speaker_node,
    delete_speaker_node,
    delete_speaker_queue_item,
    get_all_speaker_nodes,
    get_speaker_node_by_id,
    get_speaker_node_by_mac,
    get_speaker_queue,
    reorder_speaker_queue,
    update_queue_item_status,
    update_speaker_node,
    update_speaker_node_heartbeat,
)


from app.schemas.hardware import (
    EmergencyOverrideRequest,
    EnqueueAnnouncementRequest,
    ReorderQueueRequest,
    SpeakerBroadcastRequest,
    SpeakerControlRequest,
    SpeakerNodeCreate,
    SpeakerNodeHeartbeat,
    SpeakerNodeResponse,
    SpeakerNodeUpdate,
    SpeakerQueueItemResponse,
)
from app.services.hardware_speaker_service import (
    broadcast_announcement_to_speaker,
    dispatch_queue_action_to_speakers,
    send_node_control_command,
)
from app.repositories.announcement_repository import get_announcement_by_id

router = APIRouter(
    prefix="/hardware",
    tags=["Hardware & Smart Speakers"],
)


@router.delete("/speakers/{id}")
def remove_speaker_node(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin")
    ),
):
    success = delete_speaker_node(db, id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker node not found.")
    return {"message": "Speaker node deleted successfully", "id": id}


@router.delete("/queue/{id}")
def remove_speaker_queue_item(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")
    ),
):
    success = delete_speaker_queue_item(db, id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")
    return {"message": "Queue item deleted successfully", "id": id}


@router.get("/speakers", response_model=List[SpeakerNodeResponse])
def list_speaker_nodes(
    department_id: Optional[int] = None,
    zone: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    nodes = get_all_speaker_nodes(db=db, department_id=department_id, zone=zone, status=status)
    res = []
    for n in nodes:
        node_dict = {
            "id": n.id,
            "name": n.name,
            "mac_address": n.mac_address,
            "ip_address": n.ip_address,
            "department_id": n.department_id,
            "department_name": n.department.name if n.department else None,
            "zone": n.zone,
            "volume": n.volume,
            "status": n.status,
            "cpu_usage": n.cpu_usage,
            "memory_usage": n.memory_usage,
            "disk_space": n.disk_space,
            "last_heartbeat": n.last_heartbeat,
            "is_active": n.is_active,
            "created_at": n.created_at,
            "updated_at": n.updated_at,
        }
        res.append(node_dict)
    return res


@router.post("/speakers/register", response_model=SpeakerNodeResponse, status_code=status.HTTP_201_CREATED)
def register_speaker_node(
    node_in: SpeakerNodeCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    existing = get_speaker_node_by_mac(db, node_in.mac_address)
    if existing:
        # Idempotent registration / reconnect for hardware nodes
        if node_in.name:
            setattr(existing, "name", node_in.name)
        if node_in.ip_address:
            setattr(existing, "ip_address", node_in.ip_address)
        if node_in.zone:
            setattr(existing, "zone", node_in.zone)
        if node_in.volume is not None:
            setattr(existing, "volume", node_in.volume)
        if node_in.department_id is not None:
            setattr(existing, "department_id", node_in.department_id)
        setattr(existing, "status", "ONLINE")
        setattr(existing, "last_heartbeat", datetime.now(timezone.utc).replace(tzinfo=None))
        db.commit()
        db.refresh(existing)
        return existing
def _format_utc_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).isoformat()
    return dt.replace(tzinfo=timezone.utc).isoformat()


_DAILY_FEED_TTL_SECONDS = 10.0
_DAILY_FEED_CACHE: dict = {"key": None, "at": 0.0, "data": []}
_SUMMARY_JOBS: set = set()


def _summarize_in_background(announcement_id: int) -> None:
    """Generate and save a missing AI summary once, outside the request (heartbeat) path."""
    if announcement_id in _SUMMARY_JOBS:
        return
    _SUMMARY_JOBS.add(announcement_id)

    def _job():
        from app.db.database import SessionLocal
        from app.services.ai_service import AIService
        try:
            with SessionLocal() as s:
                ann = s.query(Announcement).filter(Announcement.id == announcement_id).first()
                if ann and ann.description:
                    real_sum = AIService.summarize(ann.description)
                    if real_sum and len(real_sum.strip()) > 10:
                        ann.ai_summary = real_sum.strip()
                        s.commit()
                        _DAILY_FEED_CACHE["key"] = None  # show the new summary on the next heartbeat
        except Exception as exc:
            logger.debug(f"Background summary for #{announcement_id} note: {exc}")

    threading.Thread(target=_job, daemon=True, name=f"FeedSummary_{announcement_id}").start()


def get_display_feed_data(db: Session, mac_address: Optional[str] = None) -> dict:
    """
    Constructs live display payload for ESP32 OLED/LED screens:
    1. active_notice: currently playing announcement through the speaker queue.
    2. daily_notices: important active published notices of the day from the app when idle.
    """
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    try:
        try_serialized(auto_advance_speaker_queue, db)
    except Exception:
        pass

    clean_mac = (mac_address or "").upper().strip()
    if clean_mac in ("00:00:00:00:00:00", "00-00-00-00-00-00", ""):
        clean_mac = "D4:F3:2D:22:2A:CD"

    # 1. Active playing announcement in speaker queue
    active_playing = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status == "Playing")
        .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
        .first()
    )
    active_dict = None
    if active_playing and active_playing.announcement:
        ann = active_playing.announcement
        target_mac = active_playing.speaker_node.mac_address if active_playing.speaker_node else "ALL"
        target_mac_str = str(target_mac).upper().strip() if target_mac else "ALL"
        is_targeted = (
            not mac_address
            or target_mac_str in ("ALL", "NONE", "")
            or target_mac_str == clean_mac
            or (clean_mac in ("00:00:00:00:00:00", "D4:F3:2D:22:2A:CD") and target_mac_str in ("00:00:00:00:00:00", "D4:F3:2D:22:2A:CD"))
        )
        if is_targeted:
            is_emergency = is_emergency_announcement(ann)
            dept_name = ann.creator.department.name if (ann.creator and ann.creator.department) else "College-Wide"
            p_val = "EMERGENCY" if is_emergency else (ann.priority.value if hasattr(ann.priority, "value") else str(ann.priority))
            active_content = (ann.ai_summary or ann.description or "").strip()
            for prefix in ("OFFICIAL CIRCULAR:", "CIRCULAR:", "NOTICE:", "ANNOUNCEMENT:", "SUMMARY:"):
                if active_content.upper().startswith(prefix):
                    active_content = active_content[len(prefix):].strip()
            active_content = re.sub(r'[*_#`]', '', active_content).strip()
            active_content = re.sub(r'^(summary|notice)\s*[:\-–]\s*', '', active_content, flags=re.IGNORECASE).strip()
            active_content = re.sub(r'\s+', ' ', active_content)[:1500]
            active_title = ann.title or "Campus Notice"
            for prefix in ("OFFICIAL CIRCULAR:", "CIRCULAR:", "NOTICE:", "ANNOUNCEMENT:"):
                while active_title.upper().startswith(prefix):
                    active_title = active_title[len(prefix):].strip()
            active_title = re.sub(r'[*_#`]', '', active_title).strip() or ann.title

            from app.services.speaker_playback import signed_stream_query
            from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
            sched_rec = db.query(AnnouncementRepeatSchedule).filter(
                AnnouncementRepeatSchedule.announcement_id == ann.id,
                AnnouncementRepeatSchedule.is_active == True,
            ).first()
            active_round = (sched_rec.total_played_count + 1) if sched_rec else 1

            active_dict = {
                "is_playing": True,
                "id": ann.id,
                "queue_id": active_playing.id,
                "repeat_round": active_round,
                "played_at": active_playing.played_at.isoformat() if active_playing.played_at else None,
                "title": active_title,
                "content": active_content,
                "priority": p_val,
                "is_emergency": is_emergency,
                "department": dept_name,
                "duration_seconds": active_playing.duration_seconds or 15,
                "target_node_mac": target_mac,
                "audio_url": f"/api/v1/announcements/{ann.id}/audio/stream?audio_format=wav&include_chime=false&{signed_stream_query(active_playing.id)}",
            }

    # 2. Daily important announcements for idle display ticker (strictly today's notices in IST)
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    now_ist = now_utc + timedelta(hours=5, minutes=30)

    # Heartbeats arrive every 0.8s and this list is the same for every speaker: rebuild it at
    # most every 10s instead of re-querying today's notices on every heartbeat.
    cache_key = now_ist.date().isoformat()
    cached = _DAILY_FEED_CACHE
    if cached["key"] == cache_key and time.monotonic() - cached["at"] < _DAILY_FEED_TTL_SECONDS:
        return {"status": "success", "active_notice": active_dict, "daily_notices": cached["data"]}
    start_of_today_ist = datetime(now_ist.year, now_ist.month, now_ist.day)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)

    active_statuses = [
        AnnouncementStatus.PUBLISHED,
        AnnouncementStatus.SCHEDULED,
    ]

    # Query exclusively notices created/scheduled for TODAY in campus IST timezone
    published_notices = (
        db.query(Announcement)
        .filter(
            Announcement.status.in_(active_statuses),
            Announcement.created_at >= start_of_today_utc,
        )
        .order_by(Announcement.created_at.desc())
        .limit(10)
        .all()
    )

    def priority_sort_key(a: Announcement) -> int:
        p_str = (a.priority.value if hasattr(a.priority, "value") else str(a.priority)).upper()
        if "EMERGENCY" in p_str:
            return 0
        if "URGENT" in p_str:
            return 1
        if "HIGH" in p_str:
            return 2
        return 3

    sorted_notices = sorted(published_notices, key=priority_sort_key)
    daily_list = []
    for n in sorted_notices:
        dept_name = n.creator.department.name if (n.creator and n.creator.department) else "College-Wide"
        p_str = n.priority.value if hasattr(n.priority, "value") else str(n.priority)
        cat_name = n.category.name if n.category else "Notice"
        summary_raw = (n.ai_summary or "").strip()
        title_lower = (n.title or "").strip().lower()
        # Detect placeholder title-echoes e.g. "Summary: Hackathon" or missing summaries
        is_placeholder = (
            not summary_raw
            or len(summary_raw) < 15
            or summary_raw.lower() in (f"summary: {title_lower}", title_lower, f"notice: {title_lower}")
            or (summary_raw.lower().startswith("summary:") and len(summary_raw.split()) <= 6)
        )
        if is_placeholder and n.description and len(n.description.strip()) > 10:
            # Never block a speaker heartbeat on an AI call: summarize in the background,
            # show the description until the summary is saved.
            _summarize_in_background(n.id)
            summary_raw = ""

        if not summary_raw:
            summary_raw = (n.description or n.title or "").strip()

        for prefix in ("OFFICIAL CIRCULAR:", "CIRCULAR:", "NOTICE:", "ANNOUNCEMENT:", "SUMMARY:"):
            if summary_raw.upper().startswith(prefix):
                summary_raw = summary_raw[len(prefix):].strip()
        summary_clean = re.sub(r'[*_#`]', '', summary_raw).strip()
        summary_clean = re.sub(r'^(summary|notice)\s*[:\-–]\s*', '', summary_clean, flags=re.IGNORECASE).strip()
        summary_clean = re.sub(r'\s+', ' ', summary_clean)[:800]
        n_title = (n.title or "Campus Notice").strip()
        for prefix in ("OFFICIAL CIRCULAR:", "CIRCULAR:", "NOTICE:", "ANNOUNCEMENT:"):
            while n_title.upper().startswith(prefix):
                n_title = n_title[len(prefix):].strip()
        n_title = re.sub(r'[*_#`]', '', n_title).strip() or (n.title or "Campus Notice")

        daily_list.append({
            "id": n.id,
            "title": n_title,
            "summary": summary_clean,
            "priority": p_str,
            "department": dept_name,
            "category": cat_name,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        })

    _DAILY_FEED_CACHE.update({"key": cache_key, "at": time.monotonic(), "data": daily_list})

    # Return authentic published announcements (empty list when none are published)
    return {
        "status": "success",
        "active_notice": active_dict,
        "daily_notices": daily_list,
    }


@router.get("/speakers/display-feed", summary="Get Live Display Feed for ESP32 Screens & LEDs")
def get_speaker_display_feed(
    mac_address: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns active playing notice (when speaker is broadcasting) and important daily notices (when idle)
    for connected ESP32 OLED/LED displays and campus ticker boards.
    """
    return get_display_feed_data(db, mac_address)


@router.get("/speakers/{id}", response_model=SpeakerNodeResponse)
def get_speaker_node_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    node = get_speaker_node_by_id(db, id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker node not found.")
    return {
        "id": node.id,
        "name": node.name,
        "mac_address": node.mac_address,
        "ip_address": node.ip_address,
        "department_id": node.department_id,
        "department_name": node.department.name if node.department else None,
        "zone": node.zone,
        "volume": node.volume,
        "status": node.status,
        "cpu_usage": node.cpu_usage,
        "memory_usage": node.memory_usage,
        "disk_space": node.disk_space,
        "last_heartbeat": node.last_heartbeat,
        "is_active": node.is_active,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
    }


@router.put("/speakers/{id}", response_model=SpeakerNodeResponse)
def update_speaker_node_settings(
    id: int,
    update_in: SpeakerNodeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")
    ),
):
    node = get_speaker_node_by_id(db, id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker node not found.")
    updated = update_speaker_node(db=db, node=node, update_data=update_in)
    return {
        "id": updated.id,
        "name": updated.name,
        "mac_address": updated.mac_address,
        "ip_address": updated.ip_address,
        "department_id": updated.department_id,
        "department_name": updated.department.name if updated.department else None,
        "zone": updated.zone,
        "volume": updated.volume,
        "status": updated.status,
        "cpu_usage": updated.cpu_usage,
        "memory_usage": updated.memory_usage,
        "disk_space": updated.disk_space,
        "last_heartbeat": updated.last_heartbeat,
        "is_active": updated.is_active,
        "created_at": updated.created_at,
        "updated_at": updated.updated_at,
    }


@router.post("/speakers/{id}/broadcast")
async def trigger_speaker_broadcast(
    id: int,
    request_in: SpeakerBroadcastRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")),
):
    node = get_speaker_node_by_id(db, id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker node not found.")

    announcement = get_announcement_by_id(db, request_in.announcement_id)
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found.")

    base_url = str(request.base_url).rstrip("/")
    result = await broadcast_announcement_to_speaker(
        db=db,
        announcement_id=int(getattr(announcement, "id")),
        title=str(announcement.title),
        content=str(announcement.description),
        department_code=str(node.department.code) if node.department else "ALL",
        zone=str(node.zone),
        is_emergency=False,
        base_url=base_url,
    )
    return result


@router.post("/speakers/override")
async def trigger_emergency_override(
    override_in: EmergencyOverrideRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")),
):
    try:
        base_url = str(request.base_url).rstrip("/")

        # Persist a real emergency announcement in the database so it appears in audit & notices
        from app.models.announcement_category import AnnouncementCategory
        cat = db.query(AnnouncementCategory).filter(AnnouncementCategory.name == "Emergency").first()
        if not cat:
            cat = AnnouncementCategory(name="Emergency", description="Emergency Campus Advisories")
            db.add(cat)
            db.commit()
            db.refresh(cat)

        creator_id = current_user.id if (current_user and hasattr(current_user, 'id') and current_user.id) else 1
        db_user = db.query(User).filter(User.id == creator_id).first()
        if not db_user:
            first_u = db.query(User).first()
            if first_u:
                creator_id = first_u.id
            else:
                from app.models.role import Role
                dev_role = db.query(Role).first()
                if not dev_role:
                    dev_role = Role(name="Dev Admin")
                    db.add(dev_role)
                    db.commit()
                    db.refresh(dev_role)
                fallback_u = User(
                    full_name="Emergency System Operator",
                    username="emergency_operator",
                    official_email="system@echosphere.edu",
                    role_id=dev_role.id,
                    password_hash="system_hash"
                )
                db.add(fallback_u)
                db.commit()
                db.refresh(fallback_u)
                creator_id = fallback_u.id

        emergency_ann = db.query(Announcement).filter(
            Announcement.title == override_in.title,
            Announcement.emergency_level == EmergencyLevel.EMERGENCY
        ).first()

        if not emergency_ann:
            emergency_ann = Announcement(
                title=override_in.title,
                description=override_in.message,
                status=AnnouncementStatus.PUBLISHED,
                priority=AnnouncementPriority.HIGH,
                emergency_level=EmergencyLevel.EMERGENCY,
                created_by=creator_id,
                category_id=cat.id,
            )
            db.add(emergency_ann)
            db.commit()
            db.refresh(emergency_ann)



        # Dispatch emergency notifications to all campus users
        try:
            from app.services.announcement_service import dispatch_announcement_notifications_and_deliveries
            dispatch_announcement_notifications_and_deliveries(
                db=db,
                announcement=emergency_ann,
                deliver_in_app=True,
                deliver_push=True,
                deliver_speaker=True,
                target_audience="Entire College",
                current_user=current_user,
            )
        except Exception as notif_err:
            print(f"Warning: Failed to dispatch emergency notifications: {notif_err}")

        result = await broadcast_announcement_to_speaker(
            db=db,
            announcement_id=int(getattr(emergency_ann, "id")),
            title=override_in.title,
            content=override_in.message,
            department_code="ALL",
            zone=override_in.zone or "College-Wide",
            is_emergency=True,
            base_url=base_url,
        )
        return {
            "status": "EMERGENCY_OVERRIDE_ACTIVATED",
            "message": override_in.message,
            "announcement_id": emergency_ann.id,
            "details": result,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency override error: {str(e)}"
        )


@router.post("/speakers/{id}/control")
def send_control_command(
    id: int,
    control_in: SpeakerControlRequest,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    return send_node_control_command(
        db=db,
        speaker_node_id=id,
        command=control_in.command,
        volume=control_in.volume,
        announcement_id=control_in.announcement_id,
    )

@router.post("/speakers/heartbeat")
def receive_node_heartbeat(
    heartbeat_in: SpeakerNodeHeartbeat,
    db: Session = Depends(get_db),
):
    node = update_speaker_node_heartbeat(db=db, heartbeat=heartbeat_in)
    from app.services.hardware_speaker_service import auto_advance_speaker_queue, get_pending_commands_for_mac
    try:
        try_serialized(auto_advance_speaker_queue, db)
    except Exception:
        pass
    cmds = get_pending_commands_for_mac(str(node.mac_address), db=db)
    feed = get_display_feed_data(db, str(node.mac_address))
    return {
        "status": "success",
        "node_id": node.id,
        "mac_address": node.mac_address,
        "pending_commands": cmds,
        "active_notice": feed.get("active_notice"),
        "daily_notices": feed.get("daily_notices", []),
    }


@router.get("/speakers/poll/{mac_address}", summary="Poll Pending Node Commands")
def poll_pending_node_commands(
    mac_address: str,
    db: Session = Depends(get_db),
):
    """
    Allows simulated speaker nodes to poll for pending control and audio commands over REST.
    """
    from app.services.hardware_speaker_service import auto_advance_speaker_queue, get_pending_commands_for_mac
    try:
        try_serialized(auto_advance_speaker_queue, db)
    except Exception:
        pass
    cmds = get_pending_commands_for_mac(mac_address, db=db)
    return {
        "mac_address": mac_address,
        "pending_commands": cmds,
    }


def _speaker_confirmed(item) -> bool:
    c, p = getattr(item, "speaker_confirmed_at", None), getattr(item, "played_at", None)
    return bool(getattr(item, "status", None) == "Playing" and c and p and c >= p)


def _speaker_elapsed(item) -> Optional[float]:
    if not _speaker_confirmed(item):
        return None
    elapsed = (datetime.now(timezone.utc).replace(tzinfo=None) - item.speaker_confirmed_at).total_seconds()
    return round(max(0.0, elapsed), 2)


@router.get("/queue")
def fetch_speaker_queue(
    request: Request,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    from app.services.repeat_schedule_service import evaluate_and_dispatch_repeat_slots
    try:
        evaluate_and_dispatch_repeat_slots(db)
        try_serialized(auto_advance_speaker_queue, db)
    except Exception:
        pass

    # Clean up stale items from previous dates (before today in campus IST) that have no active repeat schedule
    from datetime import timedelta, timezone
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    start_of_today_ist = datetime(now_ist.year, now_ist.month, now_ist.day)
    start_of_today_utc = start_of_today_ist - timedelta(hours=5, minutes=30)

    try:
        from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
        stale_past_items = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.status.in_(["Playing", "Paused", "Held", "Next in Queue", "Queued"]),
                SpeakerQueue.scheduled_time < start_of_today_utc,
            )
            .all()
        )
        for stale_item in stale_past_items:
            s_sched = (
                db.query(AnnouncementRepeatSchedule)
                .filter(
                    AnnouncementRepeatSchedule.announcement_id == stale_item.announcement_id,
                    AnnouncementRepeatSchedule.is_active == True,
                )
                .first()
            ) if stale_item.announcement_id else None
            if not s_sched:
                stale_item.status = "Completed"
        if stale_past_items:
            db.commit()
    except Exception:
        pass

    if status is None:
        queue_items = (
            db.query(SpeakerQueue)
            .filter(SpeakerQueue.status.in_(["Playing", "Paused", "Held", "Next in Queue", "Queued"]))
            .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
            .all()
        )
    else:
        queue_items = get_speaker_queue(db=db, status=status)
    base_url = str(request.base_url).rstrip("/")
    result = []
    from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
    from app.services.repeat_schedule_service import get_notice_priority_info

    for item in queue_items:
        ann = item.announcement
        target_node = item.speaker_node
        node_name = target_node.name if target_node else "All Nodes (College-Wide)"
        node_status = target_node.status if target_node else None
        node_zone = target_node.zone if target_node else "College-Wide"
        node_mac = target_node.mac_address if target_node else None

        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == item.announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        ) if item.announcement_id else None

        has_repeat_active = False
        max_repeats = 1
        sched_dict = None

        if sched and sched.is_active:
            prio_weight, max_reps_val, prio_tier = get_notice_priority_info(ann) if ann else (200, 2, "MEDIUM")
            has_repeat_active = True
            max_repeats = sched.max_repeats if getattr(sched, "max_repeats", None) is not None else max_reps_val
            sched_dict = {
                "id": sched.id,
                "announcement_id": sched.announcement_id,
                "repeat_mode": getattr(sched, "repeat_mode", "INTERVAL"),
                "interval_minutes": getattr(sched, "interval_minutes", 15),
                "max_repeats": sched.max_repeats,
                "play_on_publish": getattr(sched, "play_on_publish", True),
                "next_repeat_at": _format_utc_iso(sched.next_repeat_at) if sched else None,
                "last_repeat_at": _format_utc_iso(sched.last_repeat_at) if sched else None,
                "selected_slots": sched.selected_slots,
                "custom_start_time": sched.custom_start_time,
                "custom_end_time": sched.custom_end_time,
                "target_scope": sched.target_scope,
                "target_node_id": sched.target_node_id,
                "total_played_count": sched.total_played_count,
                "is_active": sched.is_active,
            }
        else:
            prio_tier = (ann.priority.value if hasattr(ann.priority, "value") else str(ann.priority)) if ann else "NORMAL"

        repeat_round = (sched.total_played_count + 1) if sched else 1
        next_rep_iso = _format_utc_iso(sched.next_repeat_at) if (sched and sched.next_repeat_at) else _format_utc_iso(item.scheduled_time)

        result.append({
            "id": item.id,
            "announcement_id": item.announcement_id,
            "title": ann.title if ann else "Announcement",
            "description": ann.description if ann else "",
            "content": ann.description if ann else "",
            "department": ann.creator.department.name if (ann and getattr(ann, 'creator', None) and getattr(ann.creator, 'department', None)) else "College-Wide",
            "priority": prio_tier,
            "type": "AI Speech",
            "status": item.status,
            "queue_position": item.queue_position,
            "scheduled_time": _format_utc_iso(item.scheduled_time),
            "played_at": _format_utc_iso(item.played_at),
            "duration_seconds": getattr(item, "duration_seconds", 15) or 15,
            # Speaker-confirmed playback: elapsed is computed on the server so client clocks don't matter
            "speaker_confirmed": _speaker_confirmed(item),
            "speaker_elapsed_seconds": _speaker_elapsed(item),
            "audio_url": f"{base_url}/api/v1/announcements/{item.announcement_id}/audio/stream",
            "speaker_node_id": item.speaker_node_id,
            "speaker_node_mac": node_mac,
            "speaker_node_name": node_name,
            "speaker_node_status": node_status,
            "speaker_node_zone": node_zone,
            "repeat_schedule": sched_dict,
            "has_repeat": has_repeat_active,
            "is_repeat": has_repeat_active and getattr(sched, "total_played_count", 0) > 0,
            "repeat_mode": getattr(sched, "repeat_mode", "INTERVAL") if sched else None,
            "repeat_round": repeat_round,
            "current_round": getattr(sched, "total_played_count", 0) if sched else 0,
            "max_repeats": max_repeats,
            "interval_minutes": getattr(sched, "interval_minutes", 15) if sched else None,
            "next_repeat_at": next_rep_iso,
        })
    return result


@router.post("/queue/add")
def enqueue_speaker_announcement(
    enqueue_in: EnqueueAnnouncementRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")),
):
    ann = get_announcement_by_id(db, enqueue_in.announcement_id)
    req_title = enqueue_in.title
    req_desc = enqueue_in.content or enqueue_in.description

    if not ann:
        # Resilient fallback: ensure announcement exists in DB so it can play on hardware
        cat = db.query(AnnouncementCategory).filter(AnnouncementCategory.name == "General").first()
        if not cat:
            cat = db.query(AnnouncementCategory).filter(AnnouncementCategory.id != 1).first()
        cat_id = cat.id if cat else 12
        creator_id = current_user.id if (current_user and hasattr(current_user, 'id') and current_user.id) else 1
        if not db.query(User).filter(User.id == creator_id).first():
            u = db.query(User).first()
            creator_id = u.id if u else 1

        ann = Announcement(
            id=enqueue_in.announcement_id,
            title=req_title or f"Campus Notice #{enqueue_in.announcement_id}",
            description=req_desc or "Official campus voice announcement broadcast.",
            status=AnnouncementStatus.PUBLISHED,
            priority=AnnouncementPriority.NORMAL,
            emergency_level=EmergencyLevel.NORMAL,
            created_by=creator_id,
            category_id=cat_id,
            speaker_voice="female",
        )
        try:
            db.add(ann)
            db.commit()
            db.refresh(ann)
        except Exception:
            db.rollback()
            ann = db.query(Announcement).first()

    if not ann:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found.")

    if (req_title or req_desc) and ("Campus Voice Broadcast" in str(ann.title) or str(ann.description) == "Official campus voice announcement broadcast."):
        # Upgrade any placeholder notice with real user content
        if req_title:
            setattr(ann, "title", req_title)
        if req_desc:
            setattr(ann, "description", req_desc)
        try:
            db.commit()
            db.refresh(ann)
        except Exception:
            db.rollback()

    from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
    dept_code = "ALL"
    creator = getattr(ann, "creator", None)
    if creator and hasattr(creator, "department") and creator.department:
        dept_code = creator.department.code

    base_url = str(request.base_url).rstrip("/")
    is_emerg = is_emergency_announcement(ann)
    target_node_id = enqueue_in.speaker_node_id if (enqueue_in.speaker_node_id and enqueue_in.speaker_node_id > 0) else None
    scheduled_time = getattr(enqueue_in, 'scheduled_time', None) or getattr(ann, 'scheduled_at', None)
    result = enqueue_and_broadcast_announcement(
        db=db,
        announcement_id=int(getattr(ann, "id")),
        title=str(ann.title),
        content=str(ann.description),
        department_code=dept_code,
        zone="College-Wide",
        is_emergency=is_emerg,
        speaker_node_id=target_node_id,
        scheduled_time=scheduled_time,
        speaker_voice=getattr(ann, 'speaker_voice', 'female') or 'female',
        base_url=base_url,
        force_requeue=True,
    )
    return {
        "status": "success",
        "announcement_id": getattr(ann, "id"),
        "queue_position": result.get("queue_position", 1),
        "item_status": result.get("queue_status", "Playing" if result.get("is_playing") else "Queued"),
        "is_playing": result.get("is_playing", False),
        "details": result,
    }


@router.post("/queue/reorder")
def reorder_speaker_queue_items(
    reorder_in: ReorderQueueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")),
):
    updated_items = reorder_speaker_queue(db=db, ordered_ids=reorder_in.queue_ids)
    return {
        "status": "success",
        "reordered_count": len(updated_items),
        "queue_ids": [item.id for item in updated_items],
    }


@router.post("/queue/{id}/action")
@router.put("/queue/{id}/action")
@router.post("/speaker-queue/{id}/action")
@router.put("/speaker-queue/{id}/status")
@router.post("/speaker-queue/{id}/status")
@serialized
def update_queue_action(
    id: int,
    request: Request,
    action: str = "complete",
    target: str = "queue",
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    # target=announcement: {id} is an announcement id (the web app); otherwise a queue id (the ESP32).
    # The announcement-id fallback stays only for 'complete', which old firmware may send with an announcement id.
    if target.lower() == "announcement":
        item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == id).order_by(SpeakerQueue.id.desc()).first()
    else:
        item = db.query(SpeakerQueue).filter(SpeakerQueue.id == id).first()
        if not item and action.lower().strip() == "complete":
            item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == id).order_by(SpeakerQueue.id.desc()).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")

    base_url = str(request.base_url).rstrip("/")
    act_clean = action.lower().strip()

    # Only the speaker's own 'complete' callback is anonymous; every user command needs staff login
    if act_clean != "complete":
        staff_roles = {"dev admin", "developer", "college admin", "admin", "principal", "hod", "teacher"}
        role_name = str(getattr(getattr(current_user, "role", None), "name", "") or "").lower()
        if current_user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required.")
        if role_name not in staff_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to control the speaker queue.")

    if act_clean == "complete":
        if getattr(item, "status", None) != "Playing":
            logger.info(f"Notice #{item.id} action=complete ignored - status is already '{getattr(item, 'status', None)}'")
            return {
                "status": "success",
                "queue_id": item.id,
                "action": action,
                "new_status": getattr(item, "status", None),
                "message": f"Notice was already advanced (status: {getattr(item, 'status', None)})",
            }

        ann = item.announcement
        is_emerg = is_emergency_announcement(ann)

        from app.services.repeat_schedule_service import (
            get_current_ist_datetime,
            get_active_break_slots,
            is_slot_active_at_time,
        )
        from app.models.announcement_repeat_schedule import (
            AnnouncementRepeatSchedule,
            RepeatSlotExecutionLog,
        )

        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == item.announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        ) if item.announcement_id else None

        ist_now = get_current_ist_datetime()
        time_str = ist_now.strftime("%H:%M")
        date_str = ist_now.strftime("%Y-%m-%d")
        active_slots = get_active_break_slots(time_str)
        matched = is_slot_active_at_time(sched, time_str, active_slots) if sched else []
        is_slot_active = bool(matched)

        from app.services.repeat_schedule_service import get_notice_priority_info
        prio_weight, max_reps_limit, prio_tier = get_notice_priority_info(ann) if ann else (200, 2, "MEDIUM")

        if is_emerg and is_slot_active and sched and sched.total_played_count < max_reps_limit:
            # Emergency notices loop continuously ONLY if repeat schedule is configured and slot is active
            sched.total_played_count += 1
            item.status = "Playing"
            item.played_at = datetime.now(timezone.utc).replace(tzinfo=None)
            db.commit()
            return {"status": "success", "queue_id": item.id, "action": action, "new_status": "Playing", "message": "Emergency continuous loop"}

        rep_mode = getattr(sched, "repeat_mode", "INTERVAL") if sched else "INTERVAL"
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        has_repeats_left = False
        next_rep_time = None
        slot_name = "REPEAT_INTERVAL"

        if sched and sched.is_active:
            max_limit = sched.max_repeats if getattr(sched, "max_repeats", None) is not None else 3
            if max_limit <= 0:
                max_limit = 999999

            sched.total_played_count += 1
            sched.last_repeat_at = now

            if sched.total_played_count < max_limit:
                if rep_mode == "INTERVAL":
                    interval_m = getattr(sched, "interval_minutes", 15) or 15
                    next_rep_time = now + timedelta(minutes=interval_m)
                    sched.next_repeat_at = next_rep_time
                    has_repeats_left = True
                    slot_name = f"INTERVAL_{interval_m}M"
                else:
                    from app.services.repeat_schedule_service import get_next_slot_datetime, _utc_to_ist_naive
                    next_cand, cand_slot = get_next_slot_datetime(sched, _utc_to_ist_naive(now), db)
                    if next_cand:
                        next_rep_time = next_cand
                        sched.next_repeat_at = next_rep_time
                        has_repeats_left = True
                        sched.is_active = True
                        slot_name = cand_slot or "NEXT_BREAK"
                    else:
                        has_repeats_left = False
                        sched.is_active = False
            else:
                has_repeats_left = False
                sched.is_active = False

            prefix_key = f"{sched.announcement_id}:{slot_name}:{date_str}"
            target_key = f"{prefix_key}:{sched.total_played_count}"
            existing_log = db.query(RepeatSlotExecutionLog).filter(RepeatSlotExecutionLog.slot_key == target_key).first()
            if not existing_log:
                exec_log = RepeatSlotExecutionLog(
                    schedule_id=sched.id,
                    slot_key=target_key,
                    slot_name=slot_name,
                    played_at=now,
                )
                db.add(exec_log)

        if has_repeats_left and next_rep_time:
            max_pos = db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(["Queued", "Next in Queue"])).count()
            item.status = "Queued"
            item.scheduled_time = next_rep_time
            item.queue_position = max_pos + 1
            item.played_at = None
            new_status = "Queued"
        else:
            item.status = "Completed"
            new_status = "Completed"

        db.commit()
        db.refresh(item)

        from app.services.hardware_speaker_service import auto_advance_speaker_queue, restore_paused_queue_items
        # 1. Unpause and restore any preempted notices so they immediately resume for their scheduled window!
        restore_paused_queue_items(db=db, now=now)

        adv_res = None
        try:
            # Only force-advance if the completed item was the one currently Playing (or queue is idle).
            # If another notice was already transitioned to Playing, DO NOT force-advance past it!
            current_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
            should_force = (current_playing is None or current_playing.id == item.id)
            adv_res = auto_advance_speaker_queue(db, force_advance=should_force, base_url=base_url)
        except Exception as adv_e:
            pass

        try:
            from app.core.websocket_manager import ws_manager
            ws_manager.broadcast_sync({
                "event": "QUEUE_UPDATED",
                "queue_id": item.id,
                "announcement_id": item.announcement_id,
                "action": "complete",
                "status": new_status,
                "timestamp": now.isoformat(),
            })
        except Exception:
            pass

        return {
            "status": "success",
            "queue_id": item.id,
            "action": action,
            "new_status": new_status,
            "next_repeat_at": next_rep_time.isoformat() if next_rep_time else None,
            "auto_advance": adv_res,
        }

    from app.services.hardware_speaker_service import (
        HELD_STATUS,
        auto_advance_speaker_queue,
        abort_announcement_stream,
        clear_announcement_stream_abort,
    )
    from app.services.speaker_playback import cancel_pending_play_commands

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    was_playing = getattr(item, "status", None) == "Playing"
    advance_res = None
    dispatch_res = None

    if act_clean in ("pause", "hold"):
        # Pause holds the whole queue. The notice restarts from the beginning on resume:
        # a streamed notice cannot continue mid-sentence on the speaker.
        if getattr(item, "status", None) not in ("Playing", "Queued", "Next in Queue", HELD_STATUS):
            # Never revive a finished / removed notice as 'Held' (it would hold the whole queue)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Notice is not in the queue (status: {item.status}).")
        item.status = HELD_STATUS
        db.commit()
        cancel_pending_play_commands(db, item.announcement_id)
        if item.announcement_id:
            abort_announcement_stream(item.announcement_id)
        if was_playing:
            dispatch_res = dispatch_queue_action_to_speakers(db=db, queue_item=item, action="pause", base_url=base_url)
        new_status = HELD_STATUS

    elif act_clean in ("play", "resume"):
        # Playing something releases any hold; whatever was playing goes back to the queue.
        for other in db.query(SpeakerQueue).filter(
            SpeakerQueue.id != item.id,
            SpeakerQueue.status.in_(["Playing", HELD_STATUS]),
        ).all():
            other.status = "Queued"
            other.played_at = None
            other.scheduled_time = now
        item.status = "Playing"
        item.played_at = now
        item.speaker_confirmed_at = None
        item.queue_position = 1
        item.failure_reason = None
        db.commit()
        cancel_pending_play_commands(db, item.announcement_id)
        if item.announcement_id:
            clear_announcement_stream_abort(item.announcement_id)
        dispatch_res = dispatch_queue_action_to_speakers(db=db, queue_item=item, action="play", base_url=base_url)
        new_status = "Playing"

    elif act_clean in ("remove", "cancel", "stop", "skip"):
        new_status = {"remove": "Completed", "skip": "Skipped"}.get(act_clean, "Cancelled")
        item.status = new_status
        if act_clean == "remove" and item.announcement_id:
            # Removing a notice also ends its repeat schedule, otherwise the next round re-queues it
            from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
            for sched in db.query(AnnouncementRepeatSchedule).filter(
                AnnouncementRepeatSchedule.announcement_id == item.announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            ).all():
                sched.is_active = False
                sched.next_repeat_at = None
        db.commit()
        cancel_pending_play_commands(db, item.announcement_id)
        if item.announcement_id:
            abort_announcement_stream(item.announcement_id)
        if was_playing:
            dispatch_res = dispatch_queue_action_to_speakers(db=db, queue_item=item, action=act_clean, base_url=base_url)
            # Not forced: the item is no longer Playing, so a normal pass starts the next notice.
            # (Forcing would complete whatever the daemon may have just started.)
            try:
                advance_res = auto_advance_speaker_queue(db, base_url=base_url)
            except Exception as adv_e:
                logger.warning(f"Queue advance after {act_clean}: {adv_e}")

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown queue action '{action}'.")

    try:
        from app.core.websocket_manager import ws_manager
        ws_manager.broadcast_sync({
            "event": "QUEUE_UPDATED",
            "queue_id": item.id,
            "announcement_id": item.announcement_id,
            "action": act_clean,
            "status": new_status,
            "timestamp": now.isoformat(),
        })
    except Exception:
        pass

    return {
        "status": "success",
        "queue_id": item.id,
        "action": action,
        "new_status": new_status,
        "hardware_dispatch": dispatch_res,
        "auto_advance": advance_res,
    }


@router.post("/queue/advance", summary="Advance Speaker Queue")
def advance_speaker_queue_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    base_url = str(request.base_url).rstrip("/")
    advance_res = auto_advance_speaker_queue(db, force_advance=True, base_url=base_url)
    return {
        "status": "success",
        "details": advance_res,
    }


@router.post("/queue/{queue_id}/trigger_repeat_now", summary="Force Play Next Repeat Round Immediately")
def trigger_repeat_round_now(
    queue_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    from app.models.speaker_queue import SpeakerQueue
    item: Any = db.query(SpeakerQueue).filter(SpeakerQueue.id == queue_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Queue item not found")

    base_url = str(request.base_url).rstrip("/")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    setattr(item, "scheduled_time", now)
    if getattr(item, "status", None) in ("Completed", "Paused"):
        setattr(item, "status", "Queued")
    db.commit()
    db.refresh(item)

    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    adv_res = auto_advance_speaker_queue(db, force_advance=True, base_url=base_url)
    return {
        "status": "success",
        "message": f"Repeat broadcast triggered immediately for Announcement #{item.announcement_id}",
        "auto_advance": adv_res,
    }


