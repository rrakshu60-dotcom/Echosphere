import logging
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger("echosphere.announcement")

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
from app.core.websocket_manager import ws_manager


def dispatch_announcement_notifications_and_deliveries(
    db: Session,
    announcement: Announcement,
    deliver_in_app: bool = True,
    deliver_push: bool = True,
    deliver_speaker: bool = False,
    target_audience: str = None,
    current_user: User = None,
):
    from app.models.delivery_type import DeliveryType
    from app.models.announcement_delivery import AnnouncementDelivery
    from app.models.notification import Notification
    from app.models.user import User
    from app.models.department import Department

    # 1. Record delivery channels in AnnouncementDelivery
    channels = []
    if deliver_in_app:
        channels.append("In-App Feed")
    if deliver_push:
        channels.append("Push Notification")
    if deliver_speaker:
        channels.append("Speaker")

    for ch_name in channels:
        try:
            dt = db.query(DeliveryType).filter(DeliveryType.name.ilike(f"%{ch_name}%")).first()
            if not dt:
                dt = DeliveryType(name=ch_name)
                db.add(dt)
                db.commit()
                db.refresh(dt)

            exists = db.query(AnnouncementDelivery).filter(
                AnnouncementDelivery.announcement_id == announcement.id,
                AnnouncementDelivery.delivery_type_id == dt.id,
            ).first()
            if not exists:
                db.add(AnnouncementDelivery(
                    announcement_id=announcement.id,
                    delivery_type_id=dt.id,
                ))
                db.commit()
        except Exception as e:
            logger.warning(f"Error persisting delivery type {ch_name}: {e}")

    # 2. If status is PUBLISHED, generate Notifications for targeted users
    if announcement.status == AnnouncementStatus.PUBLISHED:
        try:
            target_str = (target_audience or "").strip().lower()
            users_query = db.query(User)

            if target_str and not any(k in target_str for k in ["entire", "all", "college"]):
                depts = db.query(Department).all()
                target_dept_id = None
                for d in depts:
                    if d.code.lower() in target_str or d.name.lower() in target_str:
                        target_dept_id = d.id
                        break
                if target_dept_id:
                    users_query = users_query.filter(User.department_id == target_dept_id)

            recipients = users_query.all()
            short_desc = announcement.description[:180] + ("..." if len(announcement.description) > 180 else "")

            existing_user_ids = set(
                row[0] for row in db.query(Notification.user_id).filter(
                    Notification.announcement_id == announcement.id
                ).all()
            )

            new_notifications = []
            for u in recipients:
                if u.id not in existing_user_ids:
                    new_notifications.append(Notification(
                        user_id=u.id,
                        announcement_id=announcement.id,
                        is_read=False,
                    ))

            if new_notifications:
                db.bulk_save_objects(new_notifications)
                db.commit()
                logger.info(f"Generated {len(new_notifications)} notifications for announcement id={announcement.id}")
        except Exception as e:
            logger.warning(f"Error generating notifications for announcement {announcement.id}: {e}")


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

    user_role = current_user.role.name if current_user.role else "Student"

    # RBAC Approval Matrix
    if user_role == "Teacher":
        # Teachers MANDATORILY require approval for ALL notices (whether immediate or scheduled)
        initial_status = AnnouncementStatus.PENDING_APPROVAL
    elif user_role == "HoD":
        # HoD auto-approves for own department; cross-dept / institution-wide notices require approval
        target = (request.target_audience or "").lower()
        dept_name = (current_user.department.code if current_user.department else "").lower() if hasattr(current_user, 'department') and current_user.department else ""
        is_own_dept = dept_name in target and "entire" not in target and "all" not in target
        if not is_own_dept:
            initial_status = AnnouncementStatus.PENDING_APPROVAL
        elif request.scheduled_at and request.scheduled_at > datetime.utcnow():
            initial_status = AnnouncementStatus.SCHEDULED
        else:
            initial_status = AnnouncementStatus.PUBLISHED
    elif user_role in ["Dev Admin", "Developer", "College Admin", "Principal"]:
        if request.scheduled_at and request.scheduled_at > datetime.utcnow():
            initial_status = AnnouncementStatus.SCHEDULED
        else:
            initial_status = AnnouncementStatus.PUBLISHED
    else:
        initial_status = AnnouncementStatus.PENDING_APPROVAL

    announcement = Announcement(
        title=request.title,
        description=request.description,
        category_id=request.category_id,
        priority=request.priority,
        emergency_level=request.emergency_level,
        scheduled_at=request.scheduled_at,
        target_audience=request.target_audience or "Entire College",
        ai_summary=f"Summary: {request.title}",
        status=initial_status,
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
        description=f"Created announcement (status: {initial_status.value}): {created_announcement.title}",
    )

    # Multi-channel delivery and notification dispatch
    deliver_speaker = getattr(request, 'deliver_speaker', False)
    deliver_in_app = getattr(request, 'deliver_in_app', True)
    deliver_push = getattr(request, 'deliver_push', True)
    target_audience = getattr(request, 'target_audience', None)

    dispatch_announcement_notifications_and_deliveries(
        db=db,
        announcement=created_announcement,
        deliver_in_app=deliver_in_app,
        deliver_push=deliver_push,
        deliver_speaker=deliver_speaker,
        target_audience=target_audience,
        current_user=current_user,
    )

    if deliver_speaker and created_announcement.status in (AnnouncementStatus.PUBLISHED, AnnouncementStatus.SCHEDULED):
        p_val = created_announcement.priority.value if hasattr(created_announcement.priority, 'value') else str(created_announcement.priority)
        is_emerg = (p_val == "EMERGENCY")
        try:
            from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
            dept_code = current_user.department.code if (hasattr(current_user, 'department') and current_user.department) else "ALL"
            enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=created_announcement.id,
                title=created_announcement.title,
                content=created_announcement.description,
                department_code=dept_code,
                zone="College-Wide",
                is_emergency=is_emerg,
                speaker_node_id=getattr(request, 'speaker_node_id', None),
                scheduled_time=created_announcement.scheduled_at,
            )
        except Exception as e:
            logger.warning(f"Auto-broadcast error on announcement creation: {e}")

    try:
        ws_manager.broadcast_sync({
            "event": "ANNOUNCEMENT_CREATED",
            "announcement_id": created_announcement.id,
            "title": created_announcement.title,
            "status": created_announcement.status.value if hasattr(created_announcement.status, "value") else str(created_announcement.status),
            "department": created_announcement.department_name,
            "category": created_announcement.category_name,
            "creator_name": current_user.full_name,
            "creator_role": user_role,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on announcement creation: {e}")

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
    current_user: User = None,
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

    # Executive roles can edit announcements at any status; lower roles only DRAFT or own notices
    user_role = current_user.role.name if (current_user and current_user.role) else "Student"
    is_admin = user_role in ["Dev Admin", "Developer", "College Admin", "Principal"]

    if not is_admin:
        if current_user and announcement.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own announcements.",
            )
        if announcement.status not in (AnnouncementStatus.DRAFT, AnnouncementStatus.PENDING_APPROVAL):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft or pending announcements can be edited by non-admins.",
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
        user_id=current_user.id if current_user else announcement.created_by,
        action="UPDATE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=updated_announcement.id,
        description=f"Updated announcement: {updated_announcement.title}",
    )

    return updated_announcement


