from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.enums.announcement import AnnouncementStatus
from app.models.announcement import Announcement
from app.models.user import User
from app.repositories.announcement_category_repository import (
    get_category_by_id,
)
from app.repositories.announcement_repository import (
    create_announcement,
    get_all_announcements,
    get_announcement_by_id,
    update_announcement,
    delete_announcement,
)
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementUpdate,
)
from datetime import datetime

from app.models.announcement_approval import AnnouncementApproval
from app.repositories.announcement_approval_repository import create_approval
from app.schemas.announcement import AnnouncementApprovalRequest

from app.services.audit_log_service import create_audit_log_service


def create_announcement_service(
    db: Session,
    request: AnnouncementCreate,
    current_user: User,
) -> Announcement:

    category = get_category_by_id(
        db,
        request.category_id,
    )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement category not found.",
        )

    announcement = Announcement(
        title=request.title,
        description=request.description,
        category_id=request.category_id,
        priority=request.priority,
        emergency_level=request.emergency_level,
        scheduled_at=request.scheduled_at,
        status=AnnouncementStatus.DRAFT,
        created_by=current_user.id,
    )

    created_announcement = create_announcement(
        db,
        announcement,
    )

    create_audit_log_service(
        db=db,
        user_id=current_user.id,
        action="CREATE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=created_announcement.id,
        description=f"Created announcement: {created_announcement.title}",
    )

    return created_announcement


def get_all_announcements_service(
    db: Session,
    status: str | None = None,
    category_id: int | None = None,
):
    return get_all_announcements(
        db=db,
        status=status,
        category_id=category_id,
    )


def get_announcement_by_id_service(
    db: Session,
    announcement_id: int,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    return announcement


def update_announcement_service(
    db: Session,
    announcement_id: int,
    request: AnnouncementUpdate,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status != AnnouncementStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft announcements can be edited.",
        )

    if request.category_id is not None:
        category = get_category_by_id(
            db,
            request.category_id,
        )

        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement category not found.",
            )

    updated_announcement = update_announcement(
        db,
        announcement,
        request,
    )

    create_audit_log_service(
        db=db,
        user_id=announcement.created_by,
        action="UPDATE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=updated_announcement.id,
        description=f"Updated announcement: {updated_announcement.title}",
    )

    return updated_announcement


def delete_announcement_service(
    db: Session,
    announcement_id: int,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    # Store details before deleting
    announcement_title = announcement.title
    created_by = announcement.created_by
    announcement_id_value = announcement.id

    delete_announcement(
        db,
        announcement,
    )

    create_audit_log_service(
        db=db,
        user_id=created_by,
        action="DELETE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=announcement_id_value,
        description=f"Deleted announcement: {announcement_title}",
    )

    return {"message": "Announcement deleted successfully."}


def submit_announcement_service(
    db: Session,
    announcement_id: int,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status != AnnouncementStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft announcements can be submitted for approval.",
        )

    announcement.status = AnnouncementStatus.PENDING_APPROVAL

    db.commit()
    db.refresh(announcement)

    return {"message": "Announcement submitted for approval."}


def approve_announcement_service(
    db: Session,
    announcement_id: int,
    request: AnnouncementApprovalRequest,
    current_user: User,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status not in (AnnouncementStatus.PENDING_APPROVAL, AnnouncementStatus.DRAFT, "SUBMITTED", "PENDING_APPROVAL", "DRAFT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or submitted announcements can be approved.",
        )

    approval = AnnouncementApproval(
        announcement_id=announcement.id,
        approver_id=current_user.id,
        status="Approved",
        remarks=request.remarks,
        approved_at=datetime.utcnow(),
    )

    create_approval(
        db,
        approval,
    )

    updated_announcement = update_announcement(
        db,
        announcement,
        AnnouncementUpdate(
            status=AnnouncementStatus.PUBLISHED,
        ),
    )

    db.commit()
    db.refresh(updated_announcement)

    create_audit_log_service(
        db=db,
        user_id=current_user.id,
        action="APPROVE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=updated_announcement.id,
        description=f"Approved announcement: {updated_announcement.title}",
    )

    return {"message": "Announcement approved successfully."}


def reject_announcement_service(
    db: Session,
    announcement_id: int,
    request: AnnouncementApprovalRequest,
    current_user: User,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status not in (AnnouncementStatus.PENDING_APPROVAL, AnnouncementStatus.DRAFT, "SUBMITTED", "PENDING_APPROVAL", "DRAFT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or submitted announcements can be rejected.",
        )

    approval = AnnouncementApproval(
        announcement_id=announcement.id,
        approver_id=current_user.id,
        status="Rejected",
        remarks=request.remarks,
        approved_at=datetime.utcnow(),
    )

    create_approval(
        db,
        approval,
    )

    announcement.status = AnnouncementStatus.DRAFT

    db.commit()
    db.refresh(announcement)

    create_audit_log_service(
        db=db,
        user_id=current_user.id,
        action="REJECT_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=announcement.id,
        description=f"Rejected announcement: {announcement.title}",
    )

    return {"message": "Announcement rejected successfully."}


def publish_announcement_service(
    db: Session,
    announcement_id: int,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status != AnnouncementStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled announcements can be published.",
        )

    announcement.status = AnnouncementStatus.PUBLISHED

    db.commit()
    db.refresh(announcement)

    return {"message": "Announcement published successfully."}


def archive_announcement_service(
    db: Session,
    announcement_id: int,
):
    announcement = get_announcement_by_id(
        db,
        announcement_id,
    )

    if announcement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Announcement not found.",
        )

    if announcement.status != AnnouncementStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published announcements can be archived.",
        )

    announcement.status = AnnouncementStatus.ARCHIVED

    db.commit()
    db.refresh(announcement)

    return {"message": "Announcement archived successfully."}
