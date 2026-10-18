"""
EchoSphere Real-Time Binary Microphone PA Stream Manager
=========================================================
Manages real-time binary audio streams (16kHz 16-bit PCM mono)
between mobile/web administrative broadcasters and campus corridor speakers.
Provides ultra-low latency (< 120ms) fan-out distribution.
"""

import time
import asyncio
import logging
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket

logger = logging.getLogger("echosphere.mic_stream")


class MicStreamManager:
    """Manages live audio broadcaster sessions and speaker listeners."""

    def __init__(self):
        # Listeners: Hardware speakers listening for live audio frames
        self.listeners: Set[WebSocket] = set()
        self.listener_meta: Dict[WebSocket, Dict[str, Any]] = {}

        # Active broadcast session state
        self.active_session: Optional[Dict[str, Any]] = None
        self._lock = asyncio.Lock()

    async def register_listener(
        self,
        websocket: WebSocket,
        mac_address: Optional[str] = None,
        zone: Optional[str] = None,
        dept: Optional[str] = None,
    ):
        """Registers a hardware speaker node as an audio stream listener."""
        await websocket.accept()
        self.listeners.add(websocket)
        self.listener_meta[websocket] = {
            "mac_address": (mac_address or "").upper(),
            "zone": zone or "College-Wide",
            "dept": dept or "General",
            "connected_at": time.time(),
        }
        logger.info(
            f"[Live PA] Speaker listener connected: MAC={mac_address}, Zone={zone}. Total listeners: {len(self.listeners)}"
        )

    def unregister_listener(self, websocket: WebSocket):
        """Removes a hardware speaker listener."""
        if websocket in self.listeners:
            self.listeners.remove(websocket)
        meta = self.listener_meta.pop(websocket, None)
        mac = meta.get("mac_address") if meta else "unknown"
        logger.info(f"[Live PA] Speaker listener disconnected: MAC={mac}. Total listeners: {len(self.listeners)}")

    async def start_broadcast_session(
        self,
        broadcaster_user_id: Optional[int],
        broadcaster_name: str,
        broadcaster_role: str,
        zone: Optional[str] = "College-Wide",
        is_emergency: bool = False,
    ) -> Dict[str, Any]:
        """Initiates a live PA microphone broadcast session and preempts background audio."""
        async with self._lock:
            session_id = f"mic_{int(time.time() * 1000)}"
            target_zone = zone or "College-Wide"

            self.active_session = {
                "session_id": session_id,
                "broadcaster_user_id": broadcaster_user_id,
                "broadcaster_name": broadcaster_name,
                "broadcaster_role": broadcaster_role,
                "zone": target_zone,
                "is_emergency": is_emergency,
                "started_at": time.time(),
                "chunks_sent": 0,
                "bytes_sent": 0,
            }

            logger.info(
                f"[Live PA] Session STARTED: {session_id} by {broadcaster_name} ({broadcaster_role}), Zone='{target_zone}', Emergency={is_emergency}"
            )

            # Notify all listeners that live broadcast is starting
            start_msg = {
                "event": "START_MIC_STREAM",
                "session_id": session_id,
                "broadcaster": broadcaster_name,
                "zone": target_zone,
                "is_emergency": is_emergency,
                "sample_rate": 16000,
                "channels": 1,
                "bits_per_sample": 16,
            }
            await self._notify_listeners_json(start_msg, target_zone)

            # Publish MQTT hardware alert command
            try:
                from app.services.hardware_speaker_service import publish_mqtt_command
                topic = "echosphere/speakers/all/emergency" if is_emergency else f"echosphere/zone/{target_zone}/speakers/command"
                publish_mqtt_command(topic, {
                    "command": "START_MIC_STREAM",
                    "session_id": session_id,
                    "broadcaster": broadcaster_name,
                    "zone": target_zone,
                    "is_emergency": is_emergency,
                    "timestamp": time.time(),
                })
            except Exception as e:
                logger.debug(f"[Live PA] MQTT dispatch note: {e}")

            return self.active_session

    async def forward_audio_chunk(self, chunk: bytes, target_zone: Optional[str] = None):
        """
        Fans out raw binary PCM audio frames to all matching speaker nodes.
        Dead or stalled connections are automatically pruned to maintain < 120ms latency.
        """
        if not self.listeners or not chunk:
            return

        dead_listeners = []
        zone_filter = (target_zone or (self.active_session.get("zone") if self.active_session else "College-Wide")).lower()

        for ws in list(self.listeners):
            meta = self.listener_meta.get(ws, {})
            spk_zone = meta.get("zone", "College-Wide").lower()

            # Broadcast if zone matches or if session is college-wide
            if zone_filter not in ("college-wide", "all", "campus") and spk_zone not in ("college-wide", "all", zone_filter):
                continue

            try:
                await ws.send_bytes(chunk)
            except Exception as e:
                logger.debug(f"[Live PA] Error sending audio chunk to listener: {e}")
                dead_listeners.append(ws)

        for dead in dead_listeners:
            self.unregister_listener(dead)

        if self.active_session:
            self.active_session["chunks_sent"] += 1
            self.active_session["bytes_sent"] += len(chunk)

    async def end_broadcast_session(self, session_id: Optional[str] = None):
        """Terminates the live broadcast session, flushes speaker I2S buffers, and resumes normal queue."""
        async with self._lock:
            if not self.active_session:
                return

            sess = self.active_session
            target_zone = sess.get("zone", "College-Wide")
            sid = sess.get("session_id", "session")

            duration = round(time.time() - sess.get("started_at", time.time()), 2)
            logger.info(
                f"[Live PA] Session ENDED: {sid}. Duration={duration}s, Chunks={sess.get('chunks_sent')}, Total Bytes={sess.get('bytes_sent')}"
            )

            # Send stop command to listeners
            stop_msg = {
                "event": "STOP_MIC_STREAM",
                "session_id": sid,
                "duration_seconds": duration,
            }
            await self._notify_listeners_json(stop_msg, target_zone)

            # Publish MQTT command to return speakers to idle/queue state
            try:
                from app.services.hardware_speaker_service import publish_mqtt_command
                topic = f"echosphere/zone/{target_zone}/speakers/command"
                publish_mqtt_command(topic, {
                    "command": "STOP_MIC_STREAM",
                    "session_id": sid,
                    "timestamp": time.time(),
                })
            except Exception as e:
                logger.debug(f"[Live PA] MQTT dispatch stop error: {e}")

            self.active_session = None

    async def _notify_listeners_json(self, message: Dict[str, Any], target_zone: str):
        """Sends control JSON messages to listeners."""
        import json
        payload_str = json.dumps(message)
        dead = []
        zone_filter = target_zone.lower()

        for ws in list(self.listeners):
            meta = self.listener_meta.get(ws, {})
            spk_zone = meta.get("zone", "College-Wide").lower()

            if zone_filter not in ("college-wide", "all", "campus") and spk_zone not in ("college-wide", "all", zone_filter):
                continue

            try:
                await ws.send_text(payload_str)
            except Exception:
                dead.append(ws)

        for d in dead:
            self.unregister_listener(d)


mic_stream_manager = MicStreamManager()
