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

# Seconds the speaker spends on its local attention chime / siren before speech starts
CHIME_OFFSET_SECONDS = 0.4
EMERGENCY_CHIME_OFFSET_SECONDS = 0.8

# A stream counts as active if it sent a chunk within this many seconds
_STREAM_IDLE_SECONDS = 5.0

# queue_id -> monotonic time of the last chunk sent to the speaker
_ACTIVE_STREAMS: Dict[int, float] = {}
_LOCK = threading.Lock()


def mark_stream_active(queue_id: Optional[int]) -> None:
    if not queue_id:
        return
    with _LOCK:
        _ACTIVE_STREAMS[int(queue_id)] = time.monotonic()


def mark_stream_finished(queue_id: Optional[int]) -> None:
    if not queue_id:
        return
    with _LOCK:
        _ACTIVE_STREAMS.pop(int(queue_id), None)


def is_stream_active(queue_id: Optional[int]) -> bool:
    if not queue_id:
        return False
    with _LOCK:
        last = _ACTIVE_STREAMS.get(int(queue_id))
    return last is not None and (time.monotonic() - last) < _STREAM_IDLE_SECONDS


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
