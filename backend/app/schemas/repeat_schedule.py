import re
from datetime import datetime, timezone
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
        def _normalize_time_str(val: Optional[str]) -> Optional[str]:
            if not val:
                return val
            val = val.strip()
            # Match 12-hour format e.g. "9:30 PM", "9:30pm", "02:15 AM", "12:00 PM"
            m = re.match(r"^(\d{1,2}):([0-5]\d)\s*([AaPp][Mm])$", val)
            if m:
                h, mn, meridian = int(m.group(1)), int(m.group(2)), m.group(3).upper()
                if 1 <= h <= 12 and 0 <= mn <= 59:
                    if meridian == "PM" and h != 12:
                        h += 12
                    elif meridian == "AM" and h == 12:
                        h = 0
                    return f"{h:02d}:{mn:02d}"
            # Match single-digit 24-hour hour like "9:00" -> "09:00"
            if re.match(r"^\d:[0-5]\d$", val):
                return "0" + val
            return val

        # 1. Custom time validation & auto-completion
        if "CUSTOM_WINDOW" in self.selected_slots:
            if not self.custom_start_time:
                raise ValueError("custom_start_time (HH:MM or HH:MM AM/PM) is required when CUSTOM_WINDOW is selected.")
            start_str = _normalize_time_str(self.custom_start_time)
            if not start_str or not TIME_REGEX.match(start_str):
                raise ValueError(f"custom_start_time '{self.custom_start_time}' must be in 24-hour HH:MM format or 12-hour format with AM/PM.")
            self.custom_start_time = start_str

            if not self.custom_end_time:
                # Default end time to +30 minutes if omitted
                sh, sm = map(int, start_str.split(":"))
                end_m = (sh * 60 + sm + 30) % (24 * 60)
                self.custom_end_time = f"{end_m // 60:02d}:{end_m % 60:02d}"
            else:
                end_str = _normalize_time_str(self.custom_end_time)
                if not end_str or not TIME_REGEX.match(end_str):
                    raise ValueError(f"custom_end_time '{self.custom_end_time}' must be in 24-hour HH:MM format or 12-hour format with AM/PM.")
                if start_str >= end_str:
                    raise ValueError("custom_start_time must be earlier than custom_end_time.")
                self.custom_end_time = end_str

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
