from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.enums.announcement import (
    AnnouncementPriority,
    AnnouncementStatus,
    EmergencyLevel,
)
from app.db.database import Base
from app.models.base_model import TimestampMixin


class Announcement(TimestampMixin, Base):
    """
    Stores announcements created by authorized users.
    """

    __tablename__ = "announcements"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # Announcement Details
    # -------------------------

    title = Column(
        String(255),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=False,
    )

    status = Column(
        Enum(AnnouncementStatus),
        default=AnnouncementStatus.DRAFT,
        nullable=False,
    )

    priority = Column(
        Enum(AnnouncementPriority),
        default=AnnouncementPriority.NORMAL,
        nullable=False,
    )

    emergency_level = Column(
        Enum(EmergencyLevel),
        default=EmergencyLevel.NORMAL,
        nullable=False,
    )

    scheduled_at = Column(
        DateTime,
        nullable=True,
    )

    target_audience = Column(
        String(255),
        default="Entire College",
        nullable=True,
    )

    ai_summary = Column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Foreign Keys
    # -------------------------

    created_by = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("announcement_categories.id"),
        nullable=False,
    )

    # -------------------------
    # Relationships
    # -------------------------

    creator = relationship(
        "User",
        back_populates="announcements",
    )

    category = relationship(
        "AnnouncementCategory",
        back_populates="announcements",
    )

    approvals = relationship(
        "AnnouncementApproval",
        back_populates="announcement",
        cascade="all, delete-orphan",
    )

    deliveries = relationship(
        "AnnouncementDelivery",
        back_populates="announcement",
        cascade="all, delete-orphan",
    )

    notifications = relationship(
        "Notification",
        back_populates="announcement",
        cascade="all, delete-orphan",
    )

    speaker_queue = relationship(
        "SpeakerQueue",
        back_populates="announcement",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # -------------------------
    # Computed Model Properties
    # -------------------------

    @property
    def creator_name(self) -> str:
        if self.creator and self.creator.full_name:
            return self.creator.full_name
        return "Faculty / Official"

    @property
    def creator_role(self) -> str:
        if self.creator and self.creator.role:
            return self.creator.role.name
        return "Faculty / Official"

    @property
    def department_name(self) -> str:
        if self.creator and self.creator.department:
            return self.creator.department.code or self.creator.department.name
        return "College-Wide"

    @property
    def category_name(self) -> str:
        if self.category and self.category.name:
            return self.category.name
        return "Academics"

    @property
    def remarks(self) -> str | None:
        if self.approvals:
            # Get latest approval remark
            latest = sorted(self.approvals, key=lambda a: a.id)[-1]
            return latest.remarks
        return None

    @property
    def approver_name(self) -> str | None:
        if self.approvals:
            latest = sorted(self.approvals, key=lambda a: a.id)[-1]
            if latest.approver:
                return latest.approver.full_name
        return None

    @property
    def approved_at(self):
        if self.approvals:
            latest = sorted(self.approvals, key=lambda a: a.id)[-1]
            return latest.approved_at
        return None

    @property
    def deliver_speaker(self) -> bool:
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "speaker" in name:
                    return True
        return False

    @property
    def deliver_in_app(self) -> bool:
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "in-app" in name or "feed" in name or "alert" in name or "popup" in name:
                    return True
        return True

    @property
    def deliver_push(self) -> bool:
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "push" in name:
                    return True
        return True

