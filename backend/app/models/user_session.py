from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.database import Base


class UserSession(Base):
    """
    One signed-in device. Holds only a hash of the current refresh key; the key itself
    lives on the device and is replaced on every refresh.

    user_id has no foreign key on purpose: sessions are part of the security record and
    must outlive the user account.
    """

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    user_name = Column(String(255), nullable=True)
    refresh_hash = Column(String(64), nullable=False, unique=True, index=True)
    remember_me = Column(Boolean, nullable=False, default=False)
    platform = Column(String(20), nullable=True)
    user_agent = Column(String(300), nullable=True)
    ip = Column(String(64), nullable=True)
    last_ip = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    end_reason = Column(String(30), nullable=True)
    ended_by_user_id = Column(Integer, nullable=True)
