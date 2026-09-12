from typing import Any
from sqlalchemy import Column, Integer, String, Text
from app.db.database import Base
from app.models.base_model import TimestampMixin


class SpeakerCommand(TimestampMixin, Base):
    """
    Stores hardware commands persistently in the database so that
    commands dispatched by any worker process (or cloud container)
    are reliably retrieved by hardware nodes regardless of multi-process isolation.
    """
    __tablename__ = "speaker_commands"

    id: Any = Column(Integer, primary_key=True, index=True)
    command: Any = Column(String(50), nullable=False)
    target_mac: Any = Column(String(50), nullable=True, index=True)
    payload_json: Any = Column(Text, nullable=False)
    delivered_macs: Any = Column(Text, nullable=True, default="")
    status: Any = Column(String(20), nullable=False, default="PENDING")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
