from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class VipProtocolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    announcement_id: int
    guest_name: str
    guest_title: str
    guest_organization: Optional[str] = None
    event_name: str
    venue: str
    event_datetime: datetime
    arrival_datetime: Optional[datetime] = None
    spoken_script: str
    regional_script: Optional[str] = None
    voice_profile: str
    audio_url: Optional[str] = None
    confidence_score: float
    is_seating_announced: bool
    is_arrival_announced: bool
    exam_suppression_active: bool
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class VipProtocolUpdateRequest(BaseModel):
    guest_name: Optional[str] = None
    guest_title: Optional[str] = None
    guest_organization: Optional[str] = None
    venue: Optional[str] = None
    spoken_script: Optional[str] = None
    regional_script: Optional[str] = None
    voice_profile: Optional[str] = None
    exam_suppression_active: Optional[bool] = None


class VipArrivalTriggerRequest(BaseModel):
    target_zone: Optional[str] = "Portico-Auditorium"
    custom_welcome_note: Optional[str] = None
    volume: Optional[int] = 88
