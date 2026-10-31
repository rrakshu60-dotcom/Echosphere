from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "official_email"),
    )

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(String(150), nullable=False)

    username = Column(
        String(50),
        unique=True,
        nullable=False,
    )

    official_email = Column(
        String(150),
        unique=True,
        nullable=False,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    employee_id = Column(
        String(30),
        unique=True,
        nullable=True,
    )

    usn = Column(
        String(30),
        unique=True,
        nullable=True,
    )

    semester = Column(Integer, nullable=True)

    section = Column(String(10), nullable=True)

    is_active = Column(Boolean, default=True, nullable=False)

    role_id = Column(
        Integer,
        ForeignKey("roles.id"),
        nullable=False,
    )

    department_id = Column(
        Integer,
        ForeignKey("departments.id"),
        nullable=True,
    )

    role = relationship(
        "Role",
        back_populates="users",
        lazy="joined",
    )

    department = relationship(
        "Department",
        back_populates="users",
        lazy="joined",
    )

    # Announcements, approvals and audit entries keep this user's id after the
    # account is deleted, so these are read-only views. A user's own inbox and
    # reset tokens go with the account.
    announcements = relationship(
        "Announcement",
        primaryjoin="foreign(Announcement.created_by) == User.id",
        back_populates="creator",
        viewonly=True,
    )

    approvals = relationship(
        "AnnouncementApproval",
        primaryjoin="foreign(AnnouncementApproval.approver_id) == User.id",
        back_populates="approver",
        viewonly=True,
    )

    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    audit_logs = relationship(
        "AuditLog",
        primaryjoin="foreign(AuditLog.user_id) == User.id",
        back_populates="user",
        viewonly=True,
    )

    password_reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )
