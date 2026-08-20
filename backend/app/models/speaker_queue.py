from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class SpeakerQueue(TimestampMixin, Base):
    """
    Stores announcements waiting to be played
    through the college speaker system.
    """

    __tablename__ = "speaker_queue"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # Foreign Keys & Node Binding
    # -------------------------

    announcement_id = Column(
        Integer,
        ForeignKey("announcements.id"),
        nullable=False,
        unique=True,
    )

    speaker_node_id = Column(
        Integer,
        ForeignKey("speaker_nodes.id"),
        nullable=True,
    )

    # -------------------------
    # Queue Details & Telemetry
    # -------------------------

    queue_position = Column(
        Integer,
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
    )

    scheduled_time = Column(
        DateTime,
        nullable=True,
    )

    played_at = Column(
        DateTime,
        nullable=True,
    )

    duration_seconds = Column(
        Integer,
        nullable=True,
        default=0,
    )

    failure_reason = Column(
        String(255),
        nullable=True,
    )

    error_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # -------------------------
    # Relationships
    # -------------------------

    announcement = relationship(
        "Announcement",
        back_populates="speaker_queue",
    )

    speaker_node = relationship(
        "SpeakerNode",
        back_populates="queue_items",
    )

