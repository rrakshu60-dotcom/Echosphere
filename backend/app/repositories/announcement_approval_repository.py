from sqlalchemy.orm import Session

from app.models.announcement_approval import AnnouncementApproval


def create_approval(
    db: Session,
    approval: AnnouncementApproval,
) -> AnnouncementApproval:
    db.add(approval)
    db.commit()
    db.refresh(approval)

    return approval


def get_approvals_by_announcement_id(
    db: Session,
    announcement_id: int,
) -> list[AnnouncementApproval]:
    return (
        db.query(AnnouncementApproval)
        .filter(AnnouncementApproval.announcement_id == announcement_id)
        .order_by(AnnouncementApproval.created_at.desc())
        .all()
    )


def get_latest_approval(
    db: Session,
    announcement_id: int,
) -> AnnouncementApproval | None:
    return (
        db.query(AnnouncementApproval)
        .filter(AnnouncementApproval.announcement_id == announcement_id)
        .order_by(AnnouncementApproval.id.desc())
        .first()
    )
