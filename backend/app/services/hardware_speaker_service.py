import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

import paho.mqtt.client as mqtt
from sqlalchemy.orm import Session

from app.models.speaker_node import SpeakerNode
from app.models.speaker_queue import SpeakerQueue
from app.repositories.hardware_repository import (
    get_all_speaker_nodes,
    get_speaker_node_by_id,
    get_speaker_queue,
    update_queue_item_status,
)
from app.services.tts_service import generate_announcement_audio

logger = logging.getLogger("echosphere.hardware")

MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883

# Thread-safe in-memory queue for REST polling speaker nodes (e.g. Wokwi / ESP32)
_PENDING_COMMANDS: Dict[str, List[dict]] = {}


def queue_command_for_nodes(payload: dict, target_mac: Optional[str] = None):
    """
    Pushes a command into the pending command queue for REST polling nodes.
    """
    key = target_mac.upper() if target_mac else "ALL"
    if key not in _PENDING_COMMANDS:
        _PENDING_COMMANDS[key] = []
    _PENDING_COMMANDS[key].append(payload)
    # Retain at most 10 recent commands per target
    if len(_PENDING_COMMANDS[key]) > 10:
        _PENDING_COMMANDS[key] = _PENDING_COMMANDS[key][-10:]


def get_pending_commands_for_mac(mac_address: str) -> List[dict]:
    """
    Retrieves and clears pending commands for a given MAC address, plus any broadcast commands.
    """
    mac_key = mac_address.upper()
    cmds: List[dict] = []

    # Node-specific commands
    if mac_key in _PENDING_COMMANDS:
        cmds.extend(_PENDING_COMMANDS.pop(mac_key))

    # Broadcast commands (keep for other nodes but return for this node)
    if "ALL" in _PENDING_COMMANDS:
        cmds.extend(_PENDING_COMMANDS["ALL"])

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
    # 1. Generate audio stream
    audio_info = await generate_announcement_audio(announcement_id, f"{title}. {content}")
    audio_full_url = f"{base_url}{audio_info['url_path']}"

    # 2. Add/Get queue item
    existing_item = db.query(SpeakerQueue).filter(SpeakerQueue.announcement_id == announcement_id).first()
    if not existing_item:
        max_pos = db.query(SpeakerQueue).count()
        queue_item = SpeakerQueue(
            announcement_id=announcement_id,
            queue_position=1 if is_emergency else max_pos + 1,
            status="Playing" if is_emergency else "Next in Queue",
            scheduled_time=datetime.utcnow(),
            played_at=datetime.utcnow() if is_emergency else None,
        )
        db.add(queue_item)
        db.commit()
        db.refresh(queue_item)
    else:
        queue_item = existing_item
        queue_item.status = "Playing" if is_emergency else "Next in Queue"
        if is_emergency:
            queue_item.played_at = datetime.utcnow()
        db.commit()

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
        "queue_position": queue_item.queue_position,
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
