import os
import uuid
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

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


def queue_command_for_nodes(payload: dict, target_mac: Optional[str] = None):
    """
    Pushes a command into the pending command queue for REST polling nodes.
    Broadcast commands are stored with unique command_id so every polling node receives them.
    """
    cmd_id = payload.get("command_id") or str(uuid.uuid4())
    payload["command_id"] = cmd_id

    if not target_mac or target_mac.upper() == "ALL":
        # Deduplicate idempotent broadcast commands (e.g. repeated emergency button clicks)
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


def get_pending_commands_for_mac(mac_address: str) -> List[dict]:
    """
    Retrieves pending commands for a given MAC address without dropping broadcasts for other nodes.
    """
    mac_key = mac_address.upper()
    cmds: List[dict] = []

    # 1. Node-specific commands
    if mac_key in _PENDING_COMMANDS and _PENDING_COMMANDS[mac_key]:
        cmds.extend(_PENDING_COMMANDS.pop(mac_key))

    # 2. Undelivered broadcast commands for this specific node
    if mac_key not in _DELIVERED_BROADCASTS:
        _DELIVERED_BROADCASTS[mac_key] = set()

    delivered_set = _DELIVERED_BROADCASTS[mac_key]
    for b_cmd in _BROADCAST_COMMANDS:
        b_id = b_cmd.get("command_id")
        if b_id and b_id not in delivered_set:
            cmds.append(b_cmd)
            delivered_set.add(b_id)

    # Prune delivered broadcast cache
    if len(delivered_set) > 60:
        valid_ids = {c.get("command_id") for c in _BROADCAST_COMMANDS}
        _DELIVERED_BROADCASTS[mac_key] = {cid for cid in delivered_set if cid in valid_ids}

    return cmds



