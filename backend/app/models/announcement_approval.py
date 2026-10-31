from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.db.database import Base


class AnnouncementApproval(Base):
    """
    Stores the approval workflow for announcements.
    """

    __tablename__ = "announcement_approvals"

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

    # Plain id, no foreign key: it outlives the approver's account.
    approver_id = Column(
        Integer,
        nullable=False,
    )

    # -------------------------
    # Approval Details
    # -------------------------

    status = Column(
        String(30),
        nullable=False,
    )

    remarks = Column(
        String(500),
        nullable=True,
    )

    approved_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -------------------------
    # Relationships
    # -------------------------

    announcement = relationship(
        "Announcement",
        back_populates="approvals",
    )

    approver = relationship(
        "User",
        primaryjoin="foreign(AnnouncementApproval.approver_id) == User.id",
        back_populates="approvals",
        viewonly=True,
    )
