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
        default="DEPARTMENT",
    )

    target_node_id = Column(
        Integer,
        ForeignKey("speaker_nodes.id", ondelete="SET NULL"),
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
