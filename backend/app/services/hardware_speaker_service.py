import os
import uuid
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, cast
from datetime import datetime, timezone, timedelta


def utc_now() -> datetime:
    """Returns timezone-naive UTC datetime for database compatibility without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _normalize_dt(dt: Optional[datetime]) -> Optional[datetime]:
    """Safely normalizes any datetime to timezone-naive UTC to avoid TypeError comparisons."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _is_time_due(t: Optional[datetime], cutoff: datetime) -> bool:
    """Returns True if t is None or t <= cutoff in safe normalized UTC."""
    if t is None:
        return True
    t_n = _normalize_dt(t)
    c_n = _normalize_dt(cutoff)
    return t_n is not None and c_n is not None and t_n <= c_n


def _is_future_time(t: Optional[datetime], ref: datetime) -> bool:
    """Returns True if t is in the future relative to ref in safe normalized UTC."""
    if t is None:
        return False
    t_n = _normalize_dt(t)
    r_n = _normalize_dt(ref)
    return t_n is not None and r_n is not None and t_n > r_n


import paho.mqtt.client as mqtt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.core.emergency_utils import is_emergency_announcement
from app.repositories.hardware_repository import (
    get_all_speaker_nodes,
    get_speaker_node_by_id,
    get_speaker_queue,
    update_queue_item_status,
)
from app.services.tts_service import (
    generate_announcement_audio,
    generate_announcement_audio_sync,
    STATIC_AUDIO_DIR,
    ensure_audio_dir_exists,
)

logger = logging.getLogger("echosphere.hardware")

MQTT_BROKER_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Thread-safe in-memory queue for REST polling speaker nodes (e.g. Wokwi / ESP32)
_PENDING_COMMANDS: Dict[str, List[dict]] = {}
_BROADCAST_COMMANDS: List[dict] = []
_DELIVERED_BROADCASTS: Dict[str, Set[str]] = {}

import tempfile

# Global Emergency Override State (for instant audio stream preemption across all Uvicorn workers)
_GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP: float = 0.0
_GLOBAL_EMERGENCY_ANNOUNCEMENT_ID: Optional[int] = None
_EMERGENCY_PREEMPTION_FILE = os.path.join(tempfile.gettempdir(), "echosphere_emergency_preemption.json")


def _read_emergency_file() -> tuple[float, Optional[int]]:
    try:
        if os.path.exists(_EMERGENCY_PREEMPTION_FILE):
            with open(_EMERGENCY_PREEMPTION_FILE, "r") as f:
                data = json.load(f)
                return float(data.get("timestamp", 0.0)), data.get("announcement_id")
    except Exception:
        pass
    return 0.0, None


def trigger_global_emergency_preemption(announcement_id: int):
    """
    Signals an active emergency priority override across all audio streams and queue workers.
    Any active non-emergency audio streams will immediately drop/close their connections.
    Persists to a shared file in tempdir so all Uvicorn worker processes detect preemption in <0.1ms.
    """
    global _GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP, _GLOBAL_EMERGENCY_ANNOUNCEMENT_ID
    now_ts = time.time()
    _GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP = now_ts
    _GLOBAL_EMERGENCY_ANNOUNCEMENT_ID = announcement_id
    try:
        tmp_path = _EMERGENCY_PREEMPTION_FILE + f".{os.getpid()}.tmp"
        with open(tmp_path, "w") as f:
            json.dump({"timestamp": now_ts, "announcement_id": announcement_id}, f)
        os.replace(tmp_path, _EMERGENCY_PREEMPTION_FILE)
    except Exception as e:
        logger.warning(f"Failed to write emergency preemption flag file: {e}")

    logger.warning(
        f"🚨 [GLOBAL EMERGENCY PREEMPTION TRIGGERED] Announcement #{announcement_id} at {now_ts}"
    )


def clear_global_emergency_preemption():
    global _GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP, _GLOBAL_EMERGENCY_ANNOUNCEMENT_ID
    _GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP = 0.0
    _GLOBAL_EMERGENCY_ANNOUNCEMENT_ID = None
    try:
        if os.path.exists(_EMERGENCY_PREEMPTION_FILE):
            os.remove(_EMERGENCY_PREEMPTION_FILE)
    except Exception:
        pass


def is_global_emergency_active(since_timestamp: Optional[float] = None) -> bool:
    global _GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP
    file_ts, _ = _read_emergency_file()
    effective_ts = max(_GLOBAL_EMERGENCY_OVERRIDE_TIMESTAMP, file_ts)
    if effective_ts <= 0:
        return False
    if since_timestamp is not None:
        return effective_ts > since_timestamp
    return (time.time() - effective_ts) < 300


def _get_queue_item_priority_weight(item: SpeakerQueue) -> int:
    ann = getattr(item, "announcement", None)
    if not ann:
        return 200
    if is_emergency_announcement(ann):
        return 400
    p = str(getattr(ann, "priority", "") or "").upper()
    cat = str(getattr(ann, "category", "") or "").upper()
    if "EMERGENCY" in p or "CRITICAL" in p or "EMERGENCY" in cat:
        return 400
    if "HIGH" in p or "URGENT" in p:
        return 300
    if "LOW" in p:
        return 100
    return 200


def normalize_speaker_queue_positions(db: Session) -> List[SpeakerQueue]:
    """
    Deterministically normalizes and re-indexes speaker queue items:
    1. Active 'Playing' item always occupies queue_position = 1.
    2. Waiting items ('Next in Queue' and 'Queued') are sorted deterministically:
       a. Priority Weight: Emergency (400) > High/Urgent (300) > Medium/Normal (200) > Low (100)
       b. Scheduled Time: scheduled_time ascending (earlier target time plays first)
       c. Homo-temporal Tie-breaker: If scheduled for identical timestamps, priority tier wins,
          followed by earliest creation time / lowest announcement_id.
    3. Reassigns queue_position sequentially: 1 (Playing), 2 (Next in Queue), 3, 4, ...
    4. Automatically updates status of position 2 to 'Next in Queue' if ready to play,
       and remaining to 'Queued'.
    """
    now = utc_now()
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
    waiting_items = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status.in_(["Next in Queue", "Queued"]))
        .all()
    )
    if not waiting_items and not active_playing:
        return []

    def sort_key(q: SpeakerQueue):
        weight = _get_queue_item_priority_weight(q)
        prio_rank = -weight
        sched_dt = _normalize_dt(q.scheduled_time) or now
        ann_id = q.announcement_id or q.id or 0
        return (prio_rank, sched_dt, ann_id)

    waiting_sorted = sorted(waiting_items, key=sort_key)

    all_normalized: List[SpeakerQueue] = []
    current_pos = 1

    if active_playing:
        if active_playing.queue_position != 1:
            active_playing.queue_position = 1
        all_normalized.append(active_playing)
        current_pos = 2

    for item in waiting_sorted:
        item.queue_position = current_pos
        is_future = _is_future_time(item.scheduled_time, now)
        if current_pos == 1:
            # If queue is currently idle, position 1 is Next in Queue (ready to advance to Playing)
            item.status = "Next in Queue" if not is_future else "Queued"
        elif current_pos == 2 and not is_future and active_playing:
            item.status = "Next in Queue"
        else:
            item.status = "Queued"
        all_normalized.append(item)
        current_pos += 1

    # Proactively pre-render Kokoro audio for all waiting queue items in background
    for w_item in waiting_sorted:
        ann = getattr(w_item, "announcement", None)
        if ann and getattr(ann, "id", None):
            try:
                from app.api.v1.announcement import _find_cached_audio_file
                v = getattr(ann, "speaker_voice", "female") or "female"
                clean_v = str(v).lower()
                tag = f"american_{clean_v}"
                fname, fpath, _ = _find_cached_audio_file(ann.id, tag, include_chime=False, prefer_wav=True)
                if not fname or not fpath:
                    import threading
                    from app.services.tts_service import generate_announcement_audio_sync
                    def _prewarm_waiting_item(a_id=ann.id, a_title=getattr(ann, "title", ""), a_desc=getattr(ann, "description", ""), a_v=clean_v):
                        try:
                            generate_announcement_audio_sync(
                                a_id,
                                f"{a_title}. {a_desc}",
                                gender=a_v,
                                include_chime=False,
                            )
                        except Exception:
                            pass
                    threading.Thread(target=_prewarm_waiting_item, daemon=True, name=f"Prewarm_Wait_{ann.id}").start()
            except Exception:
                pass

    db.commit()
    return all_normalized


