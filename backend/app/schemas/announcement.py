from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.enums.announcement import (
    AnnouncementPriority,
    AnnouncementStatus,
    EmergencyLevel,
)


class AnnouncementCreate(BaseModel):
    title: str
    description: str
    category_id: int

    priority: AnnouncementPriority = AnnouncementPriority.NORMAL
    emergency_level: EmergencyLevel = EmergencyLevel.NORMAL
    scheduled_at: Optional[datetime] = None
    deliver_speaker: Optional[bool] = False
    deliver_in_app: Optional[bool] = True
    deliver_push: Optional[bool] = True
    target_audience: Optional[str] = None
    speaker_node_id: Optional[int] = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v):
        if isinstance(v, str):
            for p in AnnouncementPriority:
                if p.value.lower() == v.lower() or p.name.lower() == v.lower():
                    return p
        return v

    @field_validator("emergency_level", mode="before")
    @classmethod
    def normalize_emergency_level(cls, v):
        if isinstance(v, str):
            for e in EmergencyLevel:
                if e.value.lower() == v.lower() or e.name.lower() == v.lower():
                    return e
        return v


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None

    priority: Optional[AnnouncementPriority] = None
    emergency_level: Optional[EmergencyLevel] = None
    status: Optional[AnnouncementStatus] = None
    scheduled_at: Optional[datetime] = None
    deliver_speaker: Optional[bool] = None
    deliver_in_app: Optional[bool] = None
    deliver_push: Optional[bool] = None
    target_audience: Optional[str] = None
    speaker_node_id: Optional[int] = None

    @field_validator("priority", mode="before")
    @classmethod
    def normalize_priority(cls, v):
        if isinstance(v, str):
            for p in AnnouncementPriority:
                if p.value.lower() == v.lower() or p.name.lower() == v.lower():
                    return p
        return v

    @field_validator("emergency_level", mode="before")
    @classmethod
    def normalize_emergency_level(cls, v):
        if isinstance(v, str):
            for e in EmergencyLevel:
                if e.value.lower() == v.lower() or e.name.lower() == v.lower():
                    return e
        return v


class AnnouncementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str

    status: AnnouncementStatus | str
    priority: AnnouncementPriority | str
    emergency_level: EmergencyLevel | str

    scheduled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    created_by: int
    category_id: int

    creator_name: Optional[str] = None
    creator_role: Optional[str] = None
    department_name: Optional[str] = None
    category_name: Optional[str] = None
    target_audience: Optional[str] = None
    ai_summary: Optional[str] = None
    remarks: Optional[str] = None
    approver_name: Optional[str] = None
    approved_at: Optional[datetime] = None


class AnnouncementApprovalRequest(BaseModel):
    remarks: Optional[str] = None
