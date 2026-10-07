import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

ALLOWED_SLOTS = ["SHORT_BREAK", "LUNCH_BREAK", "EVENING_BREAK", "HOSTEL_WINDOW", "CUSTOM_WINDOW"]
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

    @field_validator("start_date", "end_date", "event_datetime", mode="before")
    @classmethod
    def normalize_datetimes(cls, v):
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if dt.tzinfo is not None:
                    return dt.astimezone(timezone.utc).replace(tzinfo=None)
                return dt
            except Exception:
                pass
        elif isinstance(v, datetime) and v.tzinfo is not None:
            return v.astimezone(timezone.utc).replace(tzinfo=None)
        return v

    @model_validator(mode="after")
    def validate_rules(self):
        # 1. Custom time validation & auto-completion
        if "CUSTOM_WINDOW" in self.selected_slots:
            if not self.custom_start_time:
                raise ValueError("custom_start_time (HH:MM) is required when CUSTOM_WINDOW is selected.")
            st = self.custom_start_time.strip()
            if re.match(r"^\d:[0-5]\d$", st):
                st = "0" + st
                self.custom_start_time = st
            if not TIME_REGEX.match(self.custom_start_time):
                raise ValueError(f"custom_start_time '{self.custom_start_time}' must be in 24-hour HH:MM format.")

            if not self.custom_end_time:
                # Default end time to +30 minutes if omitted
                sh, sm = map(int, self.custom_start_time.split(":"))
                end_m = (sh * 60 + sm + 30) % (24 * 60)
                self.custom_end_time = f"{end_m // 60:02d}:{end_m % 60:02d}"
            else:
                et = self.custom_end_time.strip()
                if re.match(r"^\d:[0-5]\d$", et):
                    et = "0" + et
                    self.custom_end_time = et
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
