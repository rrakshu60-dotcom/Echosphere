from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.db.database import Base


class PushDevice(Base):
    """A signed-in device's push token. Notices are pushed straight to the devices of their audience."""

    __tablename__ = "push_devices"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(Text, nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    platform = Column(String(20), nullable=True)
    # The sign-in session that registered the device: pushes stop once that session ends
    session_id = Column(Integer, nullable=True, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
