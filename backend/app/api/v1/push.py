"""Push notification device registration: the server subscribes a signed-in device to its account's topics
(browsers can't subscribe themselves to topics)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.services import firebase_push_service as push

router = APIRouter(prefix="/push", tags=["Push Notifications"])


class DeviceRegistration(BaseModel):
    token: str = Field(min_length=20, max_length=4096)
    platform: Optional[str] = None


@router.post("/register")
def register_device(body: DeviceRegistration, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if push.get_firebase_admin_app() is None:
        raise HTTPException(status_code=503, detail="Push notifications are not set up on the server.")
    topics = push.device_topics(current_user)
    drop = [t for t in push.all_restricted_topics(db) if t not in topics]
    subscribed = push.subscribe_device(body.token, topics, drop=drop)
    # Visible in the service log (no token or account details): how many topics this device joined
    print(f"[PUSH] {body.platform or 'device'} registered: {len(subscribed)}/{len(topics)} topics", flush=True)
    return {"subscribed": subscribed}
