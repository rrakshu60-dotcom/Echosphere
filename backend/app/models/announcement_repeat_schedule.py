from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class AnnouncementRepeatSchedule(TimestampMixin, Base):
    """
    Stores repeat broadcast policies for speaker announcements.
    Allows automated repetitions during designated campus break windows
    or specialized hostel custom time frames.
    """

    __tablename__ = "announcement_repeat_schedules"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    announcement_id = Column(
        Integer,
        ForeignKey("announcements.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Selected slots: e.g. ["SHORT_BREAK", "LUNCH_BREAK", "CUSTOM_WINDOW"]
    selected_slots = Column(
        JSON,
        nullable=False,
        default=list,
    )

    # Custom window (e.g. for hostel nodes or specialized slots) - "HH:MM" format
    custom_start_time = Column(
        String(5),
        nullable=True,
    )

    custom_end_time = Column(
        String(5),
        nullable=True,
    )

    # Target Scope: "DEPARTMENT", "COLLEGE_WIDE", "HOSTEL"
    target_scope = Column(
        String(30),
        nullable=False,
        default="COLLEGE_WIDE",
    )

    target_node_id = Column(
        Integer,
        ForeignKey("speaker_nodes.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Repeat Mode: "BREAK_SLOTS", "CUSTOM", "INTERVAL"
    repeat_mode = Column(
        String(20),
        nullable=False,
        default="BREAK_SLOTS",
    )

    # Interval in minutes for legacy INTERVAL mode (0 for BREAK_SLOTS)
    interval_minutes = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Maximum repeat broadcasts
    max_repeats = Column(
        Integer,
        nullable=False,
        default=15,
    )

    # Whether the notice should play immediately on publish before repeating
    play_on_publish = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Next scheduled repeat execution time
    next_repeat_at = Column(
        DateTime,
        nullable=True,
    )

    # Last time a repeat broadcast was executed
    last_repeat_at = Column(
        DateTime,
        nullable=True,
    )

    # Event date for 48h horizon verification
    event_datetime = Column(
        DateTime,
        nullable=False,
    )

    # Repeat window start and end (strictly <= 2 days span)
    start_date = Column(
        DateTime,
        nullable=False,
    )

    end_date = Column(
        DateTime,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    total_played_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Relationships
    announcement = relationship(
        "Announcement",
        back_populates="repeat_schedule",
    )

    target_node = relationship(
        "SpeakerNode",
    )

    logs = relationship(
        "RepeatSlotExecutionLog",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )

    @property
    def calculated_time_range(self):
        if self.custom_start_time and self.custom_end_time:
            from app.services.repeat_schedule_service import calculate_time_window_duration
            return calculate_time_window_duration(self.custom_start_time, self.custom_end_time).get("display_range")
        return None

    @property
    def calculated_duration_minutes(self):
        if self.custom_start_time and self.custom_end_time:
            from app.services.repeat_schedule_service import calculate_time_window_duration
            return calculate_time_window_duration(self.custom_start_time, self.custom_end_time).get("duration_minutes")
        return None

    @property
    def calculated_duration_str(self):
        if self.custom_start_time and self.custom_end_time:
            from app.services.repeat_schedule_service import calculate_time_window_duration
            return calculate_time_window_duration(self.custom_start_time, self.custom_end_time).get("duration_str")
        return None

    @property
    def time_windows_summary(self):
        from app.services.repeat_schedule_service import get_schedule_time_summary
        return get_schedule_time_summary(self).get("summary", "")


class RepeatSlotExecutionLog(TimestampMixin, Base):
    """
    Execution log preventing duplicate plays within the same slot instance,
    while guaranteeing that playing in one slot (e.g. Short Break) does not
    block playing in another slot (e.g. Lunch Break or tomorrow's break).
    """

    __tablename__ = "repeat_slot_execution_logs"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    schedule_id = Column(
        Integer,
        ForeignKey("announcement_repeat_schedules.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    # Key format: "{announcement_id}:{slot_name}:{YYYY-MM-DD}"
    slot_key = Column(
        String(80),
        unique=True,
        index=True,
        nullable=False,
    )

    slot_name = Column(
        String(30),
        nullable=False,
    )

    played_at = Column(
        DateTime,
        nullable=False,
    )

    schedule = relationship(
        "AnnouncementRepeatSchedule",
        back_populates="logs",
    )