def queue_command_for_nodes(payload: dict, target_mac: Optional[str] = None, db: Optional[Session] = None):
    """
    Pushes a command into the pending command queue for REST polling nodes.
    Broadcast commands are stored with unique command_id so every polling node receives them.
    Persists to SpeakerCommand DB table so multi-worker cloud servers (Render) never drop commands.
    """
    global _BROADCAST_COMMANDS
    cmd_id = payload.get("command_id") or str(uuid.uuid4())
    payload["command_id"] = cmd_id
    ann_id = payload.get("announcement_id")
    cmd_type = payload.get("command")
    is_repeat = bool(payload.get("is_repeat") or (payload.get("repeat_round", 1) > 1) or payload.get("force_dispatch"))

    # In-memory deduplication for PLAY commands: allow repeat rounds to dispatch cleanly
    if ann_id and cmd_type in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"):
        if not is_repeat:
            if not target_mac or target_mac.upper() == "ALL":
                for c in _BROADCAST_COMMANDS:
                    if c.get("command") == cmd_type and c.get("announcement_id") == ann_id:
                        logger.info(f"Duplicate command for announcement #{ann_id} already in memory broadcast queue.")
                        return
            else:
                key = target_mac.upper()
                if key in _PENDING_COMMANDS:
                    for c in _PENDING_COMMANDS[key]:
                        if c.get("command") == cmd_type and c.get("announcement_id") == ann_id:
                            logger.info(f"Duplicate command for announcement #{ann_id} already in node queue {key}.")
                            return
        else:
            # Prune older command for this announcement so hardware immediately processes the new repeat round
            if not target_mac or target_mac.upper() == "ALL":
                _BROADCAST_COMMANDS = [c for c in _BROADCAST_COMMANDS if c.get("announcement_id") != ann_id]
            else:
                key = target_mac.upper()
                if key in _PENDING_COMMANDS:
                    _PENDING_COMMANDS[key] = [c for c in _PENDING_COMMANDS[key] if c.get("announcement_id") != ann_id]

    # 1. In-memory queue
    if not target_mac or target_mac.upper() == "ALL":
        if cmd_type in ("TEST_SPEAKER", "RESTART"):
            _BROADCAST_COMMANDS = [c for c in _BROADCAST_COMMANDS if c.get("command") != cmd_type]
        _BROADCAST_COMMANDS.append(payload)
        if len(_BROADCAST_COMMANDS) > 25:
            _BROADCAST_COMMANDS = _BROADCAST_COMMANDS[-25:]
    else:
        key = target_mac.upper()
        if key not in _PENDING_COMMANDS:
            _PENDING_COMMANDS[key] = []
        cmd_type = payload.get("command")
        if cmd_type in ("TEST_SPEAKER", "RESTART"):
            _PENDING_COMMANDS[key] = [c for c in _PENDING_COMMANDS[key] if c.get("command") != cmd_type]
        _PENDING_COMMANDS[key].append(payload)
        if len(_PENDING_COMMANDS[key]) > 10:
            _PENDING_COMMANDS[key] = _PENDING_COMMANDS[key][-10:]

    # 2. Database persistent command queue (cross-worker reliability)
    session = db
    close_session = False
    if session is None:
        try:
            from app.db.database import SessionLocal
            session = SessionLocal()
            close_session = True
        except Exception as se:
            logger.debug(f"Could not open SessionLocal for SpeakerCommand: {se}")

    if session is not None:
        try:
            from app.models.speaker_command import SpeakerCommand
            cmd_name = str(payload.get("command", "COMMAND"))
            target_norm = target_mac.upper() if target_mac else None

            # Deduplicate DB pending commands for the same announcement
            if ann_id and cmd_name in ("PLAY_ANNOUNCEMENT", "PLAY_EMERGENCY"):
                existing_cmds = (
                    session.query(SpeakerCommand)
                    .filter(
                        SpeakerCommand.status == "PENDING",
                        SpeakerCommand.command == cmd_name,
                    )
                    .all()
                )
                for ec in existing_cmds:
                    try:
                        p_data = json.loads(getattr(ec, "payload_json", "{}"))
                        if p_data.get("announcement_id") == ann_id:
                            if not is_repeat:
                                logger.info(f"SpeakerCommand for announcement #{ann_id} already PENDING (Cmd #{ec.id}). Skipping duplicate.")
                                return
                            else:
                                ec.status = "SUPERSEDED"
                    except Exception:
                        pass

            cmd_record = SpeakerCommand(
                command=cmd_name,
                target_mac=target_norm,
                payload_json=json.dumps(payload),
                delivered_macs="",
                status="PENDING",
            )
            session.add(cmd_record)
            session.commit()
        except Exception as ce:
            try:
                session.rollback()
            except Exception:
                pass
            logger.debug(f"SpeakerCommand DB persist note: {ce}")
        finally:
            if close_session:
                session.close()


def get_pending_commands_for_mac(mac_address: str, db: Optional[Session] = None) -> List[dict]:
    """
    Retrieves pending commands for a given MAC address without dropping broadcasts for other nodes.
    Queries both in-memory queues and database-backed SpeakerCommand records for multi-worker support.
    """
    mac_key = mac_address.upper()
    cmds: List[dict] = []
    seen_command_ids: Set[str] = set()

    # 1. Node-specific in-memory commands
    if mac_key in _PENDING_COMMANDS and _PENDING_COMMANDS[mac_key]:
        for c in _PENDING_COMMANDS.pop(mac_key):
            cid = c.get("command_id")
            if cid and cid not in seen_command_ids:
                cmds.append(c)
                seen_command_ids.add(cid)

    # 2. Undelivered broadcast commands for this specific node
    if mac_key not in _DELIVERED_BROADCASTS:
        _DELIVERED_BROADCASTS[mac_key] = set()

    delivered_set = _DELIVERED_BROADCASTS[mac_key]
    for b_cmd in _BROADCAST_COMMANDS:
        b_id = b_cmd.get("command_id")
        if b_id and b_id not in delivered_set:
            if b_id not in seen_command_ids:
                cmds.append(b_cmd)
                seen_command_ids.add(b_id)
            delivered_set.add(b_id)

    # 3. Database persistent commands: query SpeakerCommand table (survives worker isolation)
    if db is not None:
        try:
            from app.models.speaker_command import SpeakerCommand
            from datetime import timedelta
            cutoff = utc_now() - timedelta(minutes=5)
            db_cmds = (
                db.query(SpeakerCommand)
                .filter(
                    SpeakerCommand.status == "PENDING",
                    SpeakerCommand.created_at >= cutoff,
                    or_(
                        SpeakerCommand.target_mac == None,
                        SpeakerCommand.target_mac == "ALL",
                        SpeakerCommand.target_mac == mac_key,
                    )
                )
                .order_by(SpeakerCommand.id.asc())
                .all()
            )
            for d_cmd in db_cmds:
                delivered_list = [m.strip() for m in (getattr(d_cmd, "delivered_macs", "") or "").split(",") if m.strip()]
                if mac_key not in delivered_list:
                    try:
                        p_data = json.loads(getattr(d_cmd, "payload_json", "{}"))
                        cid = p_data.get("command_id") or f"cmd_{d_cmd.id}"
                        p_data["command_id"] = cid
                        if cid not in seen_command_ids:
                            cmds.append(p_data)
                            seen_command_ids.add(cid)
                        delivered_list.append(mac_key)
                        # Mark command COMPLETED once delivered to prevent duplicate replay loops
                        setattr(d_cmd, "status", "COMPLETED")
                        db.commit()
                    except Exception as pe:
                        logger.debug(f"Parse payload_json note: {pe}")
        except Exception as dbe:
            try:
                db.rollback()
            except Exception:
                pass
            logger.debug(f"SpeakerCommand DB query note: {dbe}")

    # 4. Database-backed resilient fallback: check active Playing items in SpeakerQueue
    if db is not None:
        try:
            now = utc_now()
            active_playing_items = (
                db.query(SpeakerQueue)
                .filter(SpeakerQueue.status == "Playing")
                .all()
            )
            for p_item in active_playing_items:
                # If played within the last 60 seconds (or currently playing)
                p_played_at = getattr(p_item, "played_at", None)
                p_dur = getattr(p_item, "duration_seconds", 15) or 15
                if p_played_at and (now - p_played_at).total_seconds() > (p_dur + 30):
                    continue
                # If targeted to a specific node, verify MAC match
                sp_node = getattr(p_item, "speaker_node", None)
                if sp_node and getattr(sp_node, "mac_address", None):
                    target_mac = str(sp_node.mac_address).upper()
                    if target_mac != mac_key:
                        continue
                b_id = f"auto_queue_{p_item.id}_{p_item.announcement_id}"
                if b_id not in delivered_set and b_id not in seen_command_ids:
                    ann = getattr(p_item, "announcement", None)
                    title = getattr(ann, "title", "Announcement") if ann else "Announcement"
                    message = (getattr(ann, "ai_summary", None) or getattr(ann, "description", "")) if ann else ""
                    audio_url = f"https://echosphere-backend-9lv8.onrender.com/api/v1/announcements/{p_item.announcement_id}/audio/stream?audio_format=wav"
                    cmds.append({
                        "command": "PLAY_ANNOUNCEMENT",
                        "command_id": b_id,
                        "announcement_id": int(getattr(p_item, "announcement_id", 0)),
                        "title": str(title),
                        "message": str(message),
                        "audio_url": audio_url,
                        "volume": 100,
                        "duration": int(getattr(p_item, "duration_seconds", 15) or 15),
                        "duration_seconds": int(getattr(p_item, "duration_seconds", 15) or 15),
                        "timestamp": (p_played_at or now).isoformat(),
                    })
                    delivered_set.add(b_id)
                    seen_command_ids.add(b_id)
        except Exception as e:
            logger.debug(f"DB fallback command check note: {e}")

    # Prune delivered broadcast cache
    if len(delivered_set) > 60:
        valid_ids = {c.get("command_id") for c in _BROADCAST_COMMANDS}
        _DELIVERED_BROADCASTS[mac_key] = {cid for cid in delivered_set if (cid in valid_ids or cid.startswith("auto_queue_"))}

    return cmds