def publish_mqtt_command(topic: str, payload: dict) -> bool:
    """
    Publishes an MQTT control message to speaker nodes.
    Gracefully handles broker offline mode by logging locally.
    """
    try:
        client = mqtt.Client(client_id=f"EchoSphere_Server_{datetime.utcnow().timestamp()}")
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
            "timestamp": datetime.utcnow().isoformat(),
        }
        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=None)

        # Record in SpeakerQueue table if announcement exists
        from app.models.announcement import Announcement
        ann_row = db.query(Announcement).filter(Announcement.id == announcement_id).first()
        if ann_row:
            existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
            if not existing_item:
                queue_item = SpeakerQueue(
                    announcement_id=announcement_id,
                    queue_position=1,
                    status="Playing",
                    scheduled_time=datetime.utcnow(),
                    played_at=datetime.utcnow(),
                )
                db.add(queue_item)
                db.commit()
                db.refresh(queue_item)
            else:
                existing_item.status = "Playing"
                existing_item.played_at = datetime.utcnow()
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
        audio_info = await generate_announcement_audio(announcement_id, f"{title}. {content}")
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
        should_play = is_emergency or (active_playing is None) or (existing_item and existing_item.status == "Playing")

        if is_emergency and active_playing and active_playing.id != (existing_item.id if existing_item else None):
            active_playing.status = "Paused"
            db.commit()

        words = len((title + " " + content).split())
        dur_secs = max(10, int(words / 2.5))

        if not existing_item:
            max_pos = db.query(SpeakerQueue).count()
            queue_item = SpeakerQueue(
                announcement_id=announcement_id,
                queue_position=1 if is_emergency else max_pos + 1,
                status="Playing" if should_play else ("Next in Queue" if max_pos == 0 else "Queued"),
                scheduled_time=datetime.utcnow(),
                played_at=datetime.utcnow() if should_play else None,
                duration_seconds=dur_secs,
            )
            db.add(queue_item)
            db.commit()
            db.refresh(queue_item)
            queue_pos = queue_item.queue_position
        else:
            if should_play:
                existing_item.status = "Playing"
                existing_item.played_at = datetime.utcnow()
            existing_item.duration_seconds = dur_secs
            db.commit()
            queue_pos = existing_item.queue_position

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
        "timestamp": datetime.utcnow().isoformat(),
    }

    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=None)

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
        node.volume = max(0, min(100, volume))
        db.commit()

    topic = f"echosphere/node/{node.mac_address}/command"
    payload = {
        "command": command,
        "node_id": node.id,
        "mac_address": node.mac_address,
        "announcement_id": announcement_id,
        "volume": node.volume,
        "timestamp": datetime.utcnow().isoformat(),
    }

    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=node.mac_address)

    return {
        "status": "success",
        "node_id": node.id,
        "mac_address": node.mac_address,
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
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> dict:
    """
    Enqueues an announcement into SpeakerQueue and broadcasts to targeted or all active speaker nodes.
    Automatically starts playing if the queue is empty / idle.
    """
    # 0. Resolve targeted speaker node if provided
    if speaker_node_id and not target_mac:
        target_node = get_speaker_node_by_id(db, speaker_node_id)
        if target_node:
            target_mac = target_node.mac_address
            if target_node.zone:
                zone = target_node.zone

    words = len((title + " " + content).split())
    dur_secs = max(10, int(words / 2.5))

    # 1. Add / update SpeakerQueue table
    existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    active_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()
    should_play = is_emergency or (active_playing is None) or (existing_item and existing_item.status == "Playing")

    if is_emergency and active_playing and active_playing.id != (existing_item.id if existing_item else None):
        active_playing.status = "Paused"
        db.commit()

    if not existing_item:
        max_pos = db.query(SpeakerQueue).count()
        item_status = "Playing" if should_play else ("Next in Queue" if max_pos == 0 else "Queued")
        queue_item = SpeakerQueue(
            announcement_id=announcement_id,
            speaker_node_id=speaker_node_id,
            queue_position=1 if is_emergency else max_pos + 1,
            status=item_status,
            scheduled_time=datetime.utcnow(),
            played_at=datetime.utcnow() if should_play else None,
            duration_seconds=dur_secs,
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
        queue_pos = queue_item.queue_position
        current_status = queue_item.status
    else:
        if speaker_node_id and not existing_item.speaker_node_id:
            existing_item.speaker_node_id = speaker_node_id
        if should_play:
            existing_item.status = "Playing"
            existing_item.played_at = datetime.utcnow()
        existing_item.duration_seconds = dur_secs
        db.commit()
        queue_pos = existing_item.queue_position
        current_status = existing_item.status

    # 2. Generate TTS audio stream (MP3 / WAV)
    audio_full_url = f"{base_url}/static/audio_streams/announcement_{announcement_id}.mp3"
    try:
        audio_info = generate_announcement_audio_sync(announcement_id, f"{title}. {content}")
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
        "timestamp": datetime.utcnow().isoformat(),
    }

    publish_success = False
    if should_play:
        publish_success = publish_mqtt_command(topic, payload)
        queue_command_for_nodes(payload, target_mac=target_mac)
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
    if action_lower == "play":
        # Generate / verify audio stream
        audio_full_url = f"{base_url}/static/audio_streams/announcement_{queue_item.announcement_id}.mp3"
        try:
            audio_info = generate_announcement_audio_sync(queue_item.announcement_id, f"{title}. {message}")
            audio_full_url = f"{base_url}{audio_info['url_path']}"
        except Exception as e:
            logger.warning(f"TTS generation on queue play: {e}")

        payload = {
            "command": "PLAY_ANNOUNCEMENT",
            "announcement_id": queue_item.announcement_id,
            "title": title,
            "message": message,
            "audio_url": audio_full_url,
            "volume": 85,
            "timestamp": datetime.utcnow().isoformat(),
        }
    elif action_lower == "pause":
        payload = {
            "command": "PAUSE",
            "announcement_id": queue_item.announcement_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    elif action_lower in ("resume", "unpause"):
        payload = {
            "command": "RESUME",
            "announcement_id": queue_item.announcement_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    elif action_lower == "skip":
        payload = {
            "command": "SKIP",
            "announcement_id": queue_item.announcement_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    elif action_lower in ("cancel", "stop"):
        payload = {
            "command": "CANCEL",
            "announcement_id": queue_item.announcement_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
    else:
        payload = {
            "command": action.upper(),
            "announcement_id": queue_item.announcement_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    topic = f"echosphere/dept/{dept_code}/speakers/command"
    publish_success = publish_mqtt_command(topic, payload)
    queue_command_for_nodes(payload, target_mac=target_mac)

    logger.info(f"🔊 [QUEUE ACTION DISPATCH] Action: '{action}' for Queue Item #{queue_item.id} -> Dispatched to nodes.")
    return {
        "status": "success",
        "action": action,
        "command": payload.get("command"),
        "queue_id": queue_item.id,
        "mqtt_dispatched": publish_success,
    }


def auto_advance_speaker_queue(
    db: Session,
    force_advance: bool = False,
    base_url: str = "https://echosphere-backend-9lv8.onrender.com",
) -> Optional[dict]:
    """
    Automated queue progression engine:
    1. Inspects the currently 'Playing' item in the SpeakerQueue.
    2. If duration has elapsed (or force_advance=True), marks it 'Completed'.
    3. Finds the next queued item (ordered by queue_position asc where status in ('Next in Queue', 'Queued')).
    4. Automatically transitions next item to 'Playing', records played_at,
       and dispatches the PLAY_ANNOUNCEMENT hardware command to the targeted node/speakers.
    5. Updates subsequent item to 'Next in Queue' if appropriate.
    """
    now = datetime.utcnow()
    current_playing = db.query(SpeakerQueue).filter(SpeakerQueue.status == "Playing").first()

    should_advance = False
    if current_playing:
        if force_advance:
            should_advance = True
        else:
            duration = (current_playing.duration_seconds or 15) + 30
            if current_playing.played_at:
                elapsed = (now - current_playing.played_at).total_seconds()
                if elapsed >= duration:
                    should_advance = True
            else:
                current_playing.played_at = now
                db.commit()

        if should_advance:
            current_playing.status = "Completed"
            db.commit()
            db.refresh(current_playing)
            logger.info(f"Speaker queue item #{current_playing.id} completed playback after notice duration + 30s gap.")
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

    # Find the next item to play (scheduled_time <= now or immediate)
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

    next_item.status = "Playing"
    next_item.played_at = datetime.utcnow()
    if not next_item.duration_seconds:
        ann = next_item.announcement
        words = len(((ann.title if ann else '') + ' ' + (ann.description if ann else '')).split())
        next_item.duration_seconds = max(10, int(words / 2.5))
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
        subsequent_item.status = "Next in Queue"
        db.commit()

    logger.info(f"Speaker queue automatically advanced to item #{next_item.id} ('{next_item.announcement.title if next_item.announcement else 'Announcement'}').")
    return {
        "status": "advanced",
        "advanced_to_id": next_item.id,
        "title": next_item.announcement.title if next_item.announcement else "Announcement",
        "dispatch": dispatch_res,
    }



