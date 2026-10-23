import re
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

ALLOWED_MODES = ["INTERVAL", "BREAK_SLOTS", "CUSTOM"]
ALLOWED_SLOTS = ["SHORT_BREAK", "LUNCH_BREAK", "EVENING_BREAK", "HOSTEL_WINDOW", "CUSTOM_WINDOW", "INTERVAL"]
ALLOWED_SCOPES = ["DEPARTMENT", "COLLEGE_WIDE", "HOSTEL"]
TIME_REGEX = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class RepeatScheduleBase(BaseModel):
    repeat_mode: str = "BREAK_SLOTS"
    interval_minutes: int = 0
    max_repeats: int = 15
    play_on_publish: bool = True
    selected_slots: Optional[List[str]] = ["SHORT_BREAK"]
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    target_scope: str = "COLLEGE_WIDE"
    target_node_id: Optional[int] = None
    event_datetime: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    force_enable_speaker: Optional[bool] = False
    next_repeat_at: Optional[datetime] = None
    last_repeat_at: Optional[datetime] = None

    @field_validator("repeat_mode")
    @classmethod
    def validate_mode(cls, v: str):
        normalized = v.upper().strip()
        if normalized not in ALLOWED_MODES:
            raise ValueError(f"Invalid repeat_mode '{v}'. Allowed modes: {ALLOWED_MODES}")
        return normalized

    @field_validator("selected_slots")
    @classmethod
    def validate_slots(cls, v: Optional[List[str]]):
        if v is None:
            return v
        if not v:
            return []
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

    @field_validator("start_date", "end_date", "event_datetime", "next_repeat_at", "last_repeat_at", mode="before")
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
            m = re.match(r"^(\d{1,2}):([0-5]\d)\s*([AaPp][Mm])$", val)
            if m:
                h, mn, meridian = int(m.group(1)), int(m.group(2)), m.group(3).upper()
                if 1 <= h <= 12 and 0 <= mn <= 59:
                    if meridian == "PM" and h != 12:
                        h += 12
                    elif meridian == "AM" and h == 12:
                        h = 0
                    return f"{h:02d}:{mn:02d}"
            if re.match(r"^\d:[0-5]\d$", val):
                return "0" + val
            return val

        # 1. Mode and Slots defaulting (the default break slot must not turn a requested interval into a daily break)
        if self.repeat_mode == "INTERVAL" and "selected_slots" not in self.model_fields_set:
            self.selected_slots = None
        if self.selected_slots and any(s in ["SHORT_BREAK", "LUNCH_BREAK", "EVENING_BREAK", "HOSTEL_WINDOW"] for s in self.selected_slots):
            self.repeat_mode = "BREAK_SLOTS"
        elif self.selected_slots and self.selected_slots == ["CUSTOM_WINDOW"]:
            self.repeat_mode = "CUSTOM"
        elif self.repeat_mode == "INTERVAL":
            if not self.selected_slots:
                self.selected_slots = ["INTERVAL"]
            if self.interval_minutes < 1:
                self.interval_minutes = 15
            if self.max_repeats < 0:
                self.max_repeats = 3
        elif self.repeat_mode == "BREAK_SLOTS":
            if not self.selected_slots:
                self.selected_slots = ["SHORT_BREAK", "LUNCH_BREAK"]
        elif self.repeat_mode == "CUSTOM":
            if not self.selected_slots:
                self.selected_slots = ["CUSTOM_WINDOW"]

        # 2. Custom time validation & auto-completion
        if self.selected_slots and "CUSTOM_WINDOW" in self.selected_slots:
            if not self.custom_start_time:
                raise ValueError("custom_start_time (HH:MM or HH:MM AM/PM) is required when CUSTOM_WINDOW is selected.")
            start_str = _normalize_time_str(self.custom_start_time)
            if not start_str or not TIME_REGEX.match(start_str):
                raise ValueError(f"custom_start_time '{self.custom_start_time}' must be in 24-hour HH:MM format or 12-hour format with AM/PM.")
            self.custom_start_time = start_str

            if not self.custom_end_time:
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

        # 3. Date defaults and order
        from datetime import timedelta
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        if self.start_date is None:
            self.start_date = now_dt
        if self.end_date is None:
            self.end_date = self.start_date + timedelta(hours=24)
        if self.event_datetime is None:
            self.event_datetime = self.end_date

        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be earlier than start_date.")

        # 4. Maximum lifespan: Strictly 1 to 2 days (48 hours max)
        duration_seconds = (self.end_date - self.start_date).total_seconds()
        if duration_seconds > (2 * 86400 + 300):
            raise ValueError("Repeat schedule lifespan cannot exceed 2 days (48 hours).")

        # 5. Anti-spam horizon: cannot schedule repeats days before the event
        horizon_seconds = (self.event_datetime - self.start_date).total_seconds()
        if horizon_seconds > (48 * 3600 + 300):
            raise ValueError("Repeat schedule can only begin within 48 hours prior to the event date.")

        return self


class RepeatScheduleCreate(RepeatScheduleBase):
    pass


class RepeatScheduleUpdate(BaseModel):
    repeat_mode: Optional[str] = None
    interval_minutes: Optional[int] = None
    max_repeats: Optional[int] = None
    play_on_publish: Optional[bool] = None
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
    next_repeat_at: Optional[datetime] = None
    last_repeat_at: Optional[datetime] = None

    @field_validator("repeat_mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]):
        if v is not None:
            normalized = v.upper().strip()
            if normalized not in ALLOWED_MODES:
                raise ValueError(f"Invalid repeat_mode '{v}'. Allowed modes: {ALLOWED_MODES}")
            return normalized
        return v

    @field_validator("selected_slots")
    @classmethod
    def validate_slots(cls, v: Optional[List[str]]):
        if v is not None:
            if not v:
                return []
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
    repeat_mode: str = "BREAK_SLOTS"
    interval_minutes: int = 0
    max_repeats: int = 15
    play_on_publish: bool = True
    selected_slots: List[str]
    custom_start_time: Optional[str] = None
    custom_end_time: Optional[str] = None
    target_scope: str = "COLLEGE_WIDE"
    target_node_id: Optional[int] = None
    event_datetime: datetime
    start_date: datetime
    end_date: datetime
    is_active: bool
    total_played_count: int
    next_repeat_at: Optional[datetime] = None
    last_repeat_at: Optional[datetime] = None
    calculated_time_range: Optional[str] = None
    calculated_duration_minutes: Optional[int] = None
    calculated_duration_str: Optional[str] = None
    time_windows_summary: Optional[str] = None
    logs: List[RepeatSlotLogResponse] = []