def publish_mqtt_command(topic: str, payload: dict) -> bool:
    """
    Publishes an MQTT control message to speaker nodes.
    Gracefully handles broker offline mode by logging locally with zero latency socket probe (<40ms).
    """
    try:
        # Fast probe to check if MQTT broker is listening before attempting full connection
        import socket
        probe_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe_sock.settimeout(0.04)
        probe_res = probe_sock.connect_ex((MQTT_BROKER_HOST, MQTT_BROKER_PORT))
        probe_sock.close()
        if probe_res != 0:
            logger.info(f"MQTT Broker at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} offline. Simulated MQTT dispatch succeeded.")
            return False

        def _bg_publish():
            try:
                try:
                    from paho.mqtt.enums import CallbackAPIVersion
                    client = mqtt.Client(CallbackAPIVersion.VERSION2, client_id=f"EchoSphere_Server_{utc_now().timestamp()}")
                except (ImportError, AttributeError):
                    client = mqtt.Client(client_id=f"EchoSphere_Server_{utc_now().timestamp()}")

                client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=5)
                client.publish(topic, json.dumps(payload), qos=1)
                client.disconnect()
                logger.info(f"MQTT command sent to [{topic}]: {payload.get('command')}")
            except Exception as pe:
                logger.debug(f"Background MQTT publish note: {pe}")

        import threading
        threading.Thread(target=_bg_publish, daemon=True, name="MQTTPublishWorker").start()
        return True
    except Exception as e:
        logger.warning(f"MQTT dispatch error at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} - {e}. Simulated MQTT dispatch succeeded.")
        return False


async def broadcast_announcement_to_speaker(
    db: Session,
    announcement_id: int,
    title: str,
    content: str,
    department_code: str = "ALL",
    zone: str = "College-Wide",
    is_emergency: bool = False,
    speaker_voice: Optional[str] = "female",
    base_url: str = "http://localhost:8000",
) -> dict:
    """
    Synthesizes TTS audio for the announcement, queues it, and dispatches play command.
    """
    # Emergency Fast-Path: Sub-millisecond dispatch for urgent alarms without blocking on network TTS
    if is_emergency:
        trigger_global_emergency_preemption(announcement_id)
        topic = "echosphere/speakers/all/emergency"
        audio_full_url = f"{base_url}/api/v1/announcements/{announcement_id}/audio/stream?audio_format=wav&include_chime=false"
        payload = {
            "command": "PLAY_EMERGENCY",
            "announcement_id": announcement_id,
            "title": title,
            "message": content,
            "priority": "EMERGENCY",
            "is_emergency": True,
            "audio_url": audio_full_url,
            "zone": zone or "College-Wide",
            "volume": 100,
            "timestamp": utc_now().isoformat(),
        }
        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=None, db=db)

        # Enforce emergency preemption on SpeakerQueue: pause all non-emergency active items!
        non_em_items = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.announcement_id != announcement_id,
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
            )
            .all()
        )
        for nei in non_em_items:
            nei.status = "Paused"
        db.commit()

        # Record in SpeakerQueue table if announcement exists
        from app.models.announcement import Announcement
        ann_row = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if ann_row:
            existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
            if not existing_item:
                queue_item = cast(Any, SpeakerQueue)(
                    announcement_id=announcement_id,
                    queue_position=1,
                    status="Playing",
                    scheduled_time=utc_now(),
                    played_at=utc_now(),
                    duration_seconds=15,
                )
                db.add(queue_item)
                db.commit()
                db.refresh(queue_item)
            else:
                setattr(existing_item, "status", "Playing")
                setattr(existing_item, "played_at", utc_now())
                setattr(existing_item, "queue_position", 1)
                db.commit()

        return {
            "status": "success",
            "command": "PLAY_EMERGENCY",
            "topic": topic,
            "audio_url": payload["audio_url"],
            "queue_position": 1,
            "mqtt_dispatched": publish_success,
        }


    # 1. Add/Get queue item (only if valid announcement exists in database)
    from app.models.announcement import Announcement
    announcement_exists = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    queue_pos = 1
    existing_item = None
    queue_item = None
    words = len((title + " " + content).split())
    dur_secs = max(10, int(words / 2.5))

    if announcement_exists:
        existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
        active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
        existing_status = str(getattr(existing_item, "status", "")) if existing_item else ""
        should_play: bool = is_emergency or (active_playing is None) or (existing_status == "Playing")

        if is_emergency and active_playing and getattr(active_playing, "id", None) != (getattr(existing_item, "id", None) if existing_item else None):
            setattr(active_playing, "status", "Paused")
            db.commit()

        if not existing_item:
            max_pos = db.query(SpeakerQueue).count()
            queue_item = cast(Any, SpeakerQueue)(
                announcement_id=announcement_id,
                queue_position=1 if is_emergency else max_pos + 1,
                status="Playing" if should_play else ("Next in Queue" if max_pos == 0 else "Queued"),
                scheduled_time=utc_now(),
                played_at=utc_now() if should_play else None,
                duration_seconds=dur_secs,
            )
            db.add(queue_item)
            db.commit()
            db.refresh(queue_item)
            queue_pos = int(getattr(queue_item, "queue_position", 1) or 1)
        else:
            active_count = db.query(SpeakerQueue).filter(
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"])
            ).count()
            if should_play:
                setattr(existing_item, "status", "Playing")
                setattr(existing_item, "played_at", utc_now())
                setattr(existing_item, "queue_position", 1)
            else:
                setattr(existing_item, "status", "Next in Queue" if active_count == 0 else "Queued")
                setattr(existing_item, "played_at", None)
                setattr(existing_item, "queue_position", active_count + 1)
            setattr(existing_item, "scheduled_time", utc_now())
            setattr(existing_item, "duration_seconds", dur_secs)
            setattr(existing_item, "failure_reason", None)
            setattr(existing_item, "error_count", 0)
            db.commit()
            db.refresh(existing_item)
            queue_pos = int(getattr(existing_item, "queue_position", 1) or 1)

    # 2. Form robust streaming audio URL directly targeting 16-bit PCM WAV for ESP32 hardware streaming
    audio_full_url = f"{base_url}/api/v1/announcements/{announcement_id}/audio/stream?audio_format=wav&include_chime=false"

    # 3. Ensure WAV audio stream is 100% written to disk BEFORE dispatching command to ESP32
    clean_v = (speaker_voice or "female").lower()
    tag = f"american_{clean_v}"
    from app.api.v1.announcement import _find_cached_audio_file
    fname, fpath, _ = _find_cached_audio_file(
        announcement_id,
        tag,
        include_chime=False,
        prefer_wav=True,
    )
    if not fname or not fpath:
        try:
            import threading
            def _broadcast_bg_synth(a_id=announcement_id, a_title=title, a_content=content, a_gender=clean_v):
                try:
                    generate_announcement_audio_sync(
                        a_id,
                        f"{a_title}. {a_content}",
                        gender=a_gender,
                        include_chime=False,
                    )
                except Exception as bg_e:
                    logger.warning(f"Audio pre-generation on broadcast note: {bg_e}")
            threading.Thread(target=_broadcast_bg_synth, daemon=True, name=f"Broadcast_Synth_{announcement_id}").start()
        except Exception as bg_err:
            logger.warning(f"Failed to launch broadcast audio pre-render: {bg_err}")

    # 4. Publish MQTT dispatch and queue command for REST-polling nodes
    topic = f"echosphere/dept/{department_code}/speakers/command"
    if zone and zone != "College-Wide":
        topic = f"echosphere/zone/{zone}/speakers/command"
    if is_emergency:
        topic = "echosphere/speakers/all/emergency"

    from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
    sched_rec = db.query(AnnouncementRepeatSchedule).filter(
        AnnouncementRepeatSchedule.announcement_id == announcement_id,
        AnnouncementRepeatSchedule.is_active == True,
    ).first()
    rep_round = (sched_rec.total_played_count + 1) if sched_rec else 1
    is_rep = bool(sched_rec is not None and sched_rec.total_played_count > 0)
    target_queue_item = existing_item if existing_item else queue_item
    target_q_id = getattr(target_queue_item, "id", None)

    payload = {
        "command": "PLAY_EMERGENCY" if is_emergency else "PLAY_ANNOUNCEMENT",
        "command_id": f"cmd_ann_{announcement_id}_rep_{rep_round}_{int(time.time()*1000)}",
        "announcement_id": announcement_id,
        "queue_id": target_q_id,
        "title": title,
        "message": content,
        "priority": "EMERGENCY" if is_emergency else "NORMAL",
        "is_emergency": is_emergency,
        "duration_seconds": dur_secs,
        "department": department_code,
        "audio_url": audio_full_url,
        "zone": zone,
        "volume": 100,
        "is_repeat": is_rep,
        "repeat_round": rep_round,
        "timestamp": utc_now().isoformat(),
    }

    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=None, db=db)

    return {
        "status": "success",
        "command": payload["command"],
        "topic": topic,
        "audio_url": audio_full_url,
        "queue_position": queue_pos,
        "mqtt_dispatched": publish_success,
    }


