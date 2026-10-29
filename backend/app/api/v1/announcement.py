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
from app.core.enums.announcement import AnnouncementStatus
from app.core.roles import STAFF_ROLES, is_staff
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
    AudienceCheckRequest,
    AudienceCheckResponse,
    RelevanceScoreRequest,
    RelevanceScoreResponse,
    ScheduleConflictCheckRequest,
    ScheduleConflictCheckResponse,
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
    current_user: User = Depends(get_current_user),
):
    if not is_staff(current_user):
        # Students only ever see published notices, whatever status they ask for.
        status = AnnouncementStatus.PUBLISHED.value
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

    # 1. Fast local disk check (sub-millisecond, zero network IO)
    for filename in candidates:
        filepath = os.path.join(STATIC_AUDIO_DIR, filename)
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

    # 2. Local prefix scan in directory strictly matching requested tag (sub-millisecond)
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

    # 3. CDN check ONLY for candidates explicitly recorded in the storage manifest
    for filename in candidates:
        restored = CloudStorageService.restore_file_from_cdn_if_missing(filename, folder="audio_streams")
        if restored and os.path.exists(restored):
            if is_legacy_beep_file(restored):
                try:
                    os.remove(restored)
                except Exception:
                    pass
                continue
            if os.path.getsize(restored) > 512:
                media_type = "audio/wav" if filename.endswith(".wav") else "audio/mpeg"
                return filename, restored, media_type

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


def _wav_stream_info(fpath: str) -> tuple[int, float]:
    """Returns (byte_rate, speech_seconds) for a PCM WAV file, or (0, 0.0) if unknown."""
    if not fpath or not fpath.endswith(".wav"):
        return 0, 0.0
    try:
        import wave
        with wave.open(fpath, "rb") as wf:
            rate = wf.getframerate()
            byte_rate = rate * wf.getnchannels() * wf.getsampwidth()
            return byte_rate, (wf.getnframes() / float(rate) if rate else 0.0)
    except Exception:
        return 0, 0.0


