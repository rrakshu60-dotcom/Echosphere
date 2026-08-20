from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_roles
from app.db.database import get_db
from app.models.user import User
from app.repositories.hardware_repository import (
    create_speaker_node,
    delete_speaker_node,
    delete_speaker_queue_item,
    get_all_speaker_nodes,
    get_speaker_node_by_id,
    get_speaker_node_by_mac,
    get_speaker_queue,
    update_queue_item_status,
    update_speaker_node,
    update_speaker_node_heartbeat,
)


from app.schemas.hardware import (
    EmergencyOverrideRequest,
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
    current_user: User = Depends(get_current_user),
):
    return get_all_speaker_nodes(db=db, department_id=department_id, zone=zone, status=status)


@router.post("/speakers/register", response_model=SpeakerNodeResponse, status_code=status.HTTP_201_CREATED)
def register_speaker_node(
    node_in: SpeakerNodeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin")
    ),
):
    existing = get_speaker_node_by_mac(db, node_in.mac_address)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Speaker node with MAC address {node_in.mac_address} already exists.",
        )
    return create_speaker_node(db=db, node_in=node_in)


@router.get("/speakers/{id}", response_model=SpeakerNodeResponse)
def get_speaker_node_details(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    node = get_speaker_node_by_id(db, id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Speaker node not found.")
    return node


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
    return update_speaker_node(db=db, node=node, update_data=update_in)


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
        announcement_id=announcement.id,
        title=announcement.title,
        content=announcement.content,
        department_code=node.department.code if node.department else "ALL",
        zone=node.zone,
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
        require_roles("Dev Admin", "Developer", "College Admin", "Principal")
    ),
):
    base_url = str(request.base_url).rstrip("/")
    announcement_id = 99999
    result = await broadcast_announcement_to_speaker(
        db=db,
        announcement_id=announcement_id,
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
        "details": result,
    }


@router.post("/speakers/{id}/control")
def send_control_command(
    id: int,
    control_in: SpeakerControlRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")
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
    return {"status": "success", "node_id": node.id, "mac_address": node.mac_address}


@router.get("/queue")
def fetch_speaker_queue(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    queue_items = get_speaker_queue(db=db, status=status)
    result = []
    for item in queue_items:
        ann = item.announcement
        result.append({
            "id": item.id,
            "announcement_id": item.announcement_id,
            "title": ann.title if ann else "Announcement",
            "department": ann.department.name if (ann and ann.department) else "College-Wide",
            "priority": ann.priority.value if (ann and hasattr(ann.priority, 'value')) else str(ann.priority) if ann else "Normal",
            "type": "AI Speech",
            "status": item.status,
            "queue_position": item.queue_position,
            "scheduled_time": item.scheduled_time.isoformat() if item.scheduled_time else None,
            "played_at": item.played_at.isoformat() if item.played_at else None,
            "speaker_node_id": item.speaker_node_id,
        })
    return result


@router.post("/queue/{id}/action")
def update_queue_action(
    id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")
    ),
):
    status_map = {
        "play": "Playing",
        "pause": "Paused",
        "skip": "Skipped",
        "cancel": "Cancelled",
    }
    new_status = status_map.get(action.lower(), "Queued")
    updated = update_queue_item_status(db=db, queue_id=id, status=new_status)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Queue item not found.")
    return {"status": "success", "queue_id": id, "action": action, "new_status": new_status}

