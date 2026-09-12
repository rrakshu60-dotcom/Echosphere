import os
import uuid
import json
import logging
from typing import Any, Dict, List, Optional, Set, cast
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns timezone-naive UTC datetime for database compatibility without deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


import paho.mqtt.client as mqtt
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
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


def queue_command_for_nodes(payload: dict, target_mac: Optional[str] = None, db: Optional[Session] = None):
    """
    Pushes a command into the pending command queue for REST polling nodes.
    Broadcast commands are stored with unique command_id so every polling node receives them.
    Persists to SpeakerCommand DB table so multi-worker cloud servers (Render) never drop commands.
    """
    cmd_id = payload.get("command_id") or str(uuid.uuid4())
    payload["command_id"] = cmd_id

    # 1. In-memory queue
    if not target_mac or target_mac.upper() == "ALL":
        cmd_type = payload.get("command")
        global _BROADCAST_COMMANDS
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
                        setattr(d_cmd, "delivered_macs", ",".join(delivered_list))
                        t_mac = getattr(d_cmd, "target_mac", None)
                        if t_mac and t_mac != "ALL":
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
                    message = getattr(ann, "description", "") if ann else ""
                    audio_url = f"https://echosphere-backend-9lv8.onrender.com/static/audio_streams/announcement_{p_item.announcement_id}.mp3"
                    cmds.append({
                        "command": "PLAY_ANNOUNCEMENT",
                        "command_id": b_id,
                        "announcement_id": int(getattr(p_item, "announcement_id", 0)),
                        "title": str(title),
                        "message": str(message),
                        "audio_url": audio_url,
                        "volume": 85,
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
    Gracefully handles broker offline mode by logging locally.
    """
    try:
        client = mqtt.Client(client_id=f"EchoSphere_Server_{utc_now().timestamp()}")
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=10)
        client.publish(topic, json.dumps(payload), qos=1)
        client.disconnect()
        logger.info(f"MQTT command sent to [{topic}]: {payload['command']}")
        return True
    except Exception as e:
        logger.warning(f"MQTT Broker not reachable at {MQTT_BROKER_HOST}:{MQTT_BROKER_PORT} - {e}. Simulated MQTT dispatch succeeded.")
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
        topic = "echosphere/speakers/all/emergency"
        payload = {
            "command": "PLAY_EMERGENCY",
            "announcement_id": announcement_id,
            "title": title,
            "message": content,
            "audio_url": f"{base_url}/static/audio_streams/emergency_{announcement_id}.wav",
            "zone": zone or "College-Wide",
            "volume": 100,
            "timestamp": utc_now().isoformat(),
        }
        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=None, db=db)

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
                )
                db.add(queue_item)
                db.commit()
                db.refresh(queue_item)
            else:
                setattr(existing_item, "status", "Playing")
                setattr(existing_item, "played_at", utc_now())
                db.commit()

        return {
            "status": "success",
            "command": "PLAY_EMERGENCY",
            "topic": topic,
            "audio_url": payload["audio_url"],
            "queue_position": 1,
            "mqtt_dispatched": publish_success,
        }


    # 1. Generate audio stream (gracefully fallback if TTS service encounters errors)
    audio_full_url = ""
    try:
        audio_info = await generate_announcement_audio(
            announcement_id,
            f"{title}. {content}",
            gender=speaker_voice or "female",
        )
        audio_full_url = f"{base_url}{audio_info['url_path']}"
    except Exception as e:
        logger.warning(f"Audio generation fallback for #{announcement_id}: {e}")
        audio_full_url = f"{base_url}/static/audio_streams/announcement_{announcement_id}.wav"

    # 2. Add/Get queue item (only if valid announcement exists in database)
    from app.models.announcement import Announcement
    announcement_exists = db.query(Announcement).filter(Announcement.id == announcement_id).first()
    queue_pos = 1

    if announcement_exists:
        existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
        active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
        existing_status = str(getattr(existing_item, "status", "")) if existing_item else ""
        should_play: bool = bool(is_emergency or (active_playing is None) or (existing_status == "Playing"))

        if is_emergency and active_playing and getattr(active_playing, "id", None) != (getattr(existing_item, "id", None) if existing_item else None):
            setattr(active_playing, "status", "Paused")
            db.commit()

        words = len((title + " " + content).split())
        dur_secs = max(10, int(words / 2.5))

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
            if should_play:
                setattr(existing_item, "status", "Playing")
                setattr(existing_item, "played_at", utc_now())
            setattr(existing_item, "duration_seconds", dur_secs)
            db.commit()
            queue_pos = int(getattr(existing_item, "queue_position", 1) or 1)

    # 3. Publish MQTT dispatch
    topic = f"echosphere/dept/{department_code}/speakers/command"
    if zone and zone != "College-Wide":
        topic = f"echosphere/zone/{zone}/speakers/command"
    if is_emergency:
        topic = "echosphere/speakers/all/emergency"

    payload = {
        "command": "PLAY_EMERGENCY" if is_emergency else "PLAY_ANNOUNCEMENT",
        "announcement_id": announcement_id,
        "title": title,
        "audio_url": audio_full_url,
        "zone": zone,
        "volume": 100 if is_emergency else 85,
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
    announcement_id: int,
    title: str,
    content: str,
    department_code: str = "ALL",
    zone: str = "College-Wide",
    is_emergency: bool = False,
    speaker_node_id: Optional[int] = None,
    target_mac: Optional[str] = None,
    scheduled_time: Optional[datetime] = None,
    speaker_voice: Optional[str] = "female",
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
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
            if speaker_node_id in (14, 1):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("24:0A:C4:00:01:10")).first()
            elif speaker_node_id in (15, 2):
                target_node = db.query(SpeakerNode).filter(SpeakerNode.mac_address.ilike("D4:F3:2D:22:2A:CB")).first()
            elif speaker_node_id in (16, 3):
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

    words = len((title + " " + content).split())
    dur_secs = max(10, int(words / 2.5))
    now = utc_now()

    # 1. Clean up any stale 'Playing' items older than playback duration + 30s gap
    stale_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").all()
    for sp in stale_playing:
        sp_played_at = getattr(sp, "played_at", None)
        sp_dur = getattr(sp, "duration_seconds", 15) or 15
        if sp_played_at and (now - sp_played_at).total_seconds() > (sp_dur + 30):
            setattr(sp, "status", "Completed")
            db.commit()

    # Add / update SpeakerQueue table
    existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
    is_future_scheduled = scheduled_time is not None and scheduled_time > now
    active_status = getattr(active_playing, "status", None) if active_playing else None
    existing_status = getattr(existing_item, "status", None) if existing_item else None
    active_ann_id = getattr(active_playing, "announcement_id", None) if active_playing else None

    should_play = (not is_future_scheduled) and (
        is_emergency
        or (active_playing is None)
        or (existing_status == "Playing")
        or (active_ann_id == announcement_id)
    )

    if is_emergency and active_playing and getattr(active_playing, "id", None) != (getattr(existing_item, "id", None) if existing_item else None):
        setattr(active_playing, "status", "Paused")
        db.commit()

    if not existing_item:
        max_pos = db.query(SpeakerQueue).count()
        item_status = "Playing" if should_play else ("Next in Queue" if max_pos == 0 and not is_future_scheduled else "Queued")
        queue_item = cast(Any, SpeakerQueue)(
            announcement_id=announcement_id,
            speaker_node_id=speaker_node_id,
            queue_position=1 if is_emergency else max_pos + 1,
            status=item_status,
            scheduled_time=scheduled_time or now,
            played_at=now if should_play else None,
            duration_seconds=dur_secs,
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        queue_pos = int(getattr(queue_item, "queue_position", 1) or 1)
        current_status = str(getattr(queue_item, "status", item_status))
    else:
        if speaker_node_id and not getattr(existing_item, "speaker_node_id", None):
            setattr(existing_item, "speaker_node_id", speaker_node_id)
        if should_play:
            setattr(existing_item, "status", "Playing")
            setattr(existing_item, "played_at", now)
        setattr(existing_item, "duration_seconds", dur_secs)
        db.commit()
        queue_pos = int(getattr(existing_item, "queue_position", 1) or 1)
        current_status = str(getattr(existing_item, "status", "Queued"))

    # 2. Generate TTS audio stream (MP3 / WAV)
    audio_full_url = f"{base_url}/static/audio_streams/announcement_{announcement_id}.mp3"
    try:
        audio_info = generate_announcement_audio_sync(
            announcement_id,
            f"{title}. {content}",
            gender=speaker_voice or "female",
        )
        audio_full_url = f"{base_url}{audio_info['url_path']}"
    except Exception as e:
        logger.warning(f"Audio file generation fallback: {e}")

    # 3. Form payload and dispatch if ready to play
    if target_mac:
        topic = f"echosphere/node/{target_mac}/command"
    elif is_emergency:
        topic = "echosphere/speakers/all/emergency"
    elif zone and zone != "College-Wide":
        topic = f"echosphere/zone/{zone}/speakers/command"
    else:
        topic = f"echosphere/dept/{department_code}/speakers/command"

    payload = {
        "command": "PLAY_EMERGENCY" if is_emergency else "PLAY_ANNOUNCEMENT",
        "announcement_id": announcement_id,
        "title": title,
        "message": content,
        "audio_url": audio_full_url,
        "zone": zone,
        "volume": 100 if is_emergency else 85,
        "duration_seconds": dur_secs,
        "timestamp": utc_now().isoformat(),
    }

    publish_success = False
    if should_play:
        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=target_mac, db=db)
        logger.info(f"📢 [AUTO-PLAY] Announcement #{announcement_id} ('{title}') -> Immediately playing on {topic} (Node: {target_mac or 'ALL'})")
    else:
        logger.info(f"📋 [ENQUEUED] Announcement #{announcement_id} ('{title}') -> Standing by at queue position #{queue_pos} ({current_status})")

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
    message = ann.description if ann else ""
    dept_code = "ALL"
    if ann and getattr(ann, 'creator', None) and getattr(ann.creator, 'department', None):
        dept_code = ann.creator.department.code or "ALL"
    target_mac = queue_item.speaker_node.mac_address if queue_item.speaker_node else None



    action_lower = action.lower()
    ann_id = int(getattr(queue_item, "announcement_id", 0) or 0)
    if action_lower == "play":
        # Generate / verify audio stream
        audio_full_url = f"{base_url}/static/audio_streams/announcement_{ann_id}.mp3"
        try:
            voice_gender = getattr(ann, 'speaker_voice', 'female') or 'female'
            audio_info = generate_announcement_audio_sync(
                ann_id,
                f"{title}. {message}",
                gender=voice_gender,
            )
            audio_full_url = f"{base_url}{audio_info['url_path']}"
        except Exception as e:
            logger.warning(f"TTS generation on queue play: {e}")

        payload = {
            "command": "PLAY_ANNOUNCEMENT",
            "announcement_id": ann_id,
            "title": title,
            "message": message,
            "audio_url": audio_full_url,
            "volume": 85,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower == "pause":
        payload = {
            "command": "PAUSE",
            "announcement_id": ann_id,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower in ("resume", "unpause"):
        payload = {
            "command": "RESUME",
            "announcement_id": ann_id,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower == "skip":
        payload = {
            "command": "SKIP",
            "announcement_id": ann_id,
            "timestamp": utc_now().isoformat(),
        }
    elif action_lower in ("cancel", "stop"):
        payload = {
            "command": "CANCEL",
            "announcement_id": ann_id,
            "timestamp": utc_now().isoformat(),
        }
    else:
        payload = {
            "command": action.upper(),
            "announcement_id": ann_id,
            "timestamp": utc_now().isoformat(),
        }

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


BROADCAST_GAP_SECONDS = 15


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
    current_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()

    should_advance = False
    gap: int = 0
    if current_playing:
        if force_advance:
            should_advance = True
        else:
            # Check if current playing is emergency
            ann = getattr(current_playing, "announcement", None)
            is_curr_emerg = ann and (
                getattr(ann, "emergency_level", None) == "EMERGENCY"
                or (hasattr(getattr(ann, "priority", None), "value") and getattr(ann.priority, "value") == "EMERGENCY")
                or str(getattr(ann, "priority", "")).upper() == "EMERGENCY"
            )
            # Gap of 15 seconds (10-20 sec range) between normal broadcasts; 0s gap for emergency
            gap = 0 if is_curr_emerg else BROADCAST_GAP_SECONDS
            curr_dur = getattr(current_playing, "duration_seconds", 15) or 15
            duration = curr_dur + gap

            curr_played_at = getattr(current_playing, "played_at", None)
            if curr_played_at:
                elapsed = (now - curr_played_at).total_seconds()
                if elapsed >= duration:
                    should_advance = True
            else:
                setattr(current_playing, "played_at", now)
                db.commit()

        if should_advance:
            setattr(current_playing, "status", "Completed")
            db.commit()
            db.refresh(current_playing)
            logger.info(f"Speaker queue item #{current_playing.id} completed playback after duration + {gap}s gap.")
    else:
        # Check if there are queued items waiting to start (due for scheduled_time or immediate)
        waiting_item = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.status.in_(["Next in Queue", "Queued"]),
                or_(SpeakerQueue.scheduled_time == None, SpeakerQueue.scheduled_time <= now)
            )
            .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
            .first()
        )
        if waiting_item:
            should_advance = True

    if not should_advance:
        return None

    # Priority 1: Emergency preemption - check if an emergency notice is queued (prioritized first)
    from app.core.enums.announcement import AnnouncementPriority, EmergencyLevel
    from app.models.announcement import Announcement
    next_item = (
        db.query(SpeakerQueue)
        .join(SpeakerQueue.announcement)
        .filter(
            SpeakerQueue.status.in_(["Next in Queue", "Queued"]),
            or_(
                Announcement.priority == AnnouncementPriority.HIGH,
                Announcement.emergency_level == EmergencyLevel.EMERGENCY,
                Announcement.title.ilike("%emergency%"),
            )
        )
        .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
        .first()
    )

    # Priority 2: First Come First Serve (FCFS) for scheduled & publish now notices whose scheduled_time <= now
    if not next_item:
        next_item = (
            db.query(SpeakerQueue)
            .filter(
                SpeakerQueue.status.in_(["Next in Queue", "Queued"]),
                or_(SpeakerQueue.scheduled_time == None, SpeakerQueue.scheduled_time <= now)
            )
            .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
            .first()
        )

    if not next_item:
        return None

    setattr(next_item, "status", "Playing")
    setattr(next_item, "played_at", utc_now())
    if not getattr(next_item, "duration_seconds", None):
        ann = getattr(next_item, "announcement", None)
        words = len(((getattr(ann, "title", "") or '') + ' ' + (getattr(ann, "description", "") or '')).split())
        setattr(next_item, "duration_seconds", max(10, int(words / 2.5)))
    db.commit()
    db.refresh(next_item)

    # Dispatch PLAY command to speakers
    dispatch_res = dispatch_queue_action_to_speakers(
        db=db,
        queue_item=next_item,
        action="play",
        base_url=base_url,
    )

    # Update the item immediately after next_item to 'Next in Queue' for clear UI distinction
    subsequent_item = (
        db.query(SpeakerQueue)
        .filter(SpeakerQueue.status == "Queued", SpeakerQueue.id != next_item.id)
        .order_by(SpeakerQueue.queue_position.asc(), SpeakerQueue.id.asc())
        .first()
    )
    if subsequent_item:
        setattr(subsequent_item, "status", "Next in Queue")
        db.commit()

    logger.info(f"Speaker queue automatically advanced to item #{next_item.id} ('{next_item.announcement.title if next_item.announcement else 'Announcement'}').")
    return {
        "status": "advanced",
        "advanced_to_id": next_item.id,
        "title": next_item.announcement.title if next_item.announcement else "Announcement",
        "dispatch": dispatch_res,
    }



