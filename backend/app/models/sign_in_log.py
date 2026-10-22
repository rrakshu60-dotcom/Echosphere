from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.db.database import Base


class SignInLog(Base):
    """Every sign-in attempt, successful or not. Append-only: entries are never changed or deleted."""

    __tablename__ = "sign_in_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    identifier = Column(String(255), nullable=True, index=True)  # what was typed in
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    role = Column(String(50), nullable=True)
    success = Column(Boolean, nullable=False)
    reason = Column(String(40), nullable=False)  # ok | unknown_user | wrong_password | disabled | employee_id_mismatch
    ip = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(300), nullable=True)
    platform = Column(String(20), nullable=True)
    session_id = Column(Integer, nullable=True)
