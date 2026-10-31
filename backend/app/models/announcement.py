from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
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
    __table_args__ = (
        Index("ix_announcements_status_created_at", "status", "created_at"),
        # Never reuse a deleted notice's ID (SQLite would): the permanent notice record is keyed by it.
        # Postgres sequences never reuse IDs.
        {"sqlite_autoincrement": True},
    )

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
        index=True,
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

    speaker_voice = Column(
        String(20),
        nullable=True,
        default="female",
    )

    # [{"name", "url", "size", "mime"}]: files are kept in cloud storage, not in the database
    attachments = Column(
        JSON,
        nullable=True,
    )

    # -------------------------
    # Foreign Keys
    # -------------------------

    # Plain id, no foreign key: it outlives the author's account.
    created_by = Column(
        Integer,
        nullable=False,
    )

    category_id = Column(
        Integer,
        ForeignKey("announcement_categories.id"),
        nullable=False,
        index=True,
    )

    # -------------------------
    # Relationships
    # -------------------------

    creator = relationship(
        "User",
        primaryjoin="foreign(Announcement.created_by) == User.id",
        back_populates="announcements",
        viewonly=True,
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

    repeat_schedule = relationship(
        "AnnouncementRepeatSchedule",
        back_populates="announcement",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # -------------------------
    # Computed Model Properties
    # -------------------------

    def _saved_creator(self, field: str):
        """The author's details as recorded when the notice was made (used once the account is deleted)."""
        from sqlalchemy.orm import object_session
        from app.models.notice_record import NoticeRecord

        session = object_session(self)
        if session is None or self.id is None:
            return None
        return session.query(getattr(NoticeRecord, field)).filter(NoticeRecord.announcement_id == self.id).scalar()

    @property
    def creator_name(self) -> str:
        if self.creator and self.creator.full_name:
            return self.creator.full_name
        return self._saved_creator("creator_name") or "Faculty / Official"

    @property
    def creator_role(self) -> str:
        if self.creator and self.creator.role:
            return self.creator.role.name
        return self._saved_creator("creator_role") or "Faculty / Official"

    @property
    def department_name(self) -> str:
        if self.creator and self.creator.department:
            return self.creator.department.code or self.creator.department.name
        if self.creator is None:
            return self._saved_creator("creator_department") or "College-Wide"
        return "College-Wide"

    @property
    def category_name(self) -> str:
        if self.category and self.category.name:
            return self.category.name
        return "Academics"

    @property
    def remarks(self) -> str | None:
        approvals = list(self.approvals or []) if self.approvals else []
        if approvals:
            latest = sorted(approvals, key=lambda a: getattr(a, 'id', 0))[-1]
            return latest.remarks
        return None

    @property
    def approver_name(self) -> str | None:
        approvals = list(self.approvals or []) if self.approvals else []
        if approvals:
            latest = sorted(approvals, key=lambda a: getattr(a, 'id', 0))[-1]
            if latest.approver:
                return latest.approver.full_name
        return None

    @property
    def approved_at(self):
        approvals = list(self.approvals or []) if self.approvals else []
        if approvals:
            latest = sorted(approvals, key=lambda a: getattr(a, 'id', 0))[-1]
            return latest.approved_at
        return None

    @property
    def deliver_speaker(self) -> bool:
        if getattr(self, "_deliver_speaker", None) is not None:
            return bool(self._deliver_speaker)
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "speaker" in name:
                    return True
        return False

    @deliver_speaker.setter
    def deliver_speaker(self, value: bool):
        self._deliver_speaker = bool(value)

    @property
    def deliver_in_app(self) -> bool:
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "in-app" in name or "feed" in name or "alert" in name or "popup" in name:
                    return True
            return False
        return True

    @property
    def deliver_push(self) -> bool:
        if self.deliveries:
            for d in self.deliveries:
                name = (d.delivery_type.name if d.delivery_type and d.delivery_type.name else "").lower()
                if "push" in name:
                    return True
            return False
        return True

    @property
    def speaker_node_id(self) -> int | None:
        """The speaker this notice was sent to; None means every speaker."""
        return self.speaker_queue.speaker_node_id if self.speaker_queue else None