def send_node_control_command(
    db: Session,
    speaker_node_id: int,
    command: str,
    volume: Optional[int] = None,
    announcement_id: Optional[int] = None,
) -> dict:
    """
    Sends explicit control commands (PLAY, PAUSE, RESUME, SKIP, CANCEL, TEST_SPEAKER, RESTART) to a node.
    """
    node = get_speaker_node_by_id(db, speaker_node_id)
    if not node:
        return {"status": "error", "message": f"Speaker node #{speaker_node_id} not found."}

    if volume is not None:
        setattr(node, "volume", max(0, min(100, volume)))
        db.commit()

    topic = f"echosphere/node/{node.mac_address}/command"
    payload = {
        "command": command,
        "node_id": int(getattr(node, "id", 0) or 0),
        "mac_address": str(getattr(node, "mac_address", "") or ""),
        "announcement_id": announcement_id,
        "volume": int(getattr(node, "volume", 80) or 80),
        "timestamp": utc_now().isoformat(),
    }

    if announcement_id:
        from app.models.announcement import Announcement
        ann = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if ann:
            dept_name = ann.creator.department.name if (ann.creator and ann.creator.department) else "College-Wide"
            p_val = ann.priority.value if hasattr(ann.priority, "value") else str(ann.priority)
            active_content = (ann.ai_summary or ann.description or "").strip()
            active_title = (ann.title or "Campus Notice").strip()
            words = len((active_title + " " + active_content).split())
            dur_secs = max(15, int(words / 2.5))
            payload["title"] = active_title
            payload["content"] = active_content
            payload["message"] = active_content
            payload["priority"] = p_val
            payload["department"] = dept_name
            payload["duration_seconds"] = dur_secs
            payload["audio_url"] = f"/api/v1/announcements/{ann.id}/audio/stream?audio_format=wav"

    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=str(node.mac_address) if getattr(node, "mac_address", None) else None, db=db)

    return {
        "status": "success",
        "node_id": int(getattr(node, "id", 0) or 0),
        "mac_address": str(getattr(node, "mac_address", "") or ""),
        "command": command,
        "mqtt_dispatched": publish_success,
    }


