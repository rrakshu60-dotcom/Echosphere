from typing import List
from sqlalchemy.orm import Session
from app.models.notification import Notification

class NotificationService:
    @staticmethod
    def get_user_notifications(db: Session, user_id: int) -> List[Notification]:
        return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()

    @staticmethod
    def mark_as_read(db: Session, notification_id: int, user_id: int) -> bool:
        n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
        if not n:
            return False
        n.is_read = True
        db.commit()
        return True

    @staticmethod
    def mark_as_unread(db: Session, notification_id: int, user_id: int) -> bool:
        n = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
        if not n:
            return False
        n.is_read = False
        db.commit()
        return True

    @staticmethod
    def clear_read(db: Session, user_id: int) -> int:
        """Deletes the user's read alerts (their 'history'); unread alerts and other people's stay."""
        count = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == True).delete(synchronize_session=False)
        db.commit()
        return count

    @staticmethod
    def mark_all_read(db: Session, user_id: int) -> int:
        count = db.query(Notification).filter(Notification.user_id == user_id, Notification.is_read == False).update({"is_read": True})
        db.commit()
        return count
