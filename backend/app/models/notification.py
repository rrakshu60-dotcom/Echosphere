from sqlalchemy import Boolean, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class Notification(TimestampMixin, Base):
    """
    Stores notifications delivered to users.
    """

    __tablename__ = "notifications"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # Foreign Keys
    # -------------------------

    announcement_id = Column(
        Integer,
        ForeignKey("announcements.id"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # -------------------------
    # Notification Status
    # -------------------------

    is_read = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    # -------------------------
    # Relationships
    # -------------------------

    announcement = relationship(
        "Announcement",
        back_populates="notifications",
    )

    user = relationship(
        "User",
        back_populates="notifications",
    )
