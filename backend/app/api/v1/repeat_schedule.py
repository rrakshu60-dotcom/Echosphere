from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.repeat_schedule import (
    RepeatScheduleCreate,
    RepeatScheduleResponse,
    RepeatScheduleUpdate,
)
from app.services.repeat_schedule_service import (
    configure_repeat_schedule,
    delete_repeat_schedule,
    evaluate_and_dispatch_repeat_slots,
    get_repeat_schedule_by_announcement,
)

router = APIRouter(tags=["Repeat Schedules"])


@router.put(
    "/announcements/{announcement_id}/repeat-schedule",
    response_model=RepeatScheduleResponse,
    summary="Configure or Modify Notice Repeat Schedule",
    status_code=status.HTTP_200_OK,
)
def set_announcement_repeat_schedule(
    announcement_id: int,
    data: RepeatScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Configures, activates, or retrofits a repeat broadcast schedule for an announcement.
    Enforces speaker delivery, 48-hour event horizon, and max 2-day lifespan bounds.
    """
    schedule = configure_repeat_schedule(
        db=db,
        announcement_id=announcement_id,
        data=data,
        current_user=current_user,
    )
    return schedule


@router.patch(
    "/announcements/{announcement_id}/repeat-schedule",
    response_model=RepeatScheduleResponse,
    summary="Partially Update Notice Repeat Schedule",
    status_code=status.HTTP_200_OK,
)
def patch_announcement_repeat_schedule(
    announcement_id: int,
    data: RepeatScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Partially updates an existing announcement repeat schedule.
    """
    schedule = configure_repeat_schedule(
        db=db,
        announcement_id=announcement_id,
        data=data,
        current_user=current_user,
    )
    return schedule


@router.get(
    "/announcements/{announcement_id}/repeat-schedule",
    response_model=RepeatScheduleResponse,
    summary="Get Announcement Repeat Schedule & Logs",
    status_code=status.HTTP_200_OK,
)
def get_announcement_repeat_schedule(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the repeat schedule configuration and historical execution logs
    for the specified announcement.
    """
    schedule = get_repeat_schedule_by_announcement(db=db, announcement_id=announcement_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No repeat schedule found for Announcement #{announcement_id}.",
        )
    return schedule


@router.delete(
    "/announcements/{announcement_id}/repeat-schedule",
    summary="Delete Announcement Repeat Schedule",
    status_code=status.HTTP_200_OK,
)
def remove_announcement_repeat_schedule(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Removes or deactivates the repeat broadcast schedule for an announcement.
    """
    deleted = delete_repeat_schedule(db=db, announcement_id=announcement_id, current_user=current_user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No repeat schedule found for Announcement #{announcement_id}.",
        )
    return {"status": "success", "message": f"Repeat schedule for Announcement #{announcement_id} removed."}


@router.post(
    "/repeat-schedule/trigger-check",
    summary="Trigger Slot Evaluation Cycle (Daemon / Testing)",
    status_code=status.HTTP_200_OK,
)
def trigger_slot_check(
    simulated_time: Optional[str] = Query(None, description="Simulate specific time in HH:MM format (e.g. 11:05, 13:20, 18:45)"),
    simulated_date: Optional[str] = Query(None, description="Simulate specific date in YYYY-MM-DD format"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Executes a repeat slot check cycle. Can be invoked automatically by background
    timers or manually by administrators/tests with simulated timestamps.
    """
    result = evaluate_and_dispatch_repeat_slots(
        db=db,
        simulated_time_str=simulated_time,
        simulated_date_str=simulated_date,
    )
    return {
        "status": "success",
        "result": result,
    }
