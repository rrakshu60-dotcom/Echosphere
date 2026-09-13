import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

ALLOWED_SLOTS = ["SHORT_BREAK", "LUNCH_BREAK", "CUSTOM_WINDOW"]
ALLOWED_SCOPES = ["DEPARTMENT", "COLLEGE_WIDE", "HOSTEL"]
TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class RepeatScheduleBase(BaseModel):
    selected_slots: List[str]
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    target_scope: str = "DEPARTMENT"
    target_node_id: Optional[int] = None
    event_datetime: datetime
    start_date: datetime
    end_date: datetime
    force_enable_speaker: Optional[bool] = False

    @field_validator("selected_slots")
    @classmethod
    def validate_slots(cls, v: List[str]):
        if not v:
            raise ValueError("At least one repeat slot must be selected.")
        for slot in v:
            normalized = slot.upper().strip()
            if normalized not in ALLOWED_SLOTS:
                raise ValueError(f"Invalid slot '{slot}'. Allowed slots: {ALLOWED_SLOTS}")
        return [s.upper().strip() for s in v]

    @field_validator("target_scope")
    @classmethod
    def validate_scope(cls, v: str):
        normalized = v.upper().strip()
        if normalized not in ALLOWED_SCOPES:
            raise ValueError(f"Invalid target scope '{v}'. Allowed scopes: {ALLOWED_SCOPES}")
        return normalized

    @model_validator(mode="after")
    def validate_rules(self):
        # 1. Custom time validation
        if "CUSTOM_WINDOW" in self.selected_slots:
            if not self.custom_start_time or not self.custom_end_time:
                raise ValueError("Both custom_start_time and custom_end_time (HH:MM) are required when CUSTOM_WINDOW is selected.")
            if not TIME_REGEX.match(self.custom_start_time):
                raise ValueError(f"custom_start_time '{self.custom_start_time}' must be in 24-hour HH:MM format.")
            if not TIME_REGEX.match(self.custom_end_time):
                raise ValueError(f"custom_end_time '{self.custom_end_time}' must be in 24-hour HH:MM format.")
            if self.custom_start_time >= self.custom_end_time:
                raise ValueError("custom_start_time must be earlier than custom_end_time.")

        # 2. Date order
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")

        # 3. Maximum lifespan: Strictly 1 to 2 days (48 hours max)
        duration_seconds = (self.end_date - self.start_date).total_seconds()
        if duration_seconds > (2 * 86400 + 300):  # 48 hours (+5 min tolerance)
            raise ValueError("Repeat schedule lifespan cannot exceed 2 days (48 hours).")

        # 4. Anti-spam horizon: cannot schedule repeats days before the event
        # Repeat start must be within 48 hours of the event datetime
        horizon_seconds = (self.event_datetime - self.start_date).total_seconds()
        if horizon_seconds > (48 * 3600 + 300):
            raise ValueError("Repeat schedule can only begin within 48 hours prior to the event date.")

        return self


class RepeatScheduleCreate(RepeatScheduleBase):
    pass


class RepeatScheduleUpdate(BaseModel):
    selected_slots: Optional[List[str]] = None
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    target_scope: Optional[str] = None
    target_node_id: Optional[int] = None
    event_datetime: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    force_enable_speaker: Optional[bool] = False

    @field_validator("selected_slots")
    @classmethod
    def validate_slots(cls, v: Optional[List[str]]):
        if v is not None:
            if not v:
                raise ValueError("At least one repeat slot must be selected.")
            for slot in v:
                normalized = slot.upper().strip()
                if normalized not in ALLOWED_SLOTS:
                    raise ValueError(f"Invalid slot '{slot}'. Allowed slots: {ALLOWED_SLOTS}")
            return [s.upper().strip() for s in v]
        return v

    @field_validator("target_scope")
    @classmethod
    def validate_scope(cls, v: Optional[str]):
        if v is not None:
            normalized = v.upper().strip()
            if normalized not in ALLOWED_SCOPES:
                raise ValueError(f"Invalid target scope '{v}'. Allowed scopes: {ALLOWED_SCOPES}")
            return normalized
        return v


class RepeatSlotLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_key: str
    slot_name: str
    played_at: datetime


class RepeatScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    announcement_id: int
    selected_slots: List[str]
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    target_scope: str
    target_node_id: Optional[int] = None
    event_datetime: datetime
    start_date: datetime
    end_date: datetime
    is_active: bool
    total_played_count: int
    logs: List[RepeatSlotLogResponse] = []