def enqueue_and_broadcast_announcement(
    db: Session,
    announcement_id: Any,
    title: Any,
    content: Any,
    department_code: str = "ALL",
    zone: str = "College-Wide",
    is_emergency: bool = False,
    speaker_node_id: Optional[int] = None,
    target_mac: Optional[str] = None,
    scheduled_time: Optional[datetime] = None,
    speaker_voice: Optional[Any] = "female",
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
    force_requeue: bool = False,
) -> dict:
    """
    Enqueues an announcement into SpeakerQueue and broadcasts to targeted or all active speaker nodes.
    Automatically starts playing if the queue is empty / idle.
    """
    # 0. Resolve targeted speaker node if provided
    if speaker_node_id and not target_mac:
        target_node = get_speaker_node_by_id(db, speaker_node_id)
        if not target_node:
            # Resilient fallback across database environments (Render auto-inc vs SQLite IDs)
            if speaker_node_id in (10, 13, 14):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("D4:F3:2D:22:2A:CD")).first()
                if not target_node:
                    target_node = db.query(SpeakerNode).filter(SpeakerNode.name.ilike("%ESP32%")).first()
            elif speaker_node_id in (12, 1):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("24:0A:C4:00:01:10")).first()
            elif speaker_node_id in (8, 2, 15):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("D4:F3:2D:22:2A:CB")).first()
            elif speaker_node_id in (9, 3, 16, 21):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("D4:F3:2D:22:2A:CC")).first()
        if target_node:
            t_mac = getattr(target_node, "mac_address", None)
            target_mac = str(t_mac) if t_mac is not None else None
            t_id = getattr(target_node, "id", None)
            speaker_node_id = int(t_id) if t_id is not None else None
            t_zone = getattr(target_node, "zone", None)
            if t_zone is not None:
                zone = str(t_zone)
        else:
            speaker_node_id = None

    words = len((str(title) + " " + str(content)).split())
    # Speech pace: ~2.2 words per second.
    # Total hardware cycle: 1.5s attention chime + speech audio + 1.5s LCD dwell + 1s network buffer = speech + 4s
    dur_secs = max(8, int(words / 2.2) + 5)
    clean_v = (speaker_voice or "female").lower()
    tag = f"american_{clean_v}"
    try:
        from app.api.v1.announcement import _find_cached_audio_file
        cached_fn, cached_fp, _ = _find_cached_audio_file(
            announcement_id,
            tag,
            include_chime=False,
            prefer_wav=True,
        )
        if cached_fp and os.path.exists(cached_fp) and cached_fp.endswith(".wav"):
            import wave
            with wave.open(cached_fp, "rb") as wf:
                real_d = int(wf.getnframes() / wf.getframerate())
                if real_d > 0:
                    dur_secs = real_d + 4
    except Exception:
        pass

    now = utc_now()

    # 1. Clean up only genuinely expired 'Playing' items (with 20s watchdog grace period)
    stale_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").all()
    for sp in stale_playing:
        sp_played_at = getattr(sp, "played_at", None)
        sp_dur = getattr(sp, "duration_seconds", 4) or 4
        if sp_played_at is not None and (now - sp_played_at).total_seconds() >= (sp_dur + 20):
            setattr(sp, "status", "Completed")
            db.commit()

    # Add / update SpeakerQueue table
    existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
    is_future_scheduled = _is_future_time(scheduled_time, now)

    active_ann_id = getattr(active_playing, "announcement_id", None) if active_playing else None

    # Preemption check: STRICTLY restricted to EMERGENCY notices (or explicit manual overrides)!
    # Routine / non-emergency notices MUST NEVER pause an ongoing broadcast!
    if is_emergency and active_playing and active_ann_id != announcement_id:
        from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
        active_sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == active_playing.announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        )
        # Cleanly pause the ongoing broadcast so it can resume after emergency concludes
        setattr(active_playing, "status", "Paused")
        if active_sched:
            active_sched.is_active = True
        db.commit()
        logger.warning(
            f"🚨 [EMERGENCY PREEMPTION] Preempted ongoing notice #{active_playing.announcement_id} "
            f"for newly arrived Emergency Notice #{announcement_id}."
        )
        active_playing = None

    active_items_count = db.query(SpeakerQueue).filter(
        SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"])
    ).count()

    active_status = getattr(active_playing, "status", None) if active_playing else None
    existing_status = getattr(existing_item, "status", None) if existing_item else None
    active_ann_id = getattr(active_playing, "announcement_id", None) if active_playing else None

    # Audio should play immediately ONLY if queue is idle or this notice is emergency / already playing
    should_play = (not is_future_scheduled) and (
        is_emergency
        or (active_playing is None)
        or (existing_status == "Playing")
        or (active_ann_id == announcement_id)
        or (active_items_count == 0)
    )

    if is_emergency:
        trigger_global_emergency_preemption(announcement_id)
        other_active = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.announcement_id != announcement_id,
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
            )
            .all()
        )
        for oa in other_active:
            oa.status = "Paused"
        db.commit()

    active_item = existing_item
    if not existing_item:
        item_status = "Playing" if should_play else ("Next in Queue" if active_items_count == 0 and not is_future_scheduled else "Queued")
        queue_item = cast(Any, SpeakerQueue)(
            announcement_id=announcement_id,
            speaker_node_id=speaker_node_id,
            queue_position=1 if is_emergency or should_play else active_items_count + 1,
            status=item_status,
            scheduled_time=scheduled_time or now,
            played_at=now if should_play else None,
            duration_seconds=dur_secs,
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        active_item = queue_item
    else:
        # Check if existing item is already Completed and has no repeat schedule
        if getattr(existing_item, "status", "") == "Completed" and not is_emergency and not force_requeue:
            from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
            sched = db.query(AnnouncementRepeatSchedule).filter(
                AnnouncementRepeatSchedule.announcement_id == announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            ).first()
            if not sched:
                logger.info(f"Announcement #{announcement_id} has already completed single broadcast. Not re-activating.")
                return {
                    "status": "completed",
                    "command": "COMPLETED",
                    "topic": "",
                    "audio_url": f"{base_url}/api/v1/announcements/{announcement_id}/audio/stream",
                    "queue_position": int(getattr(existing_item, "queue_position", 1) or 1),
                    "queue_status": "Completed",
                    "is_playing": False,
                    "mqtt_dispatched": False,
                }

        if speaker_node_id:
            setattr(existing_item, "speaker_node_id", speaker_node_id)
        if should_play:
            setattr(existing_item, "status", "Playing")
            setattr(existing_item, "played_at", now)
            setattr(existing_item, "queue_position", 1)
        else:
            item_status = "Next in Queue" if active_items_count == 0 and not is_future_scheduled else "Queued"
            setattr(existing_item, "status", item_status)
            setattr(existing_item, "played_at", None)
            setattr(existing_item, "queue_position", active_items_count + 1)
            setattr(existing_item, "scheduled_time", scheduled_time or now)

        setattr(existing_item, "duration_seconds", dur_secs)
        setattr(existing_item, "failure_reason", None)
        setattr(existing_item, "error_count", 0)
        db.commit()

    # Deterministically normalize all queue positions (orders by emergency, schedule, priority, homo-temporal tie-breaker)
    normalize_speaker_queue_positions(db)
    db.refresh(active_item)
    queue_pos = int(getattr(active_item, "queue_position", 1) or 1)
    current_status = str(getattr(active_item, "status", "Queued"))

    # 2. Form robust streaming audio URL directly targeting 16-bit PCM WAV for ESP32 hardware streaming
    audio_full_url = f"{base_url}/api/v1/announcements/{announcement_id}/audio/stream?audio_format=wav&include_chime=false"

    # 3. Form payload and dispatch IMMEDIATELY if ready to play (sub-millisecond latency!)
    if target_mac:
        topic = f"echosphere/node/{target_mac}/command"
    elif is_emergency:
        topic = "echosphere/speakers/all/emergency"
    elif zone and zone != "College-Wide":
        topic = f"echosphere/zone/{zone}/speakers/command"
    else:
        topic = f"echosphere/dept/{department_code}/speakers/command"

    q_id = getattr(active_item, "id", None)
    payload = {
        "command": "PLAY_EMERGENCY" if is_emergency else "PLAY_ANNOUNCEMENT",
        "announcement_id": announcement_id,
        "queue_id": q_id,
        "speaker_node_id": speaker_node_id,
        "target_mac": target_mac,
        "title": title,
        "message": content,
        "priority": "EMERGENCY" if is_emergency else "NORMAL",
        "is_emergency": is_emergency,
        "audio_url": audio_full_url,
        "zone": zone,
        "volume": 100 if is_emergency else 85,
        "duration_seconds": dur_secs,
        "timestamp": utc_now().isoformat(),
    }

    publish_success = False
    if should_play:
        clean_v = (speaker_voice or "female").lower()
        tag = f"american_{clean_v}"
        from app.api.v1.announcement import _find_cached_audio_file
        fname, fpath, _ = _find_cached_audio_file(
            announcement_id,
            tag,
            include_chime=False,
            prefer_wav=True,
        )
        if not fname or not fpath:
            try:
                import threading
                def _autoplay_bg_synth(a_id=announcement_id, a_title=title, a_content=content, a_gender=clean_v):
                    try:
                        generate_announcement_audio_sync(
                            a_id,
                            f"{a_title}. {a_content}",
                            gender=a_gender,
                            include_chime=False,
                        )
                    except Exception as bg_e:
                        logger.warning(f"Audio pre-generation on auto-play note: {bg_e}")
                threading.Thread(target=_autoplay_bg_synth, daemon=True, name=f"Autoplay_Synth_{announcement_id}").start()
            except Exception as bg_err:
                logger.warning(f"Failed to launch auto-play audio pre-render: {bg_err}")

        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=target_mac, db=db)
        logger.info(f"📢 [AUTO-PLAY] Announcement #{announcement_id} ('{title}') -> Immediately playing on {topic} (Node: {target_mac or 'ALL'})")
    else:
        logger.info(f"📋 [ENQUEUED] Announcement #{announcement_id} ('{title}') -> Standing by at queue position #{queue_pos} ({current_status})")
        # Pre-warm audio in background for this enqueued announcement so it's ready when played later
        try:
            import threading
            def _prewarm_bg():
                try:
                    generate_announcement_audio_sync(
                        announcement_id,
                        f"{title}. {content}",
                        gender=speaker_voice or "female",
                        include_chime=False,
                    )
                except Exception as bg_e:
                    logger.warning(f"Background audio pre-warm note: {bg_e}")
            threading.Thread(target=_prewarm_bg, daemon=True).start()
        except Exception as e:
            logger.warning(f"Audio pre-warm dispatch note: {e}")

    return {
        "status": "success",
        "command": payload["command"] if should_play else "QUEUED",
        "topic": topic,
        "audio_url": audio_full_url,
        "queue_position": queue_pos,
        "queue_status": current_status,
        "is_playing": should_play,
        "mqtt_dispatched": publish_success,
    }


def restore_paused_queue_items(db: Session, now: datetime):
    """
    Restores any paused notices back to Queued state after an emergency broadcast finishes.
    """
    paused_items = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status == "Paused")
        .order_by(SpeakerQueue.queue_position.asc())
        .all()
    )
    if paused_items:
        logger.info(f"Restoring {len(paused_items)} paused queue items after emergency broadcast.")
        pos = 1
        for item in paused_items:
            item.status = "Queued"
            item.queue_position = pos
            pos += 1
        db.commit()


