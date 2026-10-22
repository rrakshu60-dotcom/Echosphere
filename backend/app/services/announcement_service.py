import logging
import re
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
from datetime import datetime, timezone
from typing import Optional, Any

from app.models.announcement_approval import AnnouncementApproval
from app.repositories.announcement_approval_repository import create_approval
from app.schemas.announcement import AnnouncementApprovalRequest, BatchModerateRequest

from app.services.audit_log_service import create_audit_log_service
from app.core.websocket_manager import ws_manager


def dispatch_announcement_notifications_and_deliveries(
    db: Session,
    announcement: Announcement,
    deliver_in_app: bool = True,
    deliver_push: bool = True,
    deliver_speaker: bool = False,
    target_audience: Optional[str] = None,
    current_user: Optional[User] = None,
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

        # 3. Dispatch native device Push Notifications via Firebase Cloud Messaging (FCM)
        if deliver_push or str(announcement.priority).upper() in ("URGENT", "EMERGENCY"):
            try:
                from app.services.firebase_push_service import firebase_push_service
                dept_code = None
                if getattr(announcement, "department", None):
                    dept_code = getattr(announcement.department, "code", None)

                cat_name = getattr(announcement.category, "name", "General") if getattr(announcement, "category", None) else "General"

                push_results = firebase_push_service.send_announcement_push(
                    announcement_id=announcement.id,
                    title=announcement.title,
                    description=announcement.description or "",
                    target_audience=target_audience,
                    department_code=dept_code,
                    category=cat_name,
                    priority=str(announcement.priority),
                    audio_url=getattr(announcement, "audio_url", None),
                )
                logger.info(f"Dispatched FCM push notifications for announcement #{announcement.id}: {push_results}")
            except Exception as ex:
                logger.warning(f"Error dispatching FCM push notifications for announcement #{announcement.id}: {ex}")



def _generate_creation_summary(title: str, description: Optional[str]) -> Optional[str]:
    """AI summary for a new notice (falls back to the distilled campus summary)."""
    generated_summary: Optional[str] = None
    from app.services.ai_service import AIService
    try:
        desc_text = (description or "").strip()
        text_to_summarize = desc_text if len(desc_text) > 10 else f"{title}. {desc_text}".strip()
        generated_summary = AIService.summarize(text_to_summarize)
    except Exception as e:
        logger.warning(f"AI summarization attempt failed on creation: {e}")
    if not generated_summary or len(generated_summary.strip()) < 10:
        generated_summary = AIService.distill_qwen_campus_summary((description or "").strip() or title)
    return generated_summary


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
        elif request.scheduled_at and request.scheduled_at > datetime.now(timezone.utc).replace(tzinfo=None):
            initial_status = AnnouncementStatus.SCHEDULED
        else:
            initial_status = AnnouncementStatus.PUBLISHED
    elif user_role in ["Dev Admin", "Developer", "College Admin", "Principal"]:
        if request.scheduled_at and request.scheduled_at > datetime.now(timezone.utc).replace(tzinfo=None):
            initial_status = AnnouncementStatus.SCHEDULED
        else:
            initial_status = AnnouncementStatus.PUBLISHED
    else:
        initial_status = AnnouncementStatus.PENDING_APPROVAL

    speaker_voice = getattr(request, 'speaker_voice', 'female') or 'female'

    # A speaker notice published now must reach the speaker without waiting on an AI call:
    # its summary is generated in the background right after creation instead.
    plays_on_speaker_now = (
        (getattr(request, 'deliver_speaker', False) or bool(getattr(request, 'repeat_schedule', None)))
        and initial_status == AnnouncementStatus.PUBLISHED
    )

    # Generate real institutional AI summary from content
    generated_summary: Optional[str] = None
    if not plays_on_speaker_now:
        generated_summary = _generate_creation_summary(request.title, request.description)

    # Clean any lingering "Summary:" or quotes from final summary
    if generated_summary:
        generated_summary = re.sub(r'^(summary|notice)\s*[:\-–]\s*', '', generated_summary, flags=re.IGNORECASE).strip(' "\'')

    announcement = Announcement(
        title=request.title,
        description=request.description,
        category_id=request.category_id,
        priority=request.priority,
        emergency_level=request.emergency_level,
        scheduled_at=request.scheduled_at,
        target_audience=request.target_audience or "Entire College",
        ai_summary=generated_summary,
        status=initial_status,
        created_by=current_user.id,
        speaker_voice=speaker_voice,
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

    # Proactively pre-render Kokoro-82M neural audio in background so ANY future broadcast/playback has 0.0s delay
    try:
        import threading
        from app.services.tts_service import generate_announcement_audio_sync
        def _bg_synth(ann_id=created_announcement.id, t=created_announcement.title, d=created_announcement.description, v=created_announcement.speaker_voice):
            try:
                generate_announcement_audio_sync(
                    ann_id,
                    f"{t}. {d}",
                    gender=v or "female",
                    include_chime=False,
                )
            except Exception as se:
                logger.debug(f"Proactive background synthesis note: {se}")
        threading.Thread(target=_bg_synth, daemon=True, name=f"PreRender_Ann_{created_announcement.id}").start()
    except Exception as bg_err:
        logger.debug(f"Failed to launch background pre-render: {bg_err}")

    # Multi-channel delivery and notification dispatch
    deliver_speaker = getattr(request, 'deliver_speaker', False)
    deliver_in_app = getattr(request, 'deliver_in_app', True)
    deliver_push = getattr(request, 'deliver_push', True)
    target_audience = getattr(request, 'target_audience', None)

    # Configure repeat schedule immediately if provided
    repeat_sched_data = getattr(request, 'repeat_schedule', None)
    sched_obj = None
    if repeat_sched_data:
        try:
            from app.services.repeat_schedule_service import configure_repeat_schedule
            from app.schemas.repeat_schedule import RepeatScheduleCreate
            sched_create = repeat_sched_data if isinstance(repeat_sched_data, RepeatScheduleCreate) else RepeatScheduleCreate(**repeat_sched_data)
            sched_obj = configure_repeat_schedule(
                db=db,
                announcement_id=created_announcement.id,
                data=sched_create,
                current_user=current_user,
            )
            created_announcement.deliver_speaker = True
            deliver_speaker = True
        except Exception as e:
            logger.warning(f"Error configuring repeat schedule on announcement creation: {e}")

    # Speaker first: it plays now, and notifications / the AI summary must not delay it.
    if deliver_speaker and created_announcement.status in (AnnouncementStatus.PUBLISHED, AnnouncementStatus.SCHEDULED):
        from app.core.emergency_utils import is_emergency_announcement
        is_emerg = is_emergency_announcement(created_announcement)
        try:
            from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
            dept_code = current_user.department.code if (hasattr(current_user, 'department') and current_user.department) else "ALL"
            broadcast_sched_time = created_announcement.scheduled_at
            if sched_obj and not getattr(sched_obj, 'play_on_publish', True) and not broadcast_sched_time:
                broadcast_sched_time = sched_obj.next_repeat_at

            enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=created_announcement.id,
                title=created_announcement.title,
                content=created_announcement.description,
                department_code=dept_code,
                zone="College-Wide",
                is_emergency=is_emerg,
                speaker_node_id=getattr(request, 'speaker_node_id', None),
                scheduled_time=broadcast_sched_time,
                speaker_voice=created_announcement.speaker_voice or "female",
                force_requeue=True,
            )
        except Exception as e:
            logger.warning(f"Auto-broadcast error on announcement creation: {e}")

    if plays_on_speaker_now:
        import threading

        def _summarize_after_create(ann_id=created_announcement.id, t=created_announcement.title, d=created_announcement.description):
            try:
                summary = _generate_creation_summary(t, d)
                if summary:
                    summary = re.sub(r'^(summary|notice)\s*[:\-–]\s*', '', summary, flags=re.IGNORECASE).strip(' "\'')
                    from app.db.database import SessionLocal
                    with SessionLocal() as s2:
                        row = s2.query(Announcement).filter(Announcement.id == ann_id).first()
                        if row and not row.ai_summary:
                            row.ai_summary = summary
                            s2.commit()
            except Exception as se:
                logger.warning(f"Background AI summary after creation note: {se}")
        threading.Thread(target=_summarize_after_create, daemon=True, name=f"Summary_Ann_{created_announcement.id}").start()

    dispatch_announcement_notifications_and_deliveries(
        db=db,
        announcement=created_announcement,
        deliver_in_app=deliver_in_app,
        deliver_push=deliver_push,
        deliver_speaker=deliver_speaker,
        target_audience=target_audience,
        current_user=current_user,
    )

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on announcement creation: {e}")

    # Automatically pre-warm voice audio in background so speech is instantly ready on disk for broadcast
    try:
        import threading
        def _prewarm_new_ann():
            try:
                from app.services.tts_service import generate_announcement_audio_sync
                v = created_announcement.speaker_voice or "female"
                generate_announcement_audio_sync(
                    created_announcement.id,
                    f"{created_announcement.title}. {created_announcement.description}",
                    gender=v,
                    include_chime=False,
                )
            except Exception as e:
                logger.warning(f"Background audio pre-warm on creation note: {e}")
        threading.Thread(target=_prewarm_new_ann, daemon=True).start()
    except Exception:
        pass

    return created_announcement


def get_all_announcements_service(
    db: Session,
    status: str | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int | None = None,
):
    return get_all_announcements(
        db=db,
        status=status,
        category_id=category_id,
        skip=skip,
        limit=limit,
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

    # Manage speaker delivery channel if specified in update request or on publishing/approval
    deliver_speaker = getattr(request, 'deliver_speaker', None)
    try:
        from app.models.delivery_type import DeliveryType
        from app.models.announcement_delivery import AnnouncementDelivery
        spk_type = db.query(DeliveryType).filter(DeliveryType.name.ilike("%speaker%")).first()
        if not spk_type:
            spk_type = DeliveryType(name="Speaker")
            db.add(spk_type)
            db.commit()
            db.refresh(spk_type)

        existing_deliv = db.query(AnnouncementDelivery).filter(
            AnnouncementDelivery.announcement_id == updated_announcement.id,
            AnnouncementDelivery.delivery_type_id == spk_type.id,
        ).first()

        has_speaker_delivery = False
        if deliver_speaker is True:
            if not existing_deliv:
                db.add(AnnouncementDelivery(
                    announcement_id=updated_announcement.id,
                    delivery_type_id=spk_type.id,
                ))
                db.commit()
            has_speaker_delivery = True
        elif deliver_speaker is False:
            if existing_deliv:
                db.delete(existing_deliv)
                db.commit()
            has_speaker_delivery = False
        else:
            has_speaker_delivery = bool(existing_deliv) or getattr(updated_announcement, "deliver_speaker", False)

        if has_speaker_delivery and updated_announcement.status in (AnnouncementStatus.PUBLISHED, AnnouncementStatus.SCHEDULED):
            from app.core.emergency_utils import is_emergency_announcement
            is_emerg = is_emergency_announcement(updated_announcement)
            from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
            dept_code = "ALL"
            if updated_announcement.creator and hasattr(updated_announcement.creator, 'department') and updated_announcement.creator.department:
                dept_code = updated_announcement.creator.department.code
            enqueue_and_broadcast_announcement(
                db=db,
                announcement_id=updated_announcement.id,
                title=updated_announcement.title,
                content=updated_announcement.description,
                department_code=dept_code,
                zone="College-Wide",
                is_emergency=is_emerg,
                speaker_node_id=getattr(request, 'speaker_node_id', None),
                scheduled_time=updated_announcement.scheduled_at,
                speaker_voice=updated_announcement.speaker_voice or "female",
                force_requeue=True,
            )
    except Exception as e:
        logger.warning(f"Speaker delivery update error on announcement {updated_announcement.id}: {e}")

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
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

    setattr(announcement, "status", AnnouncementStatus.PENDING_APPROVAL)

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
        approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    create_approval(
        db,
        approval,
    )

    is_future_sched = bool(announcement.scheduled_at and announcement.scheduled_at > datetime.now(timezone.utc).replace(tzinfo=None))
    target_status = AnnouncementStatus.SCHEDULED if is_future_sched else AnnouncementStatus.PUBLISHED

    updated_announcement = update_announcement(
        db,
        announcement,
        AnnouncementUpdate(
            status=target_status,
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

    has_speaker_delivery = False
    try:
        from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
        dept_code = "ALL"
        if updated_announcement.creator and hasattr(updated_announcement.creator, 'department') and updated_announcement.creator.department:
            dept_code = updated_announcement.creator.department.code
        elif hasattr(current_user, 'department') and current_user.department:
            dept_code = current_user.department.code

        from app.core.emergency_utils import is_emergency_announcement
        is_emerg = is_emergency_announcement(updated_announcement)

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
                scheduled_time=updated_announcement.scheduled_at,
                speaker_voice=updated_announcement.speaker_voice or "female",
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on approval: {e}")

    # Automatically pre-warm voice audio in background so speech is instantly ready on disk for broadcast
    try:
        import threading
        def _prewarm_approved_ann():
            try:
                from app.services.tts_service import generate_announcement_audio_sync
                v = updated_announcement.speaker_voice or "female"
                generate_announcement_audio_sync(
                    updated_announcement.id,
                    f"{updated_announcement.title}. {updated_announcement.description}",
                    gender=v,
                    include_chime=False,
                )
            except Exception as e:
                logger.warning(f"Background audio pre-warm on approval note: {e}")
        threading.Thread(target=_prewarm_approved_ann, daemon=True).start()
    except Exception:
        pass

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
        approved_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    create_approval(
        db,
        approval,
    )

    setattr(announcement, "status", AnnouncementStatus.REJECTED)

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
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on rejection: {e}")

    return {"message": "Announcement rejected successfully."}
 
 
def batch_moderate_service(
    db: Session,
    request: BatchModerateRequest,
    current_user: User,
) -> dict[str, Any]:
    action = request.action.strip().upper()
    if action not in ("APPROVE", "REJECT"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Action must be either 'APPROVE' or 'REJECT'.",
        )
    if not request.ids:
        return {
            "success": True,
            "action": action,
            "processed_count": 0,
            "affected_ids": [],
            "failed_ids": [],
            "message": "No announcements supplied for batch moderation."
        }

    user_role = current_user.role.name if (current_user and current_user.role) else "Student"
    affected_ids = []
    failed_ids = []
    approved_announcements = []

    try:
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        remarks_text = request.remarks or f"Batch {action.lower()}ed by Administrator"

        for ann_id in request.ids:
            announcement = get_announcement_by_id(db, ann_id)
            if not announcement:
                failed_ids.append(ann_id)
                continue

            # Must be pending or draft or submitted
            if announcement.status not in (
                AnnouncementStatus.PENDING_APPROVAL,
                AnnouncementStatus.DRAFT,
                "SUBMITTED",
                "PENDING_APPROVAL",
                "DRAFT",
                "Pending Approval",
            ):
                failed_ids.append(ann_id)
                continue

            # HoD permission checks
            if user_role == "HoD":
                creator_dept_id = announcement.creator.department_id if announcement.creator else None
                if creator_dept_id and current_user.department_id and creator_dept_id != current_user.department_id:
                    failed_ids.append(ann_id)
                    continue
                target = (announcement.target_audience or "").lower()
                if "entire" in target or "all" in target or "institution" in target:
                    failed_ids.append(ann_id)
                    continue

            if action == "APPROVE":
                approval = AnnouncementApproval(
                    announcement_id=announcement.id,
                    approver_id=current_user.id,
                    status="Approved",
                    remarks=remarks_text,
                    approved_at=now_dt,
                )
                db.add(approval)
                setattr(announcement, "status", AnnouncementStatus.PUBLISHED)
                db.add(announcement)
                create_audit_log_service(
                    db=db,
                    user_id=current_user.id,
                    action="BATCH_APPROVE_ANNOUNCEMENT",
                    entity="ANNOUNCEMENT",
                    entity_id=announcement.id,
                    description=f"Batch approved announcement: {announcement.title}",
                )
                affected_ids.append(announcement.id)
                approved_announcements.append(announcement)

            elif action == "REJECT":
                approval = AnnouncementApproval(
                    announcement_id=announcement.id,
                    approver_id=current_user.id,
                    status="Rejected",
                    remarks=remarks_text,
                    approved_at=now_dt,
                )
                db.add(approval)
                setattr(announcement, "status", AnnouncementStatus.REJECTED)
                db.add(announcement)
                create_audit_log_service(
                    db=db,
                    user_id=current_user.id,
                    action="BATCH_REJECT_ANNOUNCEMENT",
                    entity="ANNOUNCEMENT",
                    entity_id=announcement.id,
                    description=f"Batch rejected announcement: {announcement.title}",
                )
                affected_ids.append(announcement.id)

        # Atomic commit for the entire batch transaction
        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"Error during atomic batch moderation transaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Atomic batch moderation transaction failed: {str(e)}",
        )

    # Post-transaction dispatches (Deliveries, WebSocket, Audio Pre-warming)
    if action == "APPROVE":
        for ann in approved_announcements:
            try:
                db.refresh(ann)
                has_spk = False
                from app.core.emergency_utils import is_emergency_announcement
                is_emerg = is_emergency_announcement(ann)
                has_spk = is_emerg
                if not has_spk and ann.deliveries:
                    for deliv in ann.deliveries:
                        if deliv.delivery_type and "speaker" in deliv.delivery_type.name.lower():
                            has_spk = True
                            break

                dept_code = "ALL"
                if ann.creator and hasattr(ann.creator, 'department') and ann.creator.department:
                    dept_code = ann.creator.department.code
                elif hasattr(current_user, 'department') and current_user.department:
                    dept_code = current_user.department.code

                if has_spk:
                    from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
                    enqueue_and_broadcast_announcement(
                        db=db,
                        announcement_id=ann.id,
                        title=ann.title,
                        content=ann.description,
                        department_code=dept_code,
                        zone="College-Wide",
                        is_emergency=is_emerg,
                        speaker_voice=ann.speaker_voice or "female",
                    )

                dispatch_announcement_notifications_and_deliveries(
                    db=db,
                    announcement=ann,
                    deliver_in_app=True,
                    deliver_push=True,
                    deliver_speaker=has_spk,
                    current_user=current_user,
                )
            except Exception as ex:
                logger.warning(f"Batch post-approval broadcast warning on ID #{ann.id}: {ex}")

    # WebSocket broadcast for real-time live feed updates
    try:
        ws_manager.broadcast_sync({
            "event": "BATCH_ANNOUNCEMENTS_MODERATED",
            "action": action,
            "affected_ids": affected_ids,
            "processed_count": len(affected_ids),
            "approver_name": current_user.full_name,
            "remarks": remarks_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.warning(f"WebSocket broadcast error on batch moderation: {e}")

    return {
        "success": True,
        "action": action,
        "processed_count": len(affected_ids),
        "affected_ids": affected_ids,
        "failed_ids": failed_ids,
        "message": f"Successfully {action.lower()}ed {len(affected_ids)} announcement(s)."
    }
 
 
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

    setattr(announcement, "status", AnnouncementStatus.PUBLISHED)

    db.commit()
    db.refresh(announcement)

    try:
        from app.services.hardware_speaker_service import enqueue_and_broadcast_announcement
        dept_code = "ALL"
        if announcement.creator and hasattr(announcement.creator, 'department') and announcement.creator.department:
            dept_code = announcement.creator.department.code
        from app.core.emergency_utils import is_emergency_announcement
        is_emerg = is_emergency_announcement(announcement)

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

    setattr(announcement, "status", AnnouncementStatus.ARCHIVED)

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

    pending_statuses = [
        AnnouncementStatus.PENDING_APPROVAL,
        AnnouncementStatus.DRAFT,
    ]

    if user_role == "Teacher":
        # Teachers track all notices they have authored (submitted, draft, approved, rejected)
        return (
            base_query.filter(Announcement.created_by == current_user.id)
            .order_by(Announcement.created_at.desc())
            .all()
        )

    if user_role == "HoD":
        # HoD reviews pending notices from teachers in their department
        # PLUS any pending notices the HoD created that require Principal review
        hod_dept_id = current_user.department_id

        dept_pending = (
            db.query(Announcement)
            .join(User, Announcement.created_by == User.id)
            .filter(
                Announcement.status.in_(pending_statuses),
                User.department_id == hod_dept_id,
            )
            .options(
                joinedload(Announcement.creator),
                joinedload(Announcement.category),
                selectinload(Announcement.approvals),
                selectinload(Announcement.deliveries),
            )
            .all()
        )
        own_pending = (
            base_query.filter(
                Announcement.created_by == current_user.id,
                Announcement.status.in_(pending_statuses),
            ).all()
        )

        seen = set()
        combined = []
        for a in (dept_pending + own_pending):
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

