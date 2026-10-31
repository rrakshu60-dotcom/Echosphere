from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class AnnouncementArchive(TimestampMixin, Base):
    """
    Stores archived announcements.
    """

    __tablename__ = "announcement_archives"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # Original Announcement
    # -------------------------

    original_announcement_id = Column(
        Integer,
        ForeignKey("announcements.id"),
        nullable=False,
    )

    # -------------------------
    # Archived Data
    # -------------------------

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=False,
    )

    priority = Column(
        String(30),
        nullable=False,
    )

    emergency_level = Column(
        String(30),
        nullable=False,
    )

    # Plain id, no foreign key: it outlives the author's account.
    created_by = Column(
        Integer,
        nullable=False,
    )

    # -------------------------
    # Relationships
    # -------------------------

    announcement = relationship("Announcement")

    creator = relationship(
        "User",
        primaryjoin="foreign(AnnouncementArchive.created_by) == User.id",
        viewonly=True,
    )