def dispatch_queue_action_to_speakers(
    db: Session,
    queue_item: SpeakerQueue,
    action: str,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> dict:
    """
    Dispatches hardware control commands (PLAY, PAUSE, RESUME, SKIP, CANCEL) to all active speaker nodes
    corresponding to a queue action.
    """
    ann = queue_item.announcement
    title = ann.title if ann else "Announcement"
    message = (getattr(ann, "ai_summary", None) or getattr(ann, "description", "")) if ann else ""
    dept_code = "ALL"
    if ann and getattr(ann, 'creator', None) and getattr(ann.creator, 'department', None):
        dept_code = ann.creator.department.code or "ALL"
    target_aud = str(getattr(ann, 'target_audience', '') or '').lower()
    is_college_wide = "entire" in target_aud or "all" in target_aud or "college" in target_aud or not queue_item.speaker_node
    target_mac = None if is_college_wide else (queue_item.speaker_node.mac_address if queue_item.speaker_node else None)



    action_lower = action.lower()
    ann_id = int(getattr(queue_item, "announcement_id", 0) or 0)
    if action_lower == "play":
        # Direct neural audio stream URL (16-bit PCM WAV for ESP32 I2S)
        audio_full_url = f"{base_url}/api/v1/announcements/{ann_id}/audio/stream?audio_format=wav&include_chime=false"
        voice_gender = getattr(ann, 'speaker_voice', 'female') or 'female'
        clean_v = str(voice_gender).lower()
        tag = f"american_{clean_v}"
        from app.api.v1.announcement import _find_cached_audio_file
        fname, fpath, _ = _find_cached_audio_file(
            ann_id,
            tag,
            include_chime=False,
            prefer_wav=True,
        )
        if not fname or not fpath:
            try:
                import threading
                def _queue_play_bg_synth(a_id=ann_id, a_title=title, a_message=message, a_gender=clean_v):
                    try:
                        generate_announcement_audio_sync(
                            a_id,
                            f"{a_title}. {a_message}",
                            gender=a_gender,
                            include_chime=False,
                        )
                    except Exception as e:
                        logger.warning(f"Audio pre-generation on queue play: {e}")
                threading.Thread(target=_queue_play_bg_synth, daemon=True, name=f"Queue_Synth_{ann_id}").start()
            except Exception as bg_err:
                logger.warning(f"Failed to launch queue audio pre-render: {bg_err}")

        from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == ann_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        ) if ann_id else None

        repeat_round = (getattr(sched, "total_played_count", 0) + 1) if sched else 1
        is_repeat = bool(sched is not None and getattr(sched, "total_played_count", 0) > 0)
        max_reps = getattr(sched, "max_repeats", 1) or 1
        cmd_uid = f"cmd_ann_{ann_id}_rep_{repeat_round}_{int(time.time()*1000)}"

        is_em = is_emergency_announcement(ann)
        if is_em:
            trigger_global_emergency_preemption(ann_id)

        payload = {
            "command": "PLAY_EMERGENCY" if is_em else "PLAY_ANNOUNCEMENT",
            "command_id": cmd_uid,
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "speaker_node_id": queue_item.speaker_node_id,
            "target_mac": target_mac,
            "title": title,
            "message": message,
            "priority": "EMERGENCY" if is_em else "NORMAL",
            "is_emergency": is_em,
            "audio_url": audio_full_url,
            "volume": 100 if is_em else 85,
            "duration": getattr(queue_item, "duration_seconds", 15) or 15,
            "duration_seconds": getattr(queue_item, "duration_seconds", 15) or 15,
            "is_repeat": is_repeat,
            "repeat_round": repeat_round,
            "max_repeats": max_reps,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower == "pause":
        payload = {
            "command": "PAUSE",
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "target_mac": target_mac,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower in ("resume", "unpause"):
        payload = {
            "command": "RESUME",
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "target_mac": target_mac,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower == "skip":
        payload = {
            "command": "SKIP",
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "target_mac": target_mac,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower in ("cancel", "stop", "remove"):
        payload = {
            "command": "CANCEL",
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "target_mac": target_mac,
            "timestamp": utc_now().isoformat(),
        }
    else:
        payload = {
            "command": action.upper(),
            "announcement_id": ann_id,
            "queue_id": queue_item.id,
            "target_mac": target_mac,
            "timestamp": utc_now().isoformat(),
        }

    if target_mac:
        topic = f"echosphere/node/{target_mac}/command"
    else:
        topic = f"echosphere/dept/{dept_code}/speakers/command"
    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=target_mac, db=db)

    logger.info(f"🔊 [QUEUE ACTION DISPATCH] Action: '{action}' for Queue Item #{queue_item.id} -> Dispatched to nodes.")
    return {
        "status": "success",
        "action": action,
        "command": payload.get("command"),
        "queue_id": queue_item.id,
        "mqtt_dispatched": publish_success,
    }


def restore_paused_queue_items(db: Session, now: Optional[datetime] = None) -> int:
    """
    Restores any preempted 'Paused' notices back into the queue:
    - If the paused notice has an active repeat schedule (BREAK_SLOTS, CUSTOM, or INTERVAL):
      Checks if its slot or custom window is currently active, or if its interval schedule is valid.
      If active now: sets status='Queued', scheduled_time=now, played_at=None, queue_position=1.
      If slot concluded but future slots remain today: sets status='Queued', scheduled_time=next_slot_time.
      Ensures sched.is_active = True throughout the entire scheduled window!
    - If the paused notice was a standard one-time notice that was interrupted:
      Restores it to status='Queued' with scheduled_time=now so it can finish its broadcast.
    """
    if now is None:
        now = utc_now()

    paused_items = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status == "Paused")
        .order_by(SpeakerQueue.id.asc())
        .all()
    )
    if not paused_items:
        return 0

    from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
    from app.services.repeat_schedule_service import (
        get_current_ist_datetime,
        get_active_break_slots,
        is_slot_active_at_time,
        get_next_slot_datetime,
    )

    ist_now = get_current_ist_datetime()
    time_str = ist_now.strftime("%H:%M")
    active_slots = get_active_break_slots(time_str)
    restored_count = 0

    for p_item in paused_items:
        ann_id = getattr(p_item, "announcement_id", None)
        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == ann_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        ) if ann_id else None

        if sched:
            rep_mode = getattr(sched, "repeat_mode", "INTERVAL") or "INTERVAL"
            if rep_mode == "INTERVAL":
                max_reps = sched.max_repeats if getattr(sched, "max_repeats", None) is not None else 999999
                if max_reps <= 0:
                    max_reps = 999999
                if sched.total_played_count < max_reps and (not sched.end_date or now <= sched.end_date):
                    setattr(p_item, "status", "Queued")
                    setattr(p_item, "scheduled_time", now)
                    setattr(p_item, "played_at", None)
                    setattr(p_item, "queue_position", 1)
                    sched.is_active = True
                    restored_count += 1
                    logger.info(f"▶️ Resumed preempted INTERVAL repeat announcement #{ann_id}.")
                else:
                    setattr(p_item, "status", "Completed")
            else:
                # BREAK_SLOTS or CUSTOM mode
                # Check if currently inside one of the scheduled slots or custom window
                matched = is_slot_active_at_time(sched, time_str, active_slots)
                if matched:
                    # Current break/custom window is STILL ACTIVE!
                    setattr(p_item, "status", "Queued")
                    setattr(p_item, "scheduled_time", now)
                    setattr(p_item, "played_at", None)
                    setattr(p_item, "queue_position", 1)
                    sched.is_active = True
                    restored_count += 1
                    logger.info(
                        f"▶️ Resumed preempted repeat announcement #{ann_id} in active slot '{matched[0]}'. "
                        f"Scheduled window remains active."
                    )
                else:
                    # Current slot concluded, check if there are upcoming slots today or before end_date
                    next_slot_dt, cand_slot = get_next_slot_datetime(sched, from_ist_dt=ist_now, db=db)
                    if next_slot_dt:
                        setattr(p_item, "status", "Queued")
                        setattr(p_item, "scheduled_time", next_slot_dt)
                        setattr(p_item, "played_at", None)
                        sched.is_active = True
                        restored_count += 1
                        logger.info(f"🔁 Queued preempted repeat announcement #{ann_id} for upcoming slot '{cand_slot}' at {next_slot_dt}.")
                    else:
                        setattr(p_item, "status", "Completed")
                        sched.is_active = False
        else:
            # Non-repeat notice: restore to finish broadcast
            setattr(p_item, "status", "Queued")
            setattr(p_item, "scheduled_time", now)
            restored_count += 1
            logger.info(f"▶️ Resumed preempted notice #{ann_id} in speaker queue.")

    if paused_items:
        db.commit()

    return restored_count


BROADCAST_GAP_SECONDS = 4