def _stream_file_with_preemption_check(
    fpath: str,
    media_type: str,
    filename: str,
    announcement_id: int,
    db: Session,
    queue_id: int | None = None,
    is_speaker_client: bool = False,
):
    """
    Streams notice audio to a speaker and keeps the speaker queue honest:
      - when the first audio chunk goes out, the queue item is stamped as confirmed
        (played_at = speaker_confirmed_at = speech start) with the real speech length,
      - the stream closes as soon as the item stops being 'Playing' (pause / stop / remove /
        skip) or an emergency preempts it, so the speaker stops within about a second,
      - audio is paced just above real time so a cut takes effect quickly.
    """
    import math
    from datetime import datetime, timedelta, timezone
    from app.db.database import SessionLocal
    from app.models.speaker_queue import SpeakerQueue
    from app.services.hardware_speaker_service import is_global_emergency_active, is_announcement_stream_aborted
    from app.services import speaker_playback
    from app.core.emergency_utils import is_emergency_announcement
    from app.repositories.announcement_repository import get_announcement_by_id

    notice = get_announcement_by_id(db, announcement_id)
    is_emergency = is_emergency_announcement(notice) if notice else False

    if not fpath or not os.path.exists(fpath):
        return FileResponse(fpath, media_type=media_type, filename=filename)

    file_size = os.path.getsize(fpath)
    stream_start_time = time.time()
    byte_rate, speech_secs = _wav_stream_info(fpath)

    # Only a real speaker playing a queued notice may confirm playback (never a browser preview)
    sync_queue_id = None
    if queue_id and is_speaker_client:
        q_item = db.query(SpeakerQueue).filter(
            SpeakerQueue.id == queue_id,
            SpeakerQueue.announcement_id == announcement_id,
            SpeakerQueue.status == "Playing",
        ).first()
        sync_queue_id = q_item.id if q_item else None

    def _confirm_playback_started() -> None:
        offset = speaker_playback.EMERGENCY_CHIME_OFFSET_SECONDS if is_emergency else speaker_playback.CHIME_OFFSET_SECONDS
        started = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=offset)
        duration = int(math.ceil(speech_secs)) if speech_secs > 0 else None
        with SessionLocal() as s:
            item = s.query(SpeakerQueue).filter(SpeakerQueue.id == sync_queue_id).first()
            if not item or item.status != "Playing":
                return
            item.played_at = started
            item.speaker_confirmed_at = started
            if duration:
                item.duration_seconds = duration
            s.commit()
            duration = item.duration_seconds or duration or 15
        try:
            from app.core.websocket_manager import ws_manager
            ws_manager.broadcast_sync({
                "event": "QUEUE_SYNC_START",
                "queue_id": sync_queue_id,
                "announcement_id": announcement_id,
                "played_at": started.isoformat(),
                "speaker_confirmed_at": started.isoformat(),
                "duration_seconds": duration,
                "elapsed_seconds": 0,
            })
        except Exception:
            pass

    def _still_playing() -> bool:
        with SessionLocal() as s:
            st = s.query(SpeakerQueue.status).filter(SpeakerQueue.id == sync_queue_id).scalar()
        return st == "Playing"

    def audio_chunk_generator():
        sent = 0
        burst_bytes = int(byte_rate * 1.5) if byte_rate else 24 * 1024
        # Barely above real time: the speaker never starves after the burst, and the server is never
        # more than ~1.5s ahead, so closing the stream stops the speaker almost immediately
        paced_rate = (byte_rate * 1.02) if byte_rate else 50 * 1024
        pace_start = None
        last_check = time.monotonic()
        try:
            with open(fpath, "rb") as af:
                while True:
                    if not is_emergency and is_global_emergency_active(stream_start_time):
                        logger.warning(f"[STREAM CUT] Notice #{announcement_id} preempted by an emergency broadcast.")
                        break
                    if is_announcement_stream_aborted(announcement_id, stream_start_time):
                        logger.warning(f"[STREAM CUT] Notice #{announcement_id} audio stream terminated by explicit abort signal.")
                        break
                    if sync_queue_id and time.monotonic() - last_check >= 0.5:
                        last_check = time.monotonic()
                        if not _still_playing():
                            logger.info(f"[STREAM CUT] Queue item #{sync_queue_id} is no longer playing; closing speaker stream.")
                            break
                    chunk = af.read(4096)
                    if not chunk:
                        break
                    yield chunk
                    if sent == 0 and sync_queue_id:
                        try:
                            _confirm_playback_started()
                        except Exception as ce:
                            logger.warning(f"Speaker playback confirmation failed: {ce}")
                    sent += len(chunk)
                    speaker_playback.mark_stream_active(sync_queue_id)
                    if sent > burst_bytes:
                        if pace_start is None:
                            pace_start = time.monotonic()
                        ahead = (sent - burst_bytes) / paced_rate - (time.monotonic() - pace_start)
                        if ahead > 0:
                            time.sleep(ahead)
        except Exception as e:
            logger.warning(f"Audio chunk generator closed: {e}")
        finally:
            speaker_playback.mark_stream_finished(sync_queue_id)

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
    request: Request,
    gender: str = "female",
    accent: str = "american",
    is_summary: bool = False,
    include_chime: bool = True,
    chime: str | None = None,
    audio_format: str = Query("wav", description="Audio format: 'wav' (lossless PCM for ESP32/speakers) or 'mp3'"),
    regenerate: bool = False,
    queue_id: int | None = None,
    sig: str | None = None,
    db: Session = Depends(get_db),
):
    """
    Directly streams the audio file (WAV or MP3) for an announcement with contextual intro chime.
    Supports 16-bit PCM WAV for ESP32 I2S hardware streaming.
    """
    from app.services.speaker_playback import is_valid_stream_signature, mark_stream_pending
    # Only a URL the backend issued to a speaker (signed) may confirm playback
    is_speaker_client = is_valid_stream_signature(queue_id, sig)
    if is_speaker_client:
        # Hold the queue item while its audio may still be synthesizing (cold cache can take 10s+)
        mark_stream_pending(queue_id)
    from app.repositories.announcement_repository import get_announcement_by_id
    from app.services.tts_service import generate_announcement_audio_sync
    from app.services.chime_service import resolve_contextual_chime
    from app.services.ai_service import AIService
    clean_accent = (accent or "american").lower()
    clean_gender = (gender or "female").lower()
    tag = f"{clean_accent}_{clean_gender}"
    if is_summary:
        tag += "_summary"

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
        return _stream_file_with_preemption_check(fpath, mtype, fname, announcement_id, db, queue_id=queue_id, is_speaker_client=is_speaker_client)

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

    return _stream_file_with_preemption_check(file_path, media_type, file_name, announcement_id, db, queue_id=queue_id, is_speaker_client=is_speaker_client)


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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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


ATTACHMENT_MAX_BYTES = 10 * 1024 * 1024
ATTACHMENT_TYPES = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv", "txt", "png", "jpg", "jpeg", "webp"}


@router.post("/attachments/upload")
async def upload_attachment_file(
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")),
):
    """
    Uploads a notice attachment (staff only, 10 MB max, documents and images) to cloud storage.
    Each upload gets a unique name, so files with the same name never overwrite each other.
    """
    import re as _re
    import uuid
    from app.services.cloud_storage_service import CloudStorageService

    original = os.path.basename(file.filename or "attachment")
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ATTACHMENT_TYPES:
        raise HTTPException(status_code=400, detail="This file type can't be attached. Use a PDF, an image or an Office document.")
    content = await file.read(ATTACHMENT_MAX_BYTES + 1)
    if len(content) > ATTACHMENT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Attachments can be at most 10 MB.")
    safe = _re.sub(r"[^A-Za-z0-9._-]+", "_", original).strip("._") or f"attachment.{ext}"
    filename = f"{uuid.uuid4().hex[:10]}_{safe}"
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

    filename = os.path.basename(filename)
    # Attachments live in cloud storage: redirect there rather than copying them onto the server's disk
    cdn_url = CloudStorageService.get_public_url("attachments", filename)
    if cdn_url.startswith("http"):
        return RedirectResponse(url=cdn_url)

    static_file = os.path.join(STATIC_DIR, "attachments", filename)
    if os.path.exists(static_file):
        return FileResponse(static_file, filename=filename)

    raise HTTPException(status_code=404, detail="Attachment not found.")
