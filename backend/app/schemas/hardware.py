from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class SpeakerNodeBase(BaseModel):
    name: str = Field(..., example="CSE Main Horn 1")
    mac_address: str = Field(..., example="AA:BB:CC:DD:EE:01")
    ip_address: Optional[str] = Field(None, example="192.168.1.101")
    department_id: Optional[int] = None
    zone: str = Field("College-Wide", example="Block A")
    volume: int = Field(80, ge=0, le=100)


class SpeakerNodeCreate(SpeakerNodeBase):
    pass


class SpeakerNodeUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    department_id: Optional[int] = None
    zone: Optional[str] = None
    volume: Optional[int] = Field(None, ge=0, le=100)
    is_active: Optional[bool] = None


class SpeakerNodeHeartbeat(BaseModel):
    mac_address: str
    ip_address: Optional[str] = None
    cpu_usage: Optional[float] = 0.0
    memory_usage: Optional[float] = 0.0
    disk_space: Optional[float] = 0.0
    status: Optional[str] = "ONLINE"


class SpeakerNodeResponse(SpeakerNodeBase):
    id: int
    status: str
    department_name: Optional[str] = None
    cpu_usage: Optional[float] = 0.0
    memory_usage: Optional[float] = 0.0
    disk_space: Optional[float] = 0.0
    last_heartbeat: Optional[datetime] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpeakerBroadcastRequest(BaseModel):
    announcement_id: int
    speaker_node_ids: Optional[List[int]] = None
    zone: Optional[str] = None
    volume: Optional[int] = 85


class EmergencyOverrideRequest(BaseModel):
    title: str = Field(..., example="EMERGENCY CAMPUS EVACUATION NOTICE")
    message: str = Field(..., example="Emergency warning: Please proceed calmly to designated assembly area.")
    zone: Optional[str] = "College-Wide"
    voice_type: Optional[str] = "AI Text-to-Speech"
    volume: Optional[int] = 100


class SpeakerControlRequest(BaseModel):
    command: str = Field(..., example="PLAY_ANNOUNCEMENT")  # PLAY_ANNOUNCEMENT, PAUSE, RESUME, SKIP, CANCEL, RESTART, TEST_SPEAKER, SET_VOLUME
    announcement_id: Optional[int] = None
    audio_url: Optional[str] = None
    volume: Optional[int] = None


class SpeakerQueueItemResponse(BaseModel):
    id: int
    announcement_id: int
    title: str
    department: str
    priority: str
    type: str
    status: str
    queue_position: int
    scheduled_time: Optional[datetime] = None
    played_at: Optional[datetime] = None
    audio_url: Optional[str] = None
    speaker_node_id: Optional[int] = None

    class Config:
        from_attributes = True


class ReorderQueueRequest(BaseModel):
    queue_ids: List[int] = Field(..., example=[3, 1, 2])


class EnqueueAnnouncementRequest(BaseModel):
    announcement_id: int
    scheduled_time: Optional[datetime] = None
    speaker_node_id: Optional[int] = None

