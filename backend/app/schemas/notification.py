from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationResponse(BaseModel):
    id: int
    announcement_id: int
    user_id: int
    is_read: bool
    created_at: Optional[datetime] = None
    title: Optional[str] = None
    message: Optional[str] = None
    priority: Optional[str] = None
    category: Optional[str] = None

    class Config:
        from_attributes = True
