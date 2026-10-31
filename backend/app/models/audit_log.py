from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base
from app.models.base_model import TimestampMixin


class AuditLog(TimestampMixin, Base):
    """
    Stores every important action performed
    by users in the system.

    Used for security, debugging and tracking.
    """

    __tablename__ = "audit_logs"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # User Reference
    # -------------------------

    # Plain id, no foreign key: audit history outlives the account.
    user_id = Column(
        Integer,
        nullable=False,
        index=True,
    )

    # -------------------------
    # Who it was, copied when the entry is written
    # -------------------------

    user_name = Column(String(150), nullable=True)
    user_username = Column(String(50), nullable=True)
    user_email = Column(String(150), nullable=True)
    user_role = Column(String(50), nullable=True)
    user_department = Column(String(100), nullable=True)
    user_employee_id = Column(String(30), nullable=True)
    user_usn = Column(String(30), nullable=True)
    user_semester = Column(Integer, nullable=True)
    user_section = Column(String(10), nullable=True)

    # -------------------------
    # Audit Information
    # -------------------------

    action = Column(
        String(100),
        nullable=False,
    )

    entity = Column(
        String(100),
        nullable=False,
    )

    entity_id = Column(
        Integer,
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    # -------------------------
    # Relationships
    # -------------------------

    user = relationship(
        "User",
        primaryjoin="foreign(AuditLog.user_id) == User.id",
        back_populates="audit_logs",
        viewonly=True,
    )

    def copy_user_details(self, user) -> None:
        """Store who the user is, so the entry still reads right after the account is gone."""
        self.user_name = user.full_name
        self.user_username = user.username
        self.user_email = user.official_email
        self.user_role = user.role.name if user.role else None
        self.user_department = user.department.name if user.department else None
        self.user_employee_id = user.employee_id
        self.user_usn = user.usn
        self.user_semester = user.semester
        self.user_section = user.section
