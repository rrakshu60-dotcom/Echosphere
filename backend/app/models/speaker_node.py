from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class SpeakerNode(TimestampMixin, Base):
    """
    Represents a physical speaker device / microcontroller node
    (ESP32, Raspberry Pi, PA System) installed on campus.
    """

    __tablename__ = "speaker_nodes"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String(100),
        nullable=False,
    )

    mac_address = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )

    ip_address = Column(
        String(45),
        nullable=True,
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
    )

    zone = Column(
        String(50),
        nullable=False,
        default="College-Wide",
    )

    status = Column(
        String(30),
        nullable=False,
        default="OFFLINE",
    )

    volume = Column(
        Integer,
        nullable=False,
        default=80,
    )

    cpu_usage = Column(
        Float,
        nullable=True,
        default=0.0,
    )

    memory_usage = Column(
        Float,
        nullable=True,
        default=0.0,
    )

    disk_space = Column(
        Float,
        nullable=True,
        default=0.0,
    )

    last_heartbeat = Column(
        DateTime,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # Relationships
    department = relationship(
        "Department",
        backref="speaker_nodes",
    )

    queue_items = relationship(
        "SpeakerQueue",
        back_populates="speaker_node",
    )
