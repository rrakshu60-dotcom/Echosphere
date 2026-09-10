from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.core.dependencies import get_current_user, get_optional_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.models.announcement import Announcement
from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.core.enums.announcement import AnnouncementPriority, AnnouncementStatus, EmergencyLevel
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
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
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
    return create_speaker_node(db=db, node_in=node_in)


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
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
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
        announcement_id=int(announcement.id),
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
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")
    ),
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
            announcement_id=int(emergency_ann.id),
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
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
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
        auto_advance_speaker_queue(db)
    except Exception:
        pass
    cmds = get_pending_commands_for_mac(str(node.mac_address))
    return {
        "status": "success",
        "node_id": node.id,
        "mac_address": node.mac_address,
        "pending_commands": cmds,
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
        auto_advance_speaker_queue(db)
    except Exception:
        pass
    cmds = get_pending_commands_for_mac(mac_address)
    return {
        "mac_address": mac_address,
        "pending_commands": cmds,
    }


@router.get("/queue")
def fetch_speaker_queue(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    try:
        auto_advance_speaker_queue(db)
    except Exception:
        pass

    if status is None:
        queue_items = (
            db.query(SpeakerQueue)
            .filter(SpeakerQueue.status.in_(["Playing", "Paused", "Next in Queue", "Queued"]))
            .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
            .all()
        )
    else:
        queue_items = get_speaker_queue(db=db, status=status)
    result = []
    for item in queue_items:
        ann = item.announcement
        result.append({
            "id": item.id,
            "announcement_id": item.announcement_id,
            "title": ann.title if ann else "Announcement",
            "department": ann.creator.department.name if (ann and getattr(ann, 'creator', None) and getattr(ann.creator, 'department', None)) else "College-Wide",
            "priority": ann.priority.value if (ann and hasattr(ann.priority, 'value')) else str(ann.priority) if ann else "Normal",
            "type": "AI Speech",
            "status": item.status,
            "queue_position": item.queue_position,
            "scheduled_time": item.scheduled_time.isoformat() if item.scheduled_time else None,
            "played_at": item.played_at.isoformat() if item.played_at else None,
            "audio_url": f"/static/audio_streams/announcement_{item.announcement_id}.mp3",
            "speaker_node_id": item.speaker_node_id,
        })
    return result


@router.post("/queue/add")
def enqueue_speaker_announcement(
    enqueue_in: EnqueueAnnouncementRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    ann = get_announcement_by_id(db, enqueue_in.announcement_id)
    if not ann:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
    dept_code = "ALL"
    if ann.creator and hasattr(ann.creator, 'department') and ann.creator.department:
        dept_code = ann.creator.department.code

    base_url = str(request.base_url).rstrip("/")
    p_val = ann.priority.value if hasattr(ann.priority, 'value') else str(ann.priority)
    result = enqueue_and_broadcast_announcement(
        db=db,
        announcement_id=int(ann.id),
        title=str(ann.title),
        content=str(ann.description),
        department_code=dept_code,
        zone="College-Wide",
        is_emergency=(p_val == "EMERGENCY"),
        speaker_node_id=enqueue_in.speaker_node_id,
        base_url=base_url,
    )
    return {
        "status": "success",
        "announcement_id": ann.id,
        "queue_position": result.get("queue_position", 1),
        "item_status": result.get("queue_status", "Playing" if result.get("is_playing") else "Queued"),
        "is_playing": result.get("is_playing", False),
        "details": result,
    }


@router.post("/queue/reorder")
def reorder_speaker_queue_items(
    reorder_in: ReorderQueueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    updated_items = reorder_speaker_queue(db=db, ordered_ids=reorder_in.queue_ids)
    return {
        "status": "success",
        "reordered_count": len(updated_items),
        "queue_ids": [item.id for item in updated_items],
    }


@router.post("/queue/{id}/action")
def update_queue_action(
    id: int,
    action: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    status_map = {
        "play": "Playing",
        "pause": "Paused",
        "resume": "Playing",
        "skip": "Skipped",
        "cancel": "Cancelled",
        "stop": "Cancelled",
        "complete": "Completed",
        "remove": "Completed",
    }
    new_status = status_map.get(action.lower(), "Queued")
    updated = update_queue_item_status(db=db, queue_id=id, status=new_status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")

    # Dispatch hardware command to all speaker nodes
    base_url = str(request.base_url).rstrip("/")
    dispatch_res = dispatch_queue_action_to_speakers(
        db=db,
        queue_item=updated,
        action=action,
        base_url=base_url,
    )

    # Auto-advance to next queued item if current was skipped, cancelled, or completed
    advance_res = None
    if action.lower() in ("skip", "cancel", "stop", "complete", "remove"):
        from app.services.hardware_speaker_service import auto_advance_speaker_queue
        try:
            advance_res = auto_advance_speaker_queue(db, force_advance=True, base_url=base_url)
        except Exception:
            pass

    return {
        "status": "success",
        "queue_id": id,
        "action": action,
        "new_status": new_status,
        "hardware_dispatch": dispatch_res,
        "auto_advance": advance_res,
    }


@router.post("/queue/advance", summary="Advance Speaker Queue")
def advance_speaker_queue_endpoint(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
    ),
):
    from app.services.hardware_speaker_service import auto_advance_speaker_queue
    base_url = str(request.base_url).rstrip("/")
    advance_res = auto_advance_speaker_queue(db, force_advance=True, base_url=base_url)
    return {
        "status": "success",
        "details": advance_res,
    }


