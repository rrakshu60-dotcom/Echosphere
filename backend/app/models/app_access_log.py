from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.db.database import Base


class AppAccessLog(Base):
    """
    Every app open (launch, return after 5+ minutes away) and session refresh, on every platform.
    Append-only; entries older than 90 days are purged to stay inside the free database tier.
    """

    __tablename__ = "app_access_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    event = Column(String(20), nullable=False)  # launch | resume | refresh
    user_id = Column(Integer, nullable=True, index=True)
    user_name = Column(String(255), nullable=True)
    session_id = Column(Integer, nullable=True)
    platform = Column(String(20), nullable=True)
    app_version = Column(String(30), nullable=True)
    ip = Column(String(64), nullable=True, index=True)
    user_agent = Column(String(300), nullable=True)
