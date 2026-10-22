"""
Speaker playback state shared by the audio stream endpoint, the queue daemon and queue actions.

The ESP32 cannot send heartbeats while it streams a notice, so the backend treats
"the speaker is pulling this queue item's audio stream right now" as the proof that
the notice is really playing:
  - the stream endpoint registers the queue item here while it serves audio,
  - the queue daemon never completes an item whose stream is still being pulled,
  - pause / stop / remove change the item's status, and the stream generator
    notices and closes the socket, which makes the speaker stop within ~1-2s.
"""
import json
import logging
import threading
import time
from typing import Dict, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Serializes every speaker-queue state transition (daemon, user actions, enqueue, speaker callbacks).
# Without it a daemon pass can read "nothing playing" while a request starts a notice, and then
# start a second one, leaving two notices 'Playing'. Production runs a single worker process.
QUEUE_LOCK = threading.RLock()


def serialized(fn):
    """Runs fn while holding QUEUE_LOCK."""
    import functools

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        with QUEUE_LOCK:
            return fn(*args, **kwargs)
    return wrapper


def try_serialized(fn, *args, **kwargs):
    """Runs fn only if the queue is not busy; for opportunistic callers like heartbeats."""
    if not QUEUE_LOCK.acquire(blocking=False):
        return None
    try:
        return fn(*args, **kwargs)
    finally:
        QUEUE_LOCK.release()


# Seconds from the first audio chunk leaving the server until the speaker's voice is heard:
# transit through Render's proxy (~1s, measured live), then the local chime and pre-buffer.
CHIME_OFFSET_SECONDS = 1.5
EMERGENCY_CHIME_OFFSET_SECONDS = 1.9

# A stream counts as active if it sent a chunk within this many seconds
_STREAM_IDLE_SECONDS = 5.0

# queue_id -> monotonic time of the last chunk sent to the speaker
_ACTIVE_STREAMS: Dict[int, float] = {}
# queue_id -> monotonic time the speaker requested audio that may still be synthesizing
_PENDING_STREAMS: Dict[int, float] = {}
_PENDING_SECONDS = 60.0
_LOCK = threading.Lock()


def stream_signature(queue_id: int) -> str:
    """HMAC proving a stream URL was issued by the backend for this queue item (only then may it confirm playback)."""
    import hashlib
    import hmac
    from app.core.security import SECRET_KEY
    return hmac.new(SECRET_KEY.encode(), f"speaker-stream:{int(queue_id)}".encode(), hashlib.sha256).hexdigest()[:20]


def signed_stream_query(queue_id: int) -> str:
    return f"queue_id={int(queue_id)}&sig={stream_signature(queue_id)}"


def is_valid_stream_signature(queue_id: Optional[int], sig: Optional[str]) -> bool:
    import hmac
    return bool(queue_id and sig and hmac.compare_digest(stream_signature(queue_id), sig))


def mark_stream_pending(queue_id: Optional[int]) -> None:
    """The speaker asked for this item's audio; it may still be synthesizing (cold cache)."""
    if not queue_id:
        return
    with _LOCK:
        _PENDING_STREAMS[int(queue_id)] = time.monotonic()


def mark_stream_active(queue_id: Optional[int]) -> None:
    if not queue_id:
        return
    with _LOCK:
        _PENDING_STREAMS.pop(int(queue_id), None)
        _ACTIVE_STREAMS[int(queue_id)] = time.monotonic()


def mark_stream_finished(queue_id: Optional[int]) -> None:
    if not queue_id:
        return
    with _LOCK:
        _ACTIVE_STREAMS.pop(int(queue_id), None)
        _PENDING_STREAMS.pop(int(queue_id), None)


def any_stream_busy() -> bool:
    """True while any speaker is pulling audio or waiting for a stream to be synthesized."""
    now = time.monotonic()
    with _LOCK:
        return any(now - t < _STREAM_IDLE_SECONDS for t in _ACTIVE_STREAMS.values()) or any(
            now - t < _PENDING_SECONDS for t in _PENDING_STREAMS.values()
        )


def is_stream_active(queue_id: Optional[int]) -> bool:
    """True while the speaker is pulling this item's audio, or waiting for it to be synthesized."""
    if not queue_id:
        return False
    now = time.monotonic()
    with _LOCK:
        last = _ACTIVE_STREAMS.get(int(queue_id))
        pending = _PENDING_STREAMS.get(int(queue_id))
    return (last is not None and now - last < _STREAM_IDLE_SECONDS) or (pending is not None and now - pending < _PENDING_SECONDS)


def cancel_pending_play_commands(db: Session, announcement_id: Optional[int]) -> int:
    """
    Withdraws PLAY commands for this announcement that the speaker has not picked up yet,
    so a paused / stopped / removed notice is never replayed from a stale command.
    """
    if not announcement_id:
        return 0
    ann_id = int(announcement_id)
    cancelled = 0

    from app.services import hardware_speaker_service as hss

    def _is_play_for_ann(cmd: dict) -> bool:
        return (
            str(cmd.get("command", "")).upper().startswith("PLAY")
            and int(cmd.get("announcement_id") or 0) == ann_id
        )

    with _LOCK:
        before = len(hss._BROADCAST_COMMANDS)
        hss._BROADCAST_COMMANDS[:] = [c for c in hss._BROADCAST_COMMANDS if not _is_play_for_ann(c)]
        cancelled += before - len(hss._BROADCAST_COMMANDS)
        for mac, cmds in list(hss._PENDING_COMMANDS.items()):
            kept = [c for c in cmds if not _is_play_for_ann(c)]
            cancelled += len(cmds) - len(kept)
            hss._PENDING_COMMANDS[mac] = kept

    try:
        from app.models.speaker_command import SpeakerCommand

        rows = (
            db.query(SpeakerCommand)
            .filter(SpeakerCommand.status == "PENDING", SpeakerCommand.command.like("PLAY%"))
            .all()
        )
        for row in rows:
            try:
                payload = json.loads(getattr(row, "payload_json", "") or "{}")
            except Exception:
                continue
            if int(payload.get("announcement_id") or 0) == ann_id:
                setattr(row, "status", "CANCELLED")
                cancelled += 1
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.debug(f"cancel_pending_play_commands note: {exc}")

    if cancelled:
        logger.info(f"Cancelled {cancelled} pending PLAY command(s) for announcement #{ann_id}")
    return cancelled
