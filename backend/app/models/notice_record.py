from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.db.database import Base


class NoticeRecord(Base):
    """
    The permanent record of one notice. No foreign key to announcements on purpose: the record must
    outlive the notice. The original_* and creator fields are written once; the rest follow the notice.
    """

    __tablename__ = "notice_records"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, nullable=False, unique=True, index=True)

    # As first created (never changed)
    original_title = Column(String(255), nullable=True)
    original_content = Column(Text, nullable=True)
    creator_id = Column(Integer, nullable=True, index=True)
    creator_name = Column(String(255), nullable=True)
    creator_role = Column(String(50), nullable=True)
    creator_department = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Current state of the notice
    title = Column(String(255), nullable=True, index=True)
    content = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    priority = Column(String(30), nullable=True)
    emergency_level = Column(String(30), nullable=True)
    target_audience = Column(String(255), nullable=True)
    channels = Column(String(100), nullable=True)  # comma-separated: In-App Feed, Push Notification, Speaker
    status = Column(String(40), nullable=True)
    scheduled_at = Column(DateTime, nullable=True)

    # Delivery
    published_at = Column(DateTime, nullable=True)
    first_delivered_at = Column(DateTime, nullable=True)
    last_delivered_at = Column(DateTime, nullable=True, index=True)
    speaker_play_count = Column(Integer, nullable=False, default=0)

    # Deletion
    deleted_at = Column(DateTime, nullable=True, index=True)
    deleted_by_id = Column(Integer, nullable=True)
    deleted_by_name = Column(String(255), nullable=True)
    deleted_by_role = Column(String(50), nullable=True)
    deleted_before_broadcast = Column(Boolean, nullable=True)
    audio_deleted_at = Column(DateTime, nullable=True)

    partial = Column(Boolean, nullable=False, default=False)  # rebuilt from older logs; some fields unknown


class NoticeRecordEvent(Base):
    """One step in a notice's life, with who did it. Append-only: never changed or deleted."""

    __tablename__ = "notice_record_events"

    id = Column(Integer, primary_key=True, index=True)
    announcement_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    event = Column(String(30), nullable=False)
    actor_id = Column(Integer, nullable=True)
    actor_name = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    detail = Column(Text, nullable=True)
