from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_optional_current_user
from app.db.database import get_db
from app.models.announcement import Announcement
from app.models.announcement_vip_protocol import AnnouncementVipProtocol
from app.models.user import User
from app.schemas.vip_protocol import (
    VipArrivalTriggerRequest,
    VipProtocolResponse,
    VipProtocolUpdateRequest,
)
from app.services.vip_announcement_service import (
    analyze_and_extract_vip,
    dispatch_vip_arrival_fanfare,
)

router = APIRouter(tags=["VIP Dignitary Protocols"])


@router.get(
    "/announcements/{announcement_id}/vip-protocol",
    response_model=VipProtocolResponse,
    summary="Get VIP Protocol Details for Notice",
    status_code=status.HTTP_200_OK,
)
def get_vip_protocol(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Retrieves the extracted dignitary details, spoken PA broadcast script,
    audio stream, and milestone announcement statuses.
    """
    protocol = db.query(AnnouncementVipProtocol).filter(AnnouncementVipProtocol.announcement_id == announcement_id).first()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No VIP Protocol detected or configured for Announcement #{announcement_id}.",
        )
    return protocol


@router.post(
    "/announcements/{announcement_id}/vip-protocol/analyze",
    response_model=VipProtocolResponse,
    summary="Analyze Announcement for VIP Dignitary",
    status_code=status.HTTP_200_OK,
)
def trigger_vip_analysis(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executes AI entity extraction on the announcement to detect Chief Guest details,
    generate formal radio broadcast script, and pre-render ceremonial audio.
    """
    protocol = analyze_and_extract_vip(db, announcement_id)
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Notice does not appear to describe a Chief Guest or dignitary event.",
        )
    return protocol


@router.put(
    "/announcements/{announcement_id}/vip-protocol",
    response_model=VipProtocolResponse,
    summary="Update VIP Protocol Script & Voice Settings",
    status_code=status.HTTP_200_OK,
)
def update_vip_protocol(
    announcement_id: int,
    data: VipProtocolUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Allows coordinators to review, edit pronunciation, or adjust the spoken PA script.
    """
    protocol = db.query(AnnouncementVipProtocol).filter(AnnouncementVipProtocol.announcement_id == announcement_id).first()
    if not protocol:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"VIP Protocol not found for Announcement #{announcement_id}.",
        )

    if data.guest_name is not None:
        protocol.guest_name = data.guest_name
    if data.guest_title is not None:
        protocol.guest_title = data.guest_title
    if data.venue is not None:
        protocol.venue = data.venue
    if data.spoken_script is not None:
        protocol.spoken_script = data.spoken_script
    if data.voice_profile is not None:
        protocol.voice_profile = data.voice_profile
    if data.exam_suppression_active is not None:
        protocol.exam_suppression_active = data.exam_suppression_active

    db.commit()
    db.refresh(protocol)
    return protocol


@router.post(
    "/announcements/{announcement_id}/vip-protocol/arrival",
    summary="Trigger Live Dignitary Arrival Fanfare Broadcast",
    status_code=status.HTTP_200_OK,
)
def trigger_arrival_fanfare(
    announcement_id: int,
    payload: VipArrivalTriggerRequest = VipArrivalTriggerRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    On-Demand Live Trigger: Fast-tracks arrival fanfare announcement into
    the speaker queue at Position #2 when the Chief Guest's car pulls into the campus portico.
    """
    result = dispatch_vip_arrival_fanfare(
        db=db,
        announcement_id=announcement_id,
        current_user=current_user,
        target_zone=payload.target_zone or "Portico-Auditorium",
        custom_note=payload.custom_welcome_note,
    )
    return result
