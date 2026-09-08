from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications Module"])

@router.get("/", response_model=List[NotificationResponse])
def list_my_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notifs = NotificationService.get_user_notifications(db=db, user_id=current_user.id)
    result = []
    for n in notifs:
        ann = n.announcement
        result.append(
            NotificationResponse(
                id=n.id,
                announcement_id=n.announcement_id,
                user_id=n.user_id,
                is_read=n.is_read,
                created_at=n.created_at,
                title=ann.title if ann else "Announcement",
                message=ann.description if ann else "",
                priority=ann.priority.value if (ann and hasattr(ann.priority, 'value')) else str(ann.priority) if ann else "NORMAL",
                category=ann.category.name if (ann and ann.category) else "General",
            )
        )
    return result

@router.put("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    success = NotificationService.mark_as_read(db=db, notification_id=notification_id, user_id=current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found.")
    return {"message": "Notification marked as read"}

@router.put("/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    updated = NotificationService.mark_all_read(db=db, user_id=current_user.id)
    return {"message": f"{updated} notifications marked as read"}
