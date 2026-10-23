"""Push notification device registration: the server stores a signed-in device's token so notices of its audience reach it."""
from typing import Literal, Optional

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
    platform: Optional[Literal["web", "android", "ios", "windows", "macos", "linux"]] = None


@router.post("/register")
def register_device(body: DeviceRegistration, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if push.get_firebase_admin_app() is None:
        raise HTTPException(status_code=503, detail="Push notifications are not set up on the server.")
    push.register_device(db, current_user, body.token, body.platform)
    print(f"[PUSH] {body.platform or 'device'} registered", flush=True)
    return {"registered": True}
