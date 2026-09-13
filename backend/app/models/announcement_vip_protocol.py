from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class AnnouncementVipProtocol(TimestampMixin, Base):
    """
    Stores VIP Dignitary / Chief Guest protocol information extracted from notices.
    Manages formal spoken radio scripts, ceremonial audio streams, T-minus seating
    calls, and on-arrival fanfare broadcasts.
    """

    __tablename__ = "announcement_vip_protocols"

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

    # Extracted Dignitary Details
    guest_name = Column(
        String(150),
        nullable=False,
    )

    guest_title = Column(
        String(200),
        nullable=False,
    )

    guest_organization = Column(
        String(200),
        nullable=True,
    )

    event_name = Column(
        String(255),
        nullable=False,
    )

    venue = Column(
        String(150),
        nullable=False,
    )

    event_datetime = Column(
        DateTime,
        nullable=False,
    )

    arrival_datetime = Column(
        DateTime,
        nullable=True,
    )

    # Spoken Radio PA Broadcast Script
    spoken_script = Column(
        Text,
        nullable=False,
    )

    regional_script = Column(
        Text,
        nullable=True,
    )

    voice_profile = Column(
        String(50),
        nullable=False,
        default="british_female",
    )

    audio_url = Column(
        String(255),
        nullable=True,
    )

    confidence_score = Column(
        Float,
        nullable=False,
        default=0.90,
    )

    # Milestone tracking
    is_seating_announced = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    is_arrival_announced = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exam_suppression_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="VERIFIED",
    )

    # Relationships
    announcement = relationship(
        "Announcement",
        back_populates="vip_protocol",
    )
