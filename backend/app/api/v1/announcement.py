from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import (
    get_current_user,
    require_roles,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementApprovalRequest,
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from app.services.announcement_service import (
    approve_announcement_service,
    create_announcement_service,
    delete_announcement_service,
    get_all_announcements_service,
    get_announcement_by_id_service,
    submit_announcement_service,
    update_announcement_service,
    reject_announcement_service,
    publish_announcement_service,
    archive_announcement_service,
)

router = APIRouter(
    prefix="/announcements",
    tags=["Announcements"],
)


@router.post(
    "",
    response_model=AnnouncementResponse,
)
def create_announcement(
    request: AnnouncementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return create_announcement_service(
        db=db,
        request=request,
        current_user=current_user,
    )


@router.get("/", response_model=list[AnnouncementResponse])
def get_announcements(
    status: str | None = None,
    category_id: int | None = None,
    db: Session = Depends(get_db),
):
    return get_all_announcements_service(
        db=db,
        status=status,
        category_id=category_id,
    )


@router.get(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
)
def get_announcement_by_id(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_announcement_by_id_service(
        db,
        announcement_id,
    )


@router.put(
    "/{announcement_id}",
    response_model=AnnouncementResponse,
)
def update_announcement(
    announcement_id: int,
    request: AnnouncementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return update_announcement_service(
        db,
        announcement_id,
        request,
    )


@router.delete(
    "/{announcement_id}",
)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return delete_announcement_service(
        db,
        announcement_id,
    )


@router.post(
    "/{announcement_id}/submit",
)
def submit_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return submit_announcement_service(
        db,
        announcement_id,
    )


@router.post(
    "/{announcement_id}/approve",
)
def approve_announcement(
    announcement_id: int,
    request: AnnouncementApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
        )
    ),
):
    return approve_announcement_service(
        db=db,
        announcement_id=announcement_id,
        request=request,
        current_user=current_user,
    )


@router.post(
    "/{announcement_id}/reject",
)
def reject_announcement(
    announcement_id: int,
    request: AnnouncementApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
        )
    ),
):
    return reject_announcement_service(
        db=db,
        announcement_id=announcement_id,
        request=request,
        current_user=current_user,
    )


@router.post("/{announcement_id}/publish")
def publish_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return publish_announcement_service(
        db=db,
        announcement_id=announcement_id,
    )


@router.post("/{announcement_id}/archive")
def archive_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return archive_announcement_service(
        db=db,
        announcement_id=announcement_id,
    )
