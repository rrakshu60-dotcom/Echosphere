"""Push notification device registration: the server subscribes a signed-in device to its account's topics
(browsers can't subscribe themselves to topics)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import User
from app.services import firebase_push_service as push

router = APIRouter(prefix="/push", tags=["Push Notifications"])


class DeviceRegistration(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: Optional[str] = None


@router.post("/register")
def register_device(body: DeviceRegistration, current_user: User = Depends(get_current_user)):
    if push.get_firebase_admin_app() is None:
        raise HTTPException(status_code=503, detail="Push notifications are not set up on the server.")
    topics = push.device_topics(current_user)
    subscribed = push.subscribe_device(body.token, topics)
    return {"subscribed": subscribed}