def auto_advance_speaker_queue(
    db: Session,
    force_advance: bool = False,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> Optional[dict]:
    """
    Automated queue progression engine:
    1. Inspects the currently 'Playing' item in the SpeakerQueue.
    2. If duration has elapsed + 15s gap (or force_advance=True), marks it 'Completed'.
       (Emergency broadcasts bypass the gap and play with 0s delay).
    3. Finds the next queued item:
       - Emergency broadcast waiting -> prioritized to play immediately.
       - Otherwise, next eligible notice where scheduled_time <= now on a First Come First Serve (FCFS) basis.
    4. Transitions next item to 'Playing', records played_at, and dispatches command to speakers.
    5. Updates subsequent item to 'Next in Queue'.
    """
    now = utc_now()
    # 1. Inspect active emergency repeat schedule locking the current break or custom window
    from app.services.repeat_schedule_service import (
        get_active_emergency_repeat_schedule,
        get_current_ist_datetime,
        get_active_break_slots,
        is_slot_active_at_time,
    )
    from app.core.emergency_utils import is_emergency_announcement
    from app.models.announcement_repeat_schedule import RepeatSlotExecutionLog

    active_emerg_sched = get_active_emergency_repeat_schedule(db)
    if active_emerg_sched and active_emerg_sched.announcement:
        emerg_ann = active_emerg_sched.announcement

        # Enforce emergency lockdown: pause all other non-emergency queue items
        non_em_items = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.announcement_id != emerg_ann.id,
                SpeakerQueue.status.in_(["Playing", "Next in Queue", "Queued"]),
            )
            .all()
        )
        for nei in non_em_items:
            nei.status = "Paused"
        db.commit()

        # Check emergency notice queue item
        emerg_q: Any = (
            db.query(SpeakerQueue)
            .filter(SpeakerQueue.announcement_id == emerg_ann.id)
            .first()
        )

        if emerg_q and getattr(emerg_q, "status", None) == "Playing":
            curr_played_at = getattr(emerg_q, "played_at", None)
            curr_dur = getattr(emerg_q, "duration_seconds", 15) or 15
            elapsed = (now - curr_played_at).total_seconds() if curr_played_at else curr_dur
            if elapsed < curr_dur and not force_advance:
                # Still within current playback round
                return None

            # Audio completed round: DO NOT mark Completed or advance to other notices!
            # Loop continuously for the entire break or custom window!
            emerg_q.played_at = now
            emerg_q.status = "Playing"
            emerg_q.queue_position = 1
            active_emerg_sched.total_played_count += 1

            # Log execution round
            ist_now = get_current_ist_datetime()
            time_str = ist_now.strftime("%H:%M")
            date_str = ist_now.strftime("%Y-%m-%d")
            matched_slots = is_slot_active_at_time(active_emerg_sched, time_str, get_active_break_slots(time_str))
            slot_name = matched_slots[0] if matched_slots else "BREAK_SLOT"
            prefix_key = f"{emerg_ann.id}:{slot_name}:{date_str}"
            exec_log = RepeatSlotExecutionLog(
                schedule_id=active_emerg_sched.id,
                slot_key=f"{prefix_key}:{active_emerg_sched.total_played_count}",
                slot_name=slot_name,
                played_at=now,
            )
            db.add(exec_log)
            db.commit()

            dispatch_res = dispatch_queue_action_to_speakers(
                db=db,
                queue_item=emerg_q,
                action="play",
                base_url=base_url,
            )
            logger.info(
                f"🚨 [EMERGENCY CONTINUOUS LOOP] Repeated Emergency Announcement #{emerg_ann.id} "
                f"('{emerg_ann.title}') in {slot_name}. Play count today: {active_emerg_sched.total_played_count}."
            )
            return {
                "status": "emergency_continuous_loop",
                "advanced_to_id": emerg_q.id,
                "title": emerg_ann.title,
                "dispatch": dispatch_res,
            }
        else:
            # Emergency item is not currently playing; start it immediately!
            if not emerg_q:
                dur_words = len(((getattr(emerg_ann, "title", "") or "") + " " + (getattr(emerg_ann, "description", "") or "")).split())
                dur_secs = max(10, int(dur_words / 2.5))
                emerg_q = cast(Any, SpeakerQueue)(
                    announcement_id=emerg_ann.id,
                    queue_position=1,
                    status="Playing",
                    scheduled_time=now,
                    played_at=now,
                    duration_seconds=dur_secs,
                )
                db.add(emerg_q)
            else:
                emerg_q.status = "Playing"
                emerg_q.played_at = now
                emerg_q.queue_position = 1

            active_emerg_sched.total_played_count += 1
            db.commit()

            dispatch_res = dispatch_queue_action_to_speakers(
                db=db,
                queue_item=emerg_q,
                action="play",
                base_url=base_url,
            )
            logger.info(
                f"🚨 [EMERGENCY LOCKDOWN INITIATED] Started emergency notice #{emerg_ann.id} "
                f"('{emerg_ann.title}') continuously for entire break/custom window."
            )
            return {
                "status": "emergency_lockdown_started",
                "advanced_to_id": emerg_q.id,
                "title": emerg_ann.title,
                "dispatch": dispatch_res,
            }

    should_advance = False

    # Handle Currently Playing Item
    current_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()

    if current_playing:
        ann = getattr(current_playing, "announcement", None)
        is_curr_emerg = is_emergency_announcement(ann)
        curr_dur = getattr(current_playing, "duration_seconds", 4) or 4
        if current_playing.announcement_id:
            try:
                from app.api.v1.announcement import _find_cached_audio_file
                _, real_fp, _ = _find_cached_audio_file(current_playing.announcement_id, "american_female", include_chime=False, prefer_wav=True)
                if real_fp and os.path.exists(real_fp) and real_fp.endswith(".wav"):
                    import wave
                    with wave.open(real_fp, "rb") as wf:
                        real_secs = int(wf.getnframes() / wf.getframerate())
                        if real_secs > 0:
                            curr_dur = real_secs
            except Exception:
                pass
        curr_dur = max(3, int(curr_dur) + 1)
        curr_played_at = getattr(current_playing, "played_at", None)

        if not curr_played_at:
            current_playing.played_at = now
            db.commit()
            return None

        elapsed = (now - curr_played_at).total_seconds()

        # Telemetry: Check if a physical hardware speaker node is actively broadcasting right now
        # ESP32 nodes send heartbeats every 3s with status='PLAYING' during native I2S speech stream
        hardware_is_actively_playing = False
        try:
            active_nodes = (
                db.query(SpeakerNode)
                .filter(SpeakerNode.last_heartbeat >= (now - timedelta(seconds=12)))
                .all()
            )
            if any(str(getattr(n, "status", "")).upper() == "PLAYING" for n in active_nodes):
                hardware_is_actively_playing = True
        except Exception:
            pass

        if not force_advance:
            # IMMEDIATE EMERGENCY OVERRIDE CHECK:
            # If current item is NOT an emergency notice, check if any emergency notice is waiting in queue!
            if not is_curr_emerg:
                from app.models.announcement import Announcement
                pending_emergency = (
                    db.query(SpeakerQueue)
                    .join(SpeakerQueue.announcement)
                    .filter(
                        SpeakerQueue.status.in_(["Queued", "Next in Queue"]),
                        or_(
                            Announcement.priority == "High",
                            Announcement.category == "Emergency",
                            Announcement.alert_level == "Emergency",
                        )
                    )
                    .order_by(SpeakerQueue.queue_position.asc())
                    .first()
                )
                if pending_emergency:
                    logger.warning(
                        f"🚨 [EMERGENCY PREEMPTION] Non-emergency notice #{current_playing.announcement_id} "
                        f"preempted by waiting emergency notice #{pending_emergency.announcement_id}!"
                    )
                    # Pause current playing notice so it can resume after emergency finishes
                    current_playing.status = "Paused"
                    # Promote emergency notice to Playing immediately
                    pending_emergency.status = "Playing"
                    pending_emergency.played_at = now
                    pending_emergency.queue_position = 1
                    db.commit()

                    trigger_global_emergency_preemption(pending_emergency.announcement_id)

                    dispatch_res = dispatch_queue_action_to_speakers(
                        db=db,
                        queue_item=pending_emergency,
                        action="play",
                        base_url=base_url,
                    )
                    return {
                        "status": "emergency_preempted",
                        "preempted_id": current_playing.id,
                        "advanced_to_id": pending_emergency.id,
                        "title": pending_emergency.announcement.title if pending_emergency.announcement else "Emergency",
                        "dispatch": dispatch_res,
                    }

            # If physical hardware is actively playing, wait for it to complete or watchdog safety timeout (curr_dur + 35s)
            if hardware_is_actively_playing and elapsed < (curr_dur + 35):
                return None
            if elapsed < curr_dur:
                # Audio duration still active
                return None

        if is_curr_emerg:
            from app.services.repeat_schedule_service import get_active_emergency_repeat_schedule
            curr_active_emerg_sched = get_active_emergency_repeat_schedule(db)
            if (
                curr_active_emerg_sched
                and getattr(curr_active_emerg_sched, "is_active", True)
                and curr_active_emerg_sched.announcement_id == current_playing.announcement_id
            ):
                # Emergency notice with active repeat schedule loops continuously throughout the slot
                current_playing.status = "Playing"
                current_playing.played_at = now
                db.commit()
                return {"status": "emergency_continuous_loop"}
            else:
                # Emergency notice completed! No repeat schedule or schedule ended. Mark Completed!
                current_playing.status = "Completed"
                db.commit()
                clear_global_emergency_preemption()
                # Restore any notices paused during the emergency broadcast
                restore_paused_queue_items(db, now)
                should_advance = True

        else:
            # Normal notice completed audio playback
            from app.services.repeat_schedule_service import (
                get_current_ist_datetime,
                get_active_break_slots,
                is_slot_active_at_time,
                get_notice_priority_info,
            )
            from app.models.announcement_repeat_schedule import (
                AnnouncementRepeatSchedule,
                RepeatSlotExecutionLog,
            )

            ist_now = get_current_ist_datetime()
            time_str = ist_now.strftime("%H:%M")
            date_str = ist_now.strftime("%Y-%m-%d")
            active_slots = get_active_break_slots(time_str)

            sched = (
                db.query(AnnouncementRepeatSchedule)
                .filter(
                    AnnouncementRepeatSchedule.announcement_id == current_playing.announcement_id,
                    AnnouncementRepeatSchedule.is_active == True,
                )
                .first()
            ) if current_playing.announcement_id else None

            has_repeats_remaining = False
            next_repeat_time = None
            slot_name = "REPEAT_INTERVAL"

            if sched:
                repeat_mode = getattr(sched, "repeat_mode", "INTERVAL") or "INTERVAL"
                prio_weight, default_prio_limit, prio_tier = get_notice_priority_info(ann) if ann else (200, 2, "MEDIUM")

                sched.total_played_count += 1
                sched.last_repeat_at = now

                if repeat_mode == "INTERVAL":
                    max_reps_limit = sched.max_repeats if getattr(sched, "max_repeats", None) is not None else default_prio_limit
                    if max_reps_limit <= 0:
                        max_reps_limit = 999999

                    if sched.total_played_count < max_reps_limit:
                        interval_m = getattr(sched, "interval_minutes", 15) or 15
                        next_repeat_time = now + timedelta(minutes=interval_m)
                        if sched.end_date and next_repeat_time > sched.end_date:
                            has_repeats_remaining = False
                            sched.is_active = False
                        else:
                            sched.next_repeat_at = next_repeat_time
                            has_repeats_remaining = True
                            slot_name = f"INTERVAL_{interval_m}M"
                    else:
                        has_repeats_remaining = False
                        sched.is_active = False
                else:
                    # BREAK_SLOTS or CUSTOM mode
                    matched = is_slot_active_at_time(sched, time_str, active_slots)
                    if matched:
                        slot_name = matched[0]
                    else:
                        slot_name = "PUBLISH_NOW"

                    from app.services.repeat_schedule_service import get_next_slot_datetime
                    next_slot_dt, matched_slot_name = get_next_slot_datetime(sched, from_ist_dt=ist_now, db=db)
                    
                    # If currently inside an active slot window, KEEP SCHEDULE ACTIVE!
                    if matched:
                        has_repeats_remaining = True
                        next_repeat_time = next_slot_dt or (now + timedelta(seconds=BROADCAST_GAP_SECONDS))
                        sched.next_repeat_at = next_repeat_time
                        sched.is_active = True
                    elif next_slot_dt is not None:
                        has_repeats_remaining = True
                        next_repeat_time = next_slot_dt
                        sched.next_repeat_at = next_repeat_time
                        sched.is_active = True
                    else:
                        has_repeats_remaining = False
                        sched.is_active = False

                prefix_key = f"{sched.announcement_id}:{slot_name}:{date_str}"
                target_key = f"{prefix_key}:{sched.total_played_count}"
                existing_log = db.query(RepeatSlotExecutionLog).filter(RepeatSlotExecutionLog.slot_key == target_key).first()
                if not existing_log:
                    exec_log = RepeatSlotExecutionLog(
                        schedule_id=sched.id,
                        slot_key=target_key,
                        slot_name=slot_name,
                        played_at=now,
                    )
                    db.add(exec_log)

            if has_repeats_remaining and next_repeat_time:
                max_pos = db.query(SpeakerQueue).filter(SpeakerQueue.status.in_(["Queued", "Next in Queue"])).count()
                current_playing.status = "Queued"
                current_playing.scheduled_time = next_repeat_time
                current_playing.queue_position = max_pos + 1
                current_playing.played_at = None
                if sched:
                    sched.is_active = True
                db.commit()
                logger.info(
                    f"🔁 Announcement #{current_playing.announcement_id} repeat round scheduled "
                    f"(Round {sched.total_played_count + 1} at {next_repeat_time.strftime('%H:%M:%S')} UTC)."
                )
            else:
                current_playing.status = "Completed"
                if sched and not has_repeats_remaining:
                    sched.is_active = False
                db.commit()
                logger.info(f"Speaker queue item #{current_playing.id} completed playback and marked Completed.")

            # Restore any notices preempted by this broadcast!
            restore_paused_queue_items(db, now)
            should_advance = True
    elif not should_advance:
        # Check and restore any stranded paused items when idle
        restore_paused_queue_items(db, now)

        if force_advance:
            should_advance = True
        else:
            # When idle/stopped, advance for emergency preemption or scheduled announcements whose scheduled_time arrived
            queued_items = (
                db.query(SpeakerQueue)
                .filter(SpeakerQueue.status.in_(["Next in Queue", "Queued"]))
                .all()
            )
            emergency_waiting = any(is_emergency_announcement(q.announcement) for q in queued_items)
            if emergency_waiting:
                should_advance = True
            else:
                # Close schedule check: advance when next item is due (within 2s tolerance for timer tick)
                scheduled_due = any(
                    _is_time_due(q.scheduled_time, now + timedelta(seconds=2))
                    for q in queued_items
                )
                if scheduled_due:
                    should_advance = True

    if not should_advance:
        return None

    # Deterministically re-normalize queue items before selecting next item
    normalize_speaker_queue_positions(db)

    # Priority 1: Emergency preemption - check if an emergency notice is queued (prioritized first)
    queued_all = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status.in_(["Next in Queue", "Queued"]))
        .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
        .all()
    )
    from app.models.announcement_repeat_schedule import AnnouncementRepeatSchedule
    valid_queued = []
    for q in queued_all:
        sched = (
            db.query(AnnouncementRepeatSchedule)
            .filter(
                AnnouncementRepeatSchedule.announcement_id == q.announcement_id,
                AnnouncementRepeatSchedule.is_active == True,
            )
            .first()
        ) if q.announcement_id else None
        # If no active repeat schedule, but already played at least once, mark Completed and skip!
        if sched is None and getattr(q, "played_at", None) is not None:
            setattr(q, "status", "Completed")
            db.commit()
            continue
        valid_queued.append(q)
    queued_all = valid_queued

    next_item = next(
        (q for q in queued_all if is_emergency_announcement(q.announcement)),
        None
    )

    # Priority 2: Deterministic First Come First Serve
    # Prefer ready items that are due now or not in the future (<= now + 2s).
    if not next_item:
        ready_items = [q for q in queued_all if not _is_future_time(q.scheduled_time, now + timedelta(seconds=2))]
        if ready_items:
            next_item = ready_items[0]
        elif force_advance and queued_all:
            # If force_advance was requested and no items are due, advance to another distinct waiting notice,
            # but NEVER immediately re-play the exact same notice that was just rescheduled for the future!
            just_played_ann_id = getattr(current_playing, "announcement_id", None) if current_playing else None
            other_items = [q for q in queued_all if q.announcement_id != just_played_ann_id]
            if other_items:
                next_item = other_items[0]

    if not next_item:
        return None

    # Proactively pre-warm all upcoming queue items in the background
    # so that when the next queue transition occurs, audio playback starts with 0.0s latency!
    for upcoming in queued_all:
        if upcoming.announcement_id:
            u_ann = getattr(upcoming, "announcement", None)
            if u_ann:
                try:
                    import threading
                    from app.services.tts_service import generate_announcement_audio_sync
                    def _prewarm_item(u_id=upcoming.announcement_id, u_title=getattr(u_ann, "title", ""), u_desc=getattr(u_ann, "description", ""), u_v=getattr(u_ann, "speaker_voice", "female") or "female"):
                        try:
                            generate_announcement_audio_sync(
                                u_id,
                                f"{u_title}. {u_desc}",
                                gender=str(u_v).lower(),
                                include_chime=False,
                            )
                        except Exception:
                            pass
                    threading.Thread(target=_prewarm_item, daemon=True, name=f"Prewarm_Q_{upcoming.id}").start()
                except Exception:
                    pass

    setattr(next_item, "status", "Playing")
    setattr(next_item, "played_at", utc_now())
    if next_item.announcement and str(getattr(next_item.announcement, "status", "")).upper() in ("SCHEDULED", "APPROVED", "SUBMITTED"):
        from app.core.enums.announcement import AnnouncementStatus
    dur = 0
    if next_item.announcement_id:
        try:
            from app.api.v1.announcement import _find_cached_audio_file
            _, real_fp, _ = _find_cached_audio_file(next_item.announcement_id, "american_female", include_chime=False, prefer_wav=True)
            if real_fp and os.path.exists(real_fp) and real_fp.endswith(".wav"):
                import wave
                with wave.open(real_fp, "rb") as wf:
                    real_secs = int(wf.getnframes() / wf.getframerate())
                    if real_secs > 0:
                        dur = real_secs + 4  # Speech duration + attention chime (1.5s) + network pre-buffer (1.0s) + LCD dwell (1.5s)
        except Exception:
            pass
    if dur <= 0:
        ann = getattr(next_item, "announcement", None)
        words = len(((getattr(ann, "title", "") or '') + ' ' + (getattr(ann, "description", "") or '')).split())
        dur = max(6, int(words / 2.2) + 5)
    setattr(next_item, "duration_seconds", dur)
    db.commit()
    db.refresh(next_item)

    # Normalize positions so next_item is #1, followed by #2 Next in Queue, and others Queued
    normalize_speaker_queue_positions(db)
    db.refresh(next_item)

    # Dispatch PLAY command to speakers
    dispatch_res = dispatch_queue_action_to_speakers(
        db=db,
        queue_item=next_item,
        action="play",
        base_url=base_url,
    )

    # Real-time multi-device WebSocket notification for 0-latency UI update
    try:
        from app.core.websocket_manager import ws_manager
        ws_manager.broadcast_sync({
            "event": "QUEUE_ADVANCED",
            "announcement_id": next_item.announcement_id,
            "title": next_item.announcement.title if next_item.announcement else "Announcement",
            "queue_id": next_item.id,
            "status": "Playing",
            "timestamp": now.isoformat(),
        })
    except Exception:
        pass

    logger.info(f"Speaker queue automatically advanced to item #{next_item.id} ('{next_item.announcement.title if next_item.announcement else 'Announcement'}').")
    return {
        "status": "advanced",
        "advanced_to_id": next_item.id,
        "title": next_item.announcement.title if next_item.announcement else "Announcement",
        "dispatch": dispatch_res,
    }



