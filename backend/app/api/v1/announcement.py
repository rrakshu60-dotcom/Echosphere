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
from app.schemas.ai_schema import (
    AnnouncementTranslationRequest,
    AnnouncementTranslationResponse,
    AudienceCheckRequest,
    AudienceCheckResponse,
    DocumentOcrRequest,
    DocumentOcrResponse,
    RelevanceScoreRequest,
    RelevanceScoreResponse,
    ScheduleConflictCheckRequest,
    ScheduleConflictCheckResponse,
    VoiceNoticeRequest,
    VoiceNoticeResponse,
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
    get_approval_queue_service,
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
    "/approval-queue",
    response_model=list[AnnouncementResponse],
    summary="Get Role-Based Approval Queue",
)
def get_approval_queue(
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
    return get_approval_queue_service(
        db=db,
        current_user=current_user,
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
        summary = AIService.summarize(notice.description)
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
    include_chime: bool = True,
    chime: str = None,
    lang: str = "en",
    db: Session = Depends(get_db),
):
    """
    Directly streams the audio file (WAV or MP3) for an announcement with contextual intro chime.
    Supports regional language playback (Kannada, Hindi, Telugu, Tamil).
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync, STATIC_AUDIO_DIR
    from app.services.chime_service import resolve_contextual_chime
    from app.services.ai_service import AIService
    from app.services.translation_service import TranslationService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    selected_chime = chime or resolve_contextual_chime(
        priority=notice.priority,
        category=notice.category,
        emergency_level=notice.emergency_level,
        title=notice.title,
        content=notice.description,
    )

    clean_lang = TranslationService.normalize_language_code(lang)
    tag = f"{accent.lower()}_{gender.lower()}"
    if is_summary:
        tag += "_summary"
    if clean_lang != "en":
        tag += f"_{clean_lang}"
    if include_chime:
        tag += f"_{selected_chime}"
    else:
        tag += "_nochime"

    wav_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.wav")
    mp3_path = os.path.join(STATIC_AUDIO_DIR, f"announcement_{announcement_id}_{tag}.mp3")

    if os.path.exists(wav_path) and os.path.getsize(wav_path) > 1024:
        return FileResponse(wav_path, media_type="audio/wav", filename=f"announcement_{announcement_id}_{tag}.wav")
    if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 1024:
        return FileResponse(mp3_path, media_type="audio/mpeg", filename=f"announcement_{announcement_id}_{tag}.mp3")

    if is_summary:
        summary = AIService.summarize(notice.description)
        speech_text = f"Executive Summary of notice: {notice.title}. {summary}"
    else:
        speech_text = f"{notice.title}. {notice.description}"

    if clean_lang != "en":
        speech_text = TranslationService.translate_text(speech_text, clean_lang)

    res = generate_announcement_audio_sync(
        announcement_id=announcement_id,
        text=speech_text,
        gender=gender,
        accent=accent,
        is_summary=is_summary,
        include_chime=include_chime,
        chime_type=selected_chime,
        priority=notice.priority,
        category=notice.category,
        emergency_level=notice.emergency_level,
    )
    file_path = res["file_path"]
    media_type = "audio/wav" if res.get("type") == "wav" else "audio/mpeg"
    return FileResponse(file_path, media_type=media_type, filename=res["file_name"])


@router.get("/{announcement_id}/chime")
def get_announcement_chime(
    announcement_id: int,
    chime: str = None,
    db: Session = Depends(get_db),
):
    """
    Returns standalone preview audio of the contextual chime for this announcement.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.chime_service import resolve_contextual_chime, get_or_create_chime_wav

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    chime_type = chime or resolve_contextual_chime(
        priority=notice.priority,
        category=notice.category,
        emergency_level=notice.emergency_level,
        title=notice.title,
        content=notice.description,
    )
    wav_path = get_or_create_chime_wav(chime_type, sample_rate=24000)
    return FileResponse(wav_path, media_type="audio/wav", filename=f"chime_{chime_type}.wav")


@router.get("/chimes/{chime_type}/preview")
def preview_chime(chime_type: str):
    """
    Direct preview of any acoustic chime (urgent_academic, events_sports, emergency, standard).
    """
    from app.services.chime_service import get_or_create_chime_wav
    wav_path = get_or_create_chime_wav(chime_type, sample_rate=24000)
    return FileResponse(wav_path, media_type="audio/wav", filename=f"chime_{chime_type}.wav")


@router.get("/{announcement_id}/summary")
@router.post("/{announcement_id}/summarize")
def get_announcement_summary_endpoint(
    announcement_id: int,
    db: Session = Depends(get_db),
):
    """
    Returns an institutional text summary for an announcement using the fine-tuned Qwen 2.5 3B model / AI router.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.ai_service import AIService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    summary = AIService.summarize(notice.description)
    return {
        "status": "ready",
        "announcement_id": announcement_id,
        "title": notice.title,
        "summary": summary,
        "model_used": "Fine-Tuned Qwen 2.5 3B (Local Campus Model)",
    }


@router.get("/{announcement_id}/calendar-event")
def get_announcement_calendar_event_endpoint(
    announcement_id: int,
    db: Session = Depends(get_db),
):
    """
    Extracts dates, deadlines, and actionable calendar items from the announcement text using AI.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.ai_service import AIService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    event_data = AIService.extract_calendar_event(notice.title, notice.description)
    return {
        "status": "success",
        "announcement_id": announcement_id,
        "event": event_data,
    }


@router.post("/check-conflict", response_model=ScheduleConflictCheckResponse)
def check_schedule_conflict_endpoint(
    request: ScheduleConflictCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI Schedule Conflict & Overlap Detector.
    Scans existing circulars to detect venue collisions or conflicting major events before publishing.
    """
    import datetime
    from app.services.conflict_service import ConflictService

    scheduled_dt = None
    if request.scheduled_at:
        try:
            scheduled_dt = datetime.datetime.fromisoformat(request.scheduled_at)
        except Exception:
            pass

    return ConflictService.detect_schedule_conflicts(
        db=db,
        title=request.title,
        content=request.content,
        scheduled_at=scheduled_dt,
        category=request.category,
        exclude_notice_id=request.exclude_notice_id,
    )


@router.post("/check-audience", response_model=AudienceCheckResponse)
def check_audience_endpoint(
    request: AudienceCheckRequest,
    current_user: User = Depends(get_current_user),
):
    """
    AI Audience Pre-Flight Check (Anti-Spam Guard).
    Analyzes announcement drafts in real-time to prevent accidental campus-wide spam,
    verifying if departmental, batch-specific, or faculty-only notices are targeted appropriately.
    """
    from app.services.audience_guard_service import AudienceGuardService

    return AudienceGuardService.analyze_target_audience(
        title=request.title,
        content=request.content,
        selected_audience=request.selected_audience,
    )


@router.post("/relevance-scores", response_model=RelevanceScoreResponse)
def calculate_relevance_scores_endpoint(
    request: RelevanceScoreRequest,
):
    """
    Contextual Relevance & Feed Scoring.
    Computes personalized relevance scores (0.0 to 1.0) and explanatory reasons
    for a list of announcements based on user department, semester, and role.
    """
    from app.services.relevance_scoring_service import RelevanceScoringService

    user_dict = request.user_profile.model_dump()
    notices_dicts = [a.model_dump() for a in request.announcements]

    results = RelevanceScoringService.calculate_batch(
        user_profile=user_dict,
        announcements=notices_dicts,
    )

    return {"scores": results}


@router.post("/{announcement_id}/translate", response_model=AnnouncementTranslationResponse)
def translate_announcement_endpoint(
    announcement_id: int,
    request: AnnouncementTranslationRequest,
    db: Session = Depends(get_db),
):
    """
    Translates an announcement (title, description, and AI summary) into
    Kannada (kn), Hindi (hi), Telugu (te), or Tamil (ta).
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.translation_service import TranslationService

    notice = get_announcement_by_id(db, announcement_id)
    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    title = request.title or notice.title
    content = request.content or notice.description
    summary = request.summary or getattr(notice, "ai_summary", None)

    return TranslationService.translate_announcement(
        title=title,
        content=content,
        summary=summary,
        target_language=request.target_language,
    )


@router.post("/translate", response_model=AnnouncementTranslationResponse)
def translate_generic_endpoint(
    request: AnnouncementTranslationRequest,
):
    """
    Direct translation of circular draft text or announcements into
    Kannada, Hindi, Telugu, or Tamil.
    """
    from app.services.translation_service import TranslationService

    return TranslationService.translate_announcement(
        title=request.title or "",
        content=request.content or "",
        summary=request.summary,
        target_language=request.target_language,
    )


@router.post("/voice-to-notice", response_model=VoiceNoticeResponse)
def voice_to_notice_endpoint(
    request: VoiceNoticeRequest,
):
    """
    Smart Voice Notice Dictation (Speech-to-Circular AI).
    Transcribes spoken voice memos or converts raw conversational dictation into a structured institutional circular.
    """
    from app.services.smart_intake_service import SmartIntakeService

    return SmartIntakeService.voice_to_notice(
        audio_base64=request.audio_base64,
        audio_format=request.audio_format or "m4a",
        raw_transcript=request.raw_transcript,
    )


@router.post("/ocr-document", response_model=DocumentOcrResponse)
def ocr_document_endpoint(
    request: DocumentOcrRequest,
):
    """
    Circular Document OCR & Auto-Digitizer.
    Reads official scanned paper circulars, images, or PDF documents, extracts clean text,
    and returns a structured institutional circular.
    """
    from app.services.smart_intake_service import SmartIntakeService

    return SmartIntakeService.ocr_document_to_notice(
        file_base64=request.file_base64,
        mime_type=request.mime_type or "image/jpeg",
        filename=request.filename or "circular.jpg",
    )