def delete_announcement_service(
    db: Session,
    announcement_id: int,
    current_user: User = None,
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

    user_role = current_user.role.name if (current_user and current_user.role) else "Student"
    is_admin = user_role in ["Dev Admin", "Developer", "College Admin", "Principal", "HoD"]

    if not is_admin and current_user and announcement.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own announcements.",
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
        user_id=current_user.id if current_user else created_by,
        action="DELETE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=announcement_id_value,
        description=f"Deleted announcement: {announcement_title}",
    )

    try:
        ws_manager.broadcast_sync({
            "event": "ANNOUNCEMENT_DELETED",
            "announcement_id": announcement_id_value,
            "title": announcement_title,
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on delete: {e}")

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

    if announcement.status not in (AnnouncementStatus.PENDING_APPROVAL, AnnouncementStatus.DRAFT, "SUBMITTED", "PENDING_APPROVAL", "DRAFT", "Pending Approval"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or submitted announcements can be approved.",
        )

    user_role = current_user.role.name if (current_user and current_user.role) else "Student"
    if user_role == "HoD":
        creator_dept_id = announcement.creator.department_id if announcement.creator else None
        if creator_dept_id and current_user.department_id and creator_dept_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HoD can only approve announcements from their own department.",
            )
        target = (announcement.target_audience or "").lower()
        if "entire" in target or "all" in target or "institution" in target:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Institution-wide announcements require Principal or College Admin approval.",
            )

    approval = AnnouncementApproval(
        announcement_id=announcement.id,
        approver_id=current_user.id,
        status="Approved",
        remarks=request.remarks or "Approved for publication",
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

    try:
        from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
        dept_code = "ALL"
        if updated_announcement.creator and hasattr(updated_announcement.creator, 'department') and updated_announcement.creator.department:
            dept_code = updated_announcement.creator.department.code
        elif hasattr(current_user, 'department') and current_user.department:
            dept_code = current_user.department.code

        p_val = updated_announcement.priority.value if hasattr(updated_announcement.priority, 'value') else str(updated_announcement.priority)
        is_emerg = (p_val == "EMERGENCY")

        has_speaker_delivery = is_emerg
        if not has_speaker_delivery and updated_announcement.deliveries:
            for deliv in updated_announcement.deliveries:
                if deliv.delivery_type and "speaker" in deliv.delivery_type.name.lower():
                    has_speaker_delivery = True
                    break

        if has_speaker_delivery:
            enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=updated_announcement.id,
                title=updated_announcement.title,
                content=updated_announcement.description,
                department_code=dept_code,
                zone="College-Wide",
                is_emergency=is_emerg,
            )
    except Exception as e:
        logger.warning(f"Auto-broadcast error on announcement approval: {e}")

    # Dispatch in-app and push notifications to recipients upon approval
    dispatch_announcement_notifications_and_deliveries(
        db=db,
        announcement=updated_announcement,
        deliver_in_app=True,
        deliver_push=True,
        deliver_speaker=has_speaker_delivery,
        current_user=current_user,
    )

    try:
        ws_manager.broadcast_sync({
            "event": "ANNOUNCEMENT_APPROVED",
            "announcement_id": updated_announcement.id,
            "title": updated_announcement.title,
            "status": "PUBLISHED",
            "approver_name": current_user.full_name,
            "remarks": request.remarks or "Approved for publication",
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on approval: {e}")

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

    if announcement.status not in (AnnouncementStatus.PENDING_APPROVAL, AnnouncementStatus.DRAFT, "SUBMITTED", "PENDING_APPROVAL", "DRAFT", "Pending Approval"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or submitted announcements can be rejected.",
        )

    user_role = current_user.role.name if (current_user and current_user.role) else "Student"
    if user_role == "HoD":
        creator_dept_id = announcement.creator.department_id if announcement.creator else None
        if creator_dept_id and current_user.department_id and creator_dept_id != current_user.department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HoD can only reject announcements from their own department.",
            )

    approval = AnnouncementApproval(
        announcement_id=announcement.id,
        approver_id=current_user.id,
        status="Rejected",
        remarks=request.remarks or "Rejected by reviewer",
        approved_at=datetime.utcnow(),
    )

    create_approval(
        db,
        approval,
    )

    announcement.status = AnnouncementStatus.REJECTED

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

    try:
        ws_manager.broadcast_sync({
            "event": "ANNOUNCEMENT_REJECTED",
            "announcement_id": announcement.id,
            "title": announcement.title,
            "status": "REJECTED",
            "approver_name": current_user.full_name,
            "remarks": request.remarks or "Rejected by reviewer",
            "timestamp": datetime.utcnow().isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on rejection: {e}")

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

    try:
        from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
        dept_code = "ALL"
        if announcement.creator and hasattr(announcement.creator, 'department') and announcement.creator.department:
            dept_code = announcement.creator.department.code
        p_val = announcement.priority.value if hasattr(announcement.priority, 'value') else str(announcement.priority)
        is_emerg = (p_val == "EMERGENCY")

        has_speaker_delivery = is_emerg
        if not has_speaker_delivery and announcement.deliveries:
            for deliv in announcement.deliveries:
                if deliv.delivery_type and "speaker" in deliv.delivery_type.name.lower():
                    has_speaker_delivery = True
                    break

        if has_speaker_delivery:
            enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=announcement.id,
                title=announcement.title,
                content=announcement.description,
                department_code=dept_code,
                zone="College-Wide",
                is_emergency=is_emerg,
            )
    except Exception as e:
        logger.warning(f"Auto-broadcast error on announcement publish: {e}")

    return {"message": "Announcement published successfully."}


def archive_announcement_service(
    db: Session,
    announcement_id: int,
    current_user: User = None,
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

    # Persist in AnnouncementArchive table
    try:
        from app.models.announcement_archive import AnnouncementArchive
        archived_record = db.query(AnnouncementArchive).filter(AnnouncementArchive.original_announcement_id == announcement.id).first()
        if not archived_record:
            archived_record = AnnouncementArchive(
                original_announcement_id=announcement.id,
                title=announcement.title,
                description=announcement.description,
                priority=announcement.priority.value if hasattr(announcement.priority, 'value') else str(announcement.priority),
                emergency_level=announcement.emergency_level.value if hasattr(announcement.emergency_level, 'value') else str(announcement.emergency_level),
                created_by=announcement.created_by,
            )
            db.add(archived_record)
            db.commit()
    except Exception as e:
        logger.warning(f"Error persisting AnnouncementArchive record: {e}")

    # Create system audit log
    create_audit_log_service(
        db=db,
        user_id=current_user.id if current_user else announcement.created_by,
        action="ARCHIVE_ANNOUNCEMENT",
        entity="ANNOUNCEMENT",
        entity_id=announcement.id,
        description=f"Archived announcement: {announcement.title}",
    )

    return {"message": "Announcement archived successfully."}


def get_approval_queue_service(
    db: Session,
    current_user: User,
) -> list[Announcement]:
    from sqlalchemy.orm import joinedload, selectinload
    user_role = current_user.role.name if (current_user and current_user.role) else "Student"

    base_query = db.query(Announcement).options(
        joinedload(Announcement.creator),
        joinedload(Announcement.category),
        selectinload(Announcement.approvals),
        selectinload(Announcement.deliveries),
    )

    pending_statuses = (
        AnnouncementStatus.PENDING_APPROVAL,
        AnnouncementStatus.DRAFT,
        "Pending Approval",
        "PENDING_APPROVAL",
        "SUBMITTED",
        "DRAFT",
    )

    if user_role == "Teacher":
        # Teachers track all notices they have authored (submitted, draft, approved, rejected)
        return (
            base_query.filter(Announcement.created_by == current_user.id)
            .order_by(Announcement.created_at.desc())
            .all()
        )

    if user_role == "HoD":
        # HoD reviews pending notices from teachers in their department
        # PLUS any notices the HoD created that require Principal review
        hod_dept_id = current_user.department_id

        dept_pending = (
            base_query.join(User, Announcement.created_by == User.id)
            .filter(
                Announcement.status.in_(pending_statuses),
                User.department_id == hod_dept_id,
            )
            .all()
        )
        own_notices = (
            base_query.filter(Announcement.created_by == current_user.id).all()
        )

        seen = set()
        combined = []
        for a in (dept_pending + own_notices):
            if a.id not in seen:
                seen.add(a.id)
                combined.append(a)
        combined.sort(key=lambda x: x.created_at if x.created_at else datetime.min, reverse=True)
        return combined

    if user_role in ("Dev Admin", "Developer", "College Admin", "Principal"):
        # Executive roles have college-wide approval authority
        return (
            base_query.filter(Announcement.status.in_(pending_statuses))
            .order_by(Announcement.created_at.desc())
            .all()
        )

    return []

