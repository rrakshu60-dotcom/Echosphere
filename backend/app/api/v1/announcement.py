import os
import time
import logging
from fastapi import APIRouter, Depends, Request, HTTPException, status, Query, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
    BatchModerateRequest,
    BatchModerateResponse,
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
    batch_moderate_service,
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


@router.get("", response_model=list[AnnouncementResponse], include_in_schema=False)
@router.get("/", response_model=list[AnnouncementResponse])
def get_announcements(
    status: str | None = None,
    category_id: int | None = None,
    skip: int = 0,
    limit: int | None = None,
    db: Session = Depends(get_db),
):
    return get_all_announcements_service(
        db=db,
        status=status,
        category_id=category_id,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/approval-queue",
    response_model=list[AnnouncementResponse],
    summary="Get Role-Based Approval Queue",
)
@router.get(
    "/pending",
    response_model=list[AnnouncementResponse],
    summary="Get Pending Approval Queue Alias",
    include_in_schema=False,
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


@router.get("/chimes/{chime_type}/preview")
def preview_chime(chime_type: str):
    """
    Direct preview of any acoustic chime (urgent_academic, events_sports, emergency, standard).
    """
    from app.services.chime_service import get_or_create_chime_wav
    wav_path = get_or_create_chime_wav(chime_type, sample_rate=24000)
    return FileResponse(wav_path, media_type="audio/wav", filename=f"chime_{chime_type}.wav")


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


@router.post(
    "/batch-moderate",
    response_model=BatchModerateResponse,
)
def batch_moderate_announcements(
    request: BatchModerateRequest,
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
    """
    Atomic transaction endpoint for batch approving or rejecting announcements.
    All valid IDs are processed in a single DB commit block, ensuring consistent state.
    """
    return batch_moderate_service(
        db=db,
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


def _find_cached_audio_file(
    announcement_id: int,
    tag: str,
    chime: str | None = None,
    include_chime: bool = True,
    prefer_wav: bool = False,
) -> tuple[str | None, str | None, str | None]:
    from app.services.tts_service import STATIC_AUDIO_DIR
    if not os.path.exists(STATIC_AUDIO_DIR):
        return None, None, None

    candidates = []
    # If WAV is preferred (e.g. ESP32 hardware streaming), prioritize WAV candidates FIRST
    if prefer_wav:
        if not include_chime:
            candidates.append(f"announcement_{announcement_id}_{tag}_nochime.wav")
            candidates.append(f"announcement_{announcement_id}_{tag}.wav")
            candidates.append(f"announcement_{announcement_id}_{tag}_nochime.mp3")
        if chime:
            candidates.append(f"announcement_{announcement_id}_{tag}_{chime}.wav")
            candidates.append(f"announcement_{announcement_id}_{tag}_{chime}.mp3")
        candidates.append(f"announcement_{announcement_id}_{tag}.wav")
        candidates.append(f"announcement_{announcement_id}_{tag}.mp3")
        for c in ["urgent_academic", "events_sports", "emergency", "standard"]:
            candidates.append(f"announcement_{announcement_id}_{tag}_{c}.wav")
            candidates.append(f"announcement_{announcement_id}_{tag}_{c}.mp3")
    else:
        if not include_chime:
            candidates.append(f"announcement_{announcement_id}_{tag}_nochime.mp3")
            candidates.append(f"announcement_{announcement_id}_{tag}_nochime.wav")
        if chime:
            candidates.append(f"announcement_{announcement_id}_{tag}_{chime}.mp3")
            candidates.append(f"announcement_{announcement_id}_{tag}_{chime}.wav")
        candidates.append(f"announcement_{announcement_id}_{tag}.mp3")
        candidates.append(f"announcement_{announcement_id}_{tag}.wav")
        for c in ["urgent_academic", "events_sports", "emergency", "standard"]:
            candidates.append(f"announcement_{announcement_id}_{tag}_{c}.mp3")
            candidates.append(f"announcement_{announcement_id}_{tag}_{c}.wav")

    from app.services.tts_service import is_legacy_beep_file
    from app.services.cloud_storage_service import CloudStorageService

    for filename in candidates:
        filepath = os.path.join(STATIC_AUDIO_DIR, filename)
        if not os.path.exists(filepath):
            restored = CloudStorageService.restore_file_from_cdn_if_missing(filename, folder="audio_streams")
            if restored and os.path.exists(restored):
                filepath = restored
        if os.path.exists(filepath):
            if is_legacy_beep_file(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
                continue
            if os.path.getsize(filepath) > 512:
                media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
                return filename, filepath, media_type

    # Specific prefix scan in directory strictly matching requested tag (never cross-matching opposite gender or mode)
    try:
        prefix = f"announcement_{announcement_id}_{tag}"
        for f in os.listdir(STATIC_AUDIO_DIR):
            if f.startswith(prefix) and (f.endswith(".wav") or f.endswith(".mp3")):
                fp = os.path.join(STATIC_AUDIO_DIR, f)
                if is_legacy_beep_file(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
                    continue
                if os.path.getsize(fp) > 512:
                    media_type = "audio/wav" if f.endswith(".wav") else "audio/mpeg"
                    return f, fp, media_type
    except Exception:
        pass
    return None, None, None


@router.get("/{announcement_id}/audio")
def get_announcement_audio_endpoint(
    announcement_id: int,
    request: Request,
    gender: str | None = None,
    accent: str = "american",
    is_summary: bool = False,
    include_chime: bool = True,
    chime: str | None = None,
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    """
    Returns the synthesized audio stream metadata and URL for an announcement.
    Supports Kokoro-82M offline neural TTS with female/male voices and American, Indian, and British accents.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync
    from app.services.ai_service import AIService
    from app.services.chime_service import resolve_contextual_chime
    from app.services.cloud_storage_service import CloudStorageService

    notice = get_announcement_by_id(db, announcement_id)
    if not gender:
        if notice and getattr(notice, "speaker_voice", None):
            gender = str(notice.speaker_voice).lower()
        else:
            gender = "female"

    clean_accent = (accent or "american").lower()
    clean_gender = (gender or "female").lower()
    base_url = str(request.base_url).rstrip("/")
    tag = f"{clean_accent}_{clean_gender}"
    if is_summary:
        tag += "_summary"

    fname, fpath, mtype = (None, None, None) if regenerate else _find_cached_audio_file(announcement_id, tag, chime)
    if fname and fpath:
        public_url = CloudStorageService.get_public_url("audio_streams", fname)
        if not public_url.startswith("http"):
            public_url = f"{base_url}{public_url}"
        return {
            "status": "ready",
            "audio_url": public_url,
            "file_name": fname,
            "engine": "Neural Speech (Cached)",
            "type": "wav" if fname.endswith(".wav") else "mp3",
            "chime": chime or "standard",
        }
    if notice:
        notice_priority = str(getattr(notice, "priority", "NORMAL") or "NORMAL")
        cat_attr = getattr(notice, "category", None)
        notice_category = str(getattr(cat_attr, "name", cat_attr) or "General")
        notice_emergency = str(getattr(notice, "emergency_level", "NORMAL") or "NORMAL")
        notice_title = str(getattr(notice, "title", "") or "")
        notice_desc = str(getattr(notice, "description", "") or "")

        selected_chime = chime or resolve_contextual_chime(
            priority=notice_priority,
            category=notice_category,
            emergency_level=notice_emergency,
            title=notice_title,
            content=notice_desc,
        )
        if is_summary:
            summary = getattr(notice, "ai_summary", None) or AIService.summarize(notice_desc)
            speech_text = f"Executive Summary of notice: {notice_title}. {summary}"
        else:
            speech_text = f"{notice_title}. {notice_desc}"
    else:
        speech_text = f"Notice Number {announcement_id}. Official campus announcement broadcast."
        selected_chime = chime or "standard"
        notice_priority = "NORMAL"
        notice_category = "General"
        notice_emergency = "NORMAL"

    try:
        res = generate_announcement_audio_sync(
            announcement_id=announcement_id,
            text=speech_text,
            gender=clean_gender,
            accent=clean_accent,
            is_summary=is_summary,
            include_chime=include_chime,
            chime_type=selected_chime,
            priority=notice_priority,
            category=notice_category,
            emergency_level=notice_emergency,
        )
    except Exception as exc:
        from app.services.chime_service import get_or_create_chime_wav
        wav_fallback = get_or_create_chime_wav(selected_chime)
        res = {
            "url_path": f"/api/v1/announcements/{announcement_id}/chime",
            "file_name": os.path.basename(wav_fallback),
            "engine": "Campus Notice Chime",
            "voice": "Institutional Chime",
            "type": "wav",
            "duration_sec": 3.0,
        }
    audio_url = res.get("public_url")
    if not audio_url or not audio_url.startswith("http"):
        audio_url = f"{base_url}{res['url_path']}"
    return {
        "status": "ready",
        "audio_url": audio_url,
        "file_name": res["file_name"],
        "engine": res.get("engine", "Kokoro-82M"),
        "voice": res.get("voice"),
        "type": res.get("type", "wav"),
        "duration_sec": res.get("duration_sec"),
    }


def _stream_file_with_preemption_check(
    fpath: str,
    media_type: str,
    filename: str,
    announcement_id: int,
    db: Session,
):
    from app.services.hardware_speaker_service import is_global_emergency_active
    from app.core.emergency_utils import is_emergency_announcement
    from app.repositories.announcement_repository import get_announcement_by_id

    notice = get_announcement_by_id(db, announcement_id)
    is_emergency = is_emergency_announcement(notice) if notice else False

    # Emergency audio streams must NEVER be preempted
    if is_emergency or not fpath or not os.path.exists(fpath):
        return FileResponse(fpath, media_type=media_type, filename=filename)

    file_size = os.path.getsize(fpath)
    stream_start_time = time.time()

    def audio_chunk_generator():
        try:
            with open(fpath, "rb") as af:
                while True:
                    # If an emergency was triggered while this non-emergency notice was streaming, ABORT!
                    if is_global_emergency_active(stream_start_time):
                        logger.warning(
                            f"🚨 [STREAM CUT] Non-emergency audio stream #{announcement_id} "
                            f"preempted by incoming emergency override! Closing socket immediately."
                        )
                        break
                    chunk = af.read(4096)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.warning(f"Audio chunk generator closed: {e}")

    return StreamingResponse(
        audio_chunk_generator(),
        media_type=media_type,
        headers={
            "Content-Length": str(file_size),
            "Content-Disposition": f'inline; filename="{filename}"',
            "Accept-Ranges": "bytes",
        },
    )


@router.get("/{announcement_id}/audio/stream")
def stream_announcement_audio_endpoint(
    announcement_id: int,
    gender: str = "female",
    accent: str = "american",
    is_summary: bool = False,
    include_chime: bool = True,
    chime: str | None = None,
    lang: str = "en",
    audio_format: str = Query("wav", description="Audio format: 'wav' (lossless PCM for ESP32/speakers) or 'mp3'"),
    regenerate: bool = False,
    db: Session = Depends(get_db),
):
    """
    Directly streams the audio file (WAV or MP3) for an announcement with contextual intro chime.
    Supports 16-bit PCM WAV for ESP32 I2S hardware streaming and regional languages.
    """
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync
    from app.services.chime_service import resolve_contextual_chime
    from app.services.ai_service import AIService
    from app.services.translation_service import TranslationService
    clean_lang = TranslationService.normalize_language_code(lang) if lang else "en"
    clean_accent = (accent or "american").lower()
    clean_gender = (gender or "female").lower()
    tag = f"{clean_accent}_{clean_gender}"
    if is_summary:
        tag += "_summary"
    if clean_lang != "en":
        tag += f"_{clean_lang}"

    fname, fpath, mtype = (None, None, None) if regenerate else _find_cached_audio_file(
        announcement_id,
        tag,
        chime,
        include_chime=include_chime,
        prefer_wav=(audio_format.lower() == "wav"),
    )
    
    # If WAV is requested for ESP32 I2S playback, ensure WAV file format
    if audio_format.lower() == "wav" and fpath and fpath.endswith(".mp3"):
        wav_path = fpath[:-4] + ".wav"
        if not os.path.exists(wav_path):
            try:
                import miniaudio
                decoded = miniaudio.mp3_read_file_s16(fpath)
                miniaudio.wav_write_file(wav_path, decoded)
                fpath = wav_path
                fname = os.path.basename(wav_path)
                mtype = "audio/wav"
            except Exception as me:
                pass
        else:
            fpath = wav_path
            fname = os.path.basename(wav_path)
            mtype = "audio/wav"
    elif audio_format.lower() == "mp3" and fpath and fpath.endswith(".wav"):
        mp3_path = fpath[:-4] + ".mp3"
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 500:
            fpath = mp3_path
            fname = os.path.basename(mp3_path)
            mtype = "audio/mpeg"
        else:
            try:
                from app.services.tts_service import convert_wav_to_mp3
                if convert_wav_to_mp3(fpath, mp3_path):
                    fpath = mp3_path
                    fname = os.path.basename(mp3_path)
                    mtype = "audio/mpeg"
            except Exception:
                pass

    if fname and fpath:
        return _stream_file_with_preemption_check(fpath, mtype, fname, announcement_id, db)

    notice = get_announcement_by_id(db, announcement_id)
    if notice:
        notice_priority = str(getattr(notice, "priority", "NORMAL") or "NORMAL")
        cat_attr = getattr(notice, "category", None)
        notice_category = str(getattr(cat_attr, "name", cat_attr) or "General")
        notice_emergency = str(getattr(notice, "emergency_level", "NORMAL") or "NORMAL")
        notice_title = str(getattr(notice, "title", "") or "")
        notice_desc = str(getattr(notice, "description", "") or "")

        selected_chime = chime or resolve_contextual_chime(
            priority=notice_priority,
            category=notice_category,
            emergency_level=notice_emergency,
            title=notice_title,
            content=notice_desc,
        )
        if is_summary:
            summary = getattr(notice, "ai_summary", None) or AIService.summarize(notice_desc)
            speech_text = f"Executive Summary of notice: {notice_title}. {summary}"
        else:
            speech_text = f"{notice_title}. {notice_desc}"
    else:
        speech_text = f"Notice Number {announcement_id}. Official campus announcement broadcast."
        selected_chime = chime or "standard"
        notice_priority = "NORMAL"
        notice_category = "General"
        notice_emergency = "NORMAL"

    if clean_lang != "en":
        speech_text = TranslationService.translate_text(speech_text, clean_lang)

    try:
        res = generate_announcement_audio_sync(
            announcement_id=announcement_id,
            text=speech_text,
            gender=clean_gender,
            accent=clean_accent,
            is_summary=is_summary,
            include_chime=include_chime,
            chime_type=selected_chime,
            priority=notice_priority,
            category=notice_category,
            emergency_level=notice_emergency,
        )
        file_path = res["file_path"]
        media_type = "audio/wav" if res.get("type") == "wav" else "audio/mpeg"
        file_name = res["file_name"]
    except Exception as exc:
        from app.services.chime_service import get_or_create_chime_wav
        file_path = get_or_create_chime_wav(selected_chime or "standard")
        media_type = "audio/wav"
        file_name = f"chime_{selected_chime or 'standard'}.wav"

    if audio_format.lower() == "wav" and file_path.endswith(".mp3"):
        wav_path = file_path[:-4] + ".wav"
        if not os.path.exists(wav_path):
            try:
                import miniaudio
                decoded = miniaudio.mp3_read_file_s16(file_path)
                miniaudio.wav_write_file(wav_path, decoded)
                file_path = wav_path
                file_name = os.path.basename(wav_path)
                media_type = "audio/wav"
            except Exception as me:
                pass
        else:
            file_path = wav_path
            file_name = os.path.basename(wav_path)
            media_type = "audio/wav"
    elif audio_format.lower() == "mp3" and file_path.endswith(".wav"):
        mp3_path = file_path[:-4] + ".mp3"
        if os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 500:
            file_path = mp3_path
            file_name = os.path.basename(mp3_path)
            media_type = "audio/mpeg"
        else:
            try:
                from app.services.tts_service import convert_wav_to_mp3
                if convert_wav_to_mp3(file_path, mp3_path):
                    file_path = mp3_path
                    file_name = os.path.basename(mp3_path)
                    media_type = "audio/mpeg"
            except Exception:
                pass

    return _stream_file_with_preemption_check(file_path, media_type, file_name, announcement_id, db)


@router.get("/{announcement_id}/chime")
def get_announcement_chime(
    announcement_id: int,
    chime: str | None = None,
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

    notice_priority = str(getattr(notice, "priority", "NORMAL") or "NORMAL")
    cat_attr = getattr(notice, "category", None)
    notice_category = str(getattr(cat_attr, "name", cat_attr) or "General")
    notice_emergency = str(getattr(notice, "emergency_level", "NORMAL") or "NORMAL")
    notice_title = str(getattr(notice, "title", "") or "")
    notice_desc = str(getattr(notice, "description", "") or "")

    chime_type = chime or resolve_contextual_chime(
        priority=notice_priority,
        category=notice_category,
        emergency_level=notice_emergency,
        title=notice_title,
        content=notice_desc,
    )
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

    notice_desc = str(getattr(notice, "description", "") or "")
    notice_title = str(getattr(notice, "title", "") or "")
    summary = AIService.summarize(notice_desc)
    if summary and summary != getattr(notice, "ai_summary", None):
        notice.ai_summary = summary
        try:
            db.commit()
            db.refresh(notice)
        except Exception:
            db.rollback()
    return {
        "status": "ready",
        "announcement_id": announcement_id,
        "title": notice_title,
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

    notice_title = str(getattr(notice, "title", "") or "")
    notice_desc = str(getattr(notice, "description", "") or "")
    event_data = AIService.extract_calendar_event(notice_title, notice_desc)
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

    title = str(request.title or getattr(notice, "title", "") or "")
    content = str(request.content or getattr(notice, "description", "") or "")
    raw_summary = request.summary or getattr(notice, "ai_summary", None)
    summary = str(raw_summary) if raw_summary else None

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
        raw_text=request.raw_text,
    )


@router.post("/attachments/upload")
async def upload_attachment_file(
    file: UploadFile = File(...),
):
    """
    Circular Attachment Cloud Storage Uploader.
    Uploads institutional circulars, scanned orders, images, or PDFs to Hugging Face Datasets CDN.
    Guarantees 100% free, unlimited, permanent storage with direct raw Cloudflare CDN URLs.
    """
    from app.services.cloud_storage_service import CloudStorageService

    content = await file.read()
    filename = file.filename or "attachment.bin"
    res = CloudStorageService.upload_bytes(content, filename=filename, folder="attachments")

    return {
        "status": "success",
        "file_name": res["file_name"],
        "file_url": res["public_url"],
        "cdn_url": res.get("cdn_url"),
        "local_url": res["local_url"],
        "size_bytes": len(content),
        "mime_type": file.content_type or "application/octet-stream",
        "storage_mode": res.get("storage_mode", "local_static"),
    }


@router.get("/attachments/{filename}")
def get_attachment_file(filename: str):
    """
    Retrieves or streams a circular attachment document.
    If container disk was wiped during sleep/restart, automatically restores from CDN.
    """
    from app.services.cloud_storage_service import CloudStorageService, STATIC_DIR

    static_file = os.path.join(STATIC_DIR, "attachments", filename)
    if not os.path.exists(static_file):
        restored = CloudStorageService.restore_file_from_cdn_if_missing(filename, folder="attachments")
        if restored and os.path.exists(restored):
            static_file = restored

    if os.path.exists(static_file):
        return FileResponse(static_file, filename=filename)

    cdn_url = CloudStorageService.get_public_url("attachments", filename)
    if cdn_url.startswith("http"):
        return RedirectResponse(url=cdn_url)

    raise HTTPException(status_code=404, detail="Attachment not found.")
