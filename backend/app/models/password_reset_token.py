from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class PasswordResetToken(Base):
    """
    Stores password reset tokens for staff/admin users.
    """

    __tablename__ = "password_reset_tokens"

    # -------------------------
    # Primary Key
    # -------------------------

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # -------------------------
    # Foreign Key
    # -------------------------

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # -------------------------
    # Token Details
    # -------------------------

    token = Column(
        String(255),
        unique=True,
        nullable=False,
    )

    expires_at = Column(
        DateTime,
        nullable=False,
    )

    used = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    # -------------------------
    # Relationship
    # -------------------------

    user = relationship(
        "User",
        back_populates="password_reset_tokens",
    )
