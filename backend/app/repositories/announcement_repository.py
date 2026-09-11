from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.announcement import Announcement
from app.models.announcement_delivery import AnnouncementDelivery
from app.schemas.announcement import AnnouncementUpdate
from app.core.enums.announcement import AnnouncementStatus


def normalize_status_filter(status: str) -> AnnouncementStatus | None:
    if not status:
        return None
    s = status.strip().upper().replace(" ", "_")
    if s in ("PENDING", "SUBMITTED", "PENDING_APPROVAL"):
        return AnnouncementStatus.PENDING_APPROVAL
    if s in ("PUBLISHED", "APPROVED"):
        return AnnouncementStatus.PUBLISHED
    if s == "DRAFT":
        return AnnouncementStatus.DRAFT
    if s == "SCHEDULED":
        return AnnouncementStatus.SCHEDULED
    if s == "ARCHIVED":
        return AnnouncementStatus.ARCHIVED
    if s == "REJECTED":
        return AnnouncementStatus.REJECTED
    for enum_item in AnnouncementStatus:
        if enum_item.name == s or enum_item.value.upper().replace(" ", "_") == s:
            return enum_item
    return None


def create_announcement(
    db: Session,
    announcement: Announcement,
) -> Announcement:
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


def get_announcement_by_id(
    db: Session,
    announcement_id: int,
) -> Announcement | None:
    return (
        db.query(Announcement)
        .options(
            joinedload(Announcement.creator),
            joinedload(Announcement.category),
            selectinload(Announcement.approvals),
            selectinload(Announcement.deliveries).joinedload(AnnouncementDelivery.delivery_type),
        )
        .filter(Announcement.id == announcement_id)
        .first()
    )


def get_all_announcements(
    db: Session,
    status: str | None = None,
    category_id: int | None = None,
    created_by: int | None = None,
):
    query = db.query(Announcement).options(
        joinedload(Announcement.creator),
        joinedload(Announcement.category),
        selectinload(Announcement.approvals),
        selectinload(Announcement.deliveries).joinedload(AnnouncementDelivery.delivery_type),
    )

    if status:
        normalized = normalize_status_filter(status)
        if normalized is not None:
            query = query.filter(Announcement.status == normalized)
        else:
            return []

    if category_id:
        query = query.filter(Announcement.category_id == category_id)

    if created_by:
        query = query.filter(Announcement.created_by == created_by)

    return query.order_by(Announcement.created_at.desc()).all()


def update_announcement(
    db: Session,
    announcement: Announcement,
    update_data: AnnouncementUpdate,
) -> Announcement:
    data = update_data.model_dump(exclude_unset=True)

    for key, value in data.items():
        setattr(announcement, key, value)

    db.commit()
    db.refresh(announcement)

    return announcement


def delete_announcement(
    db: Session,
    announcement: Announcement,
):
    db.delete(announcement)
    db.commit()
