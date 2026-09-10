import os
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import FileResponse
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
            "Dev Admin",
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
            "Dev Admin",
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return update_announcement_service(
        db=db,
        announcement_id=announcement_id,
        request=request,
        current_user=current_user,
    )


@router.delete(
    "/{announcement_id}",
)
def delete_announcement(
    announcement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return delete_announcement_service(
        db=db,
        announcement_id=announcement_id,
        current_user=current_user,
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
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
            "Principal",
            "HoD",
            "Teacher",
        )
    ),
):
    return publish_announcement_service(
        db=db,
        announcement_id=announcement_id,
    )


@router.post("/{announcement_id}/archive")
def archive_announcement(
    announcement_id: int,
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
    return archive_announcement_service(
        db=db,
        announcement_id=announcement_id,
        current_user=current_user,
    )


@router.get("/{announcement_id}/audio")
def get_announcement_audio_endpoint(
    announcement_id: int,
    request: Request,
    gender: str = "female",
    accent: str = "indian",
    is_summary: bool = False,
    db: Session = Depends(get_db),
):
    """
    Returns the synthesized audio stream metadata and URL for an announcement.
    Supports Kokoro-82M offline neural TTS with female/male voices and Indian/American/British accents.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync, STATIC_AUDIO_DIR
    from app.services.ai_service import AIService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    base_url = str(request.base_url).rstrip("/")
    tag = f"{accent.lower()}_{gender.lower()}"
    if is_summary:
        tag += "_summary"

    wav_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.wav")
    mp3_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.mp3")

    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1024:
        return {
            "status": "ready",
            "audio_url": f"{base_url}/static/audio_streams/announcement_{announcement_id}_{tag}.wav",
            "file_name": f"announcement_{announcement_id}_{tag}.wav",
            "engine": "Kokoro-82M (Offline Neural)",
            "type": "wav",
        }
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1024:
        return {
            "status": "ready",
            "audio_url": f"{base_url}/static/audio_streams/announcement_{announcement_id}_{tag}.mp3",
            "file_name": f"announcement_{announcement_id}_{tag}.mp3",
            "engine": "Neural TTS",
            "type": "mp3",
        }

    # Prepare speech text (Full notice or AI Summary)
    if is_summary:
        summary = AIService.summarize_content(notice.description)
        speech_text = f"Executive Summary of notice: {notice.title}. {summary}"
    else:
        speech_text = f"{notice.title}. {notice.description}"

    res = generate_announcement_audio_sync(
        announcement_id=announcement_id,
        text=speech_text,
        gender=gender,
        accent=accent,
        is_summary=is_summary,
    )
    return {
        "status": "ready",
        "audio_url": f"{base_url}{res['url_path']}",
        "file_name": res["file_name"],
        "engine": res.get("engine", "Kokoro-82M"),
        "voice": res.get("voice"),
        "type": res.get("type", "wav"),
        "duration_sec": res.get("duration_sec"),
    }


@router.get("/{announcement_id}/audio/stream")
def stream_announcement_audio_endpoint(
    announcement_id: int,
    gender: str = "female",
    accent: str = "indian",
    is_summary: bool = False,
    db: Session = Depends(get_db),
):
    """
    Directly streams the audio file (WAV or MP3) for an announcement.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync, STATIC_AUDIO_DIR
    from app.services.ai_service import AIService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    tag = f"{accent.lower()}_{gender.lower()}"
    if is_summary:
        tag += "_summary"

    wav_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.wav")
    mp3_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.mp3")

    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1024:
        return FileResponse(wav_path, media_type="audio/wav", filename=f"announcement_{announcement_id}_{tag}.wav")
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1024:
        return FileResponse(mp3_path, media_type="audio/mpeg", filename=f"announcement_{announcement_id}_{tag}.mp3")

    if is_summary:
        summary = AIService.summarize_content(notice.description)
        speech_text = f"Executive Summary of notice: {notice.title}. {summary}"
    else:
        speech_text = f"{notice.title}. {notice.description}"

    res = generate_announcement_audio_sync(
        announcement_id=announcement_id,
        text=speech_text,
        gender=gender,
        accent=accent,
        is_summary=is_summary,
    )
    file_path = res["file_path"]
    media_type = "audio/wav" if res.get("type") == "wav" else "audio/mpeg"
    return FileResponse(file_path, media_type=media_type, filename=res["file_name"])



