import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("echosphere.websocket_api")

router = APIRouter(tags=["Realtime Sync"])


@router.get("/ws/live")
def websocket_live_http_probe():
    """
    HTTP probe handler for /ws/live.
    Informs clients or scanners that this endpoint requires WebSocket protocol (ws:// or wss://).
    """
    return {
        "status": "online",
        "service": "EchoSphere Realtime WebSocket",
        "protocol": "WebSocket",
        "message": "Connect via ws:// or wss:// to establish real-time stream.",
    }


def _session_user(token):
    """The signed-in user for a socket's ?token=, only if its session is still open."""
    if not token or not token.strip():
        return None
    from app.core.dependencies import _resolve_session
    from app.db.database import SessionLocal

    with SessionLocal() as db:
        resolved = _resolve_session(token.strip(), db)
        if resolved is None:
            return None
        user = resolved[0]
        _ = user.role  # load before the session closes
        return user


@router.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket, token: str | None = None):
    """
    Real-time WebSocket endpoint for instant multi-device synchronization of:
    - Notice approval & rejection events
    - New notice creation
    - Notice updates and deletions
    Supports optional JWT token for authenticated role-targeted channels.
    """
    role = None
    user_id = None
    signed_in = _session_user(token)
    if signed_in is not None:
        role = signed_in.role.name if signed_in.role else "Student"
        user_id = signed_in.official_email or signed_in.usn or signed_in.username

    await ws_manager.connect(websocket, role=role, user_id=user_id)
    try:
        # Send initial connection acknowledgment
        await websocket.send_json({
            "event": "CONNECTED",
            "message": "EchoSphere Realtime Synchronization Active",
        })

        while True:
            # Keep socket alive and handle client heartbeat/ping
            data = await websocket.receive_text()
            if data in ("ping", '{"type":"ping"}', '{"event":"ping"}'):
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket session error: {e}")
        ws_manager.disconnect(websocket)


# =============================================================================
# Live Campus PA Microphone Streaming Endpoints (< 120ms Real-Time Audio)
# =============================================================================
from app.core.mic_stream_manager import mic_stream_manager


def _is_registered_speaker(mac: str) -> bool:
    # Strict format + exact match: a LIKE pattern would let "%" pose as any registered speaker
    import re
    from sqlalchemy import func
    from app.db.database import SessionLocal
    from app.models.speaker_node import SpeakerNode
    if not re.fullmatch(r"([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", mac or ""):
        return False
    with SessionLocal() as db:
        return db.query(SpeakerNode.id).filter(func.upper(SpeakerNode.mac_address) == mac.upper()).first() is not None


@router.websocket("/ws/speaker/{mac}")
async def websocket_speaker_push_endpoint(websocket: WebSocket, mac: str):
    """
    Command push channel for speaker nodes: commands queued for this speaker are sent here
    the moment they are queued (see app.core.speaker_push). Read-only from the speaker's side.
    """
    from starlette.concurrency import run_in_threadpool
    from app.core import speaker_push

    if not await run_in_threadpool(_is_registered_speaker, mac):
        await websocket.close(code=4404)
        return
    await websocket.accept()
    speaker_push.register(mac, websocket)
    # print (not logger.info): app INFO logs are hidden on Render, and these show speaker connectivity
    print(f"[SPEAKER PUSH] {mac} connected", flush=True)
    try:
        while True:
            # The speaker only sends keep-alive text; reading detects disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[SPEAKER PUSH] {mac} session error: {e}", flush=True)
    finally:
        speaker_push.unregister(mac, websocket)
        print(f"[SPEAKER PUSH] {mac} disconnected", flush=True)


@router.get("/ws/hardware/mic-status")
def get_mic_stream_status():
    """
    Returns real-time status of the Live Campus PA broadcast system,
    including active broadcast session details and registered speaker listeners.
    """
    active = mic_stream_manager.active_session is not None
    sess = mic_stream_manager.active_session or {}

    listeners_summary = []
    for ws, meta in list(mic_stream_manager.listener_meta.items()):
        listeners_summary.append({
            "mac_address": meta.get("mac_address", ""),
            "zone": meta.get("zone", "College-Wide"),
            "dept": meta.get("dept", "General"),
            "connected_at": meta.get("connected_at"),
        })

    return {
        "is_active": active,
        "session": sess,
        "listener_count": len(mic_stream_manager.listeners),
        "listeners": listeners_summary,
    }


@router.get("/ws/hardware/mic-stream")
@router.get("/ws/hardware/mic-listen")
def mic_stream_http_probe():
    """HTTP probe informing clients that these endpoints require WebSocket connection."""
    return {
        "status": "online",
        "service": "EchoSphere Live Microphone PA Audio Stream",
        "protocol": "WebSocket (Binary PCM 16kHz Mono)",
        "message": "Connect via ws:// or wss:// to stream or listen to live voice frames.",
    }


@router.websocket("/ws/hardware/mic-listen")
async def websocket_mic_listen_endpoint(
    websocket: WebSocket,
    mac_address: str | None = None,
    zone: str | None = None,
    dept: str | None = None,
):
    """
    WebSocket endpoint for hardware speaker nodes (ESP32 / Raspberry Pi / Edge Clients)
    to receive real-time binary audio frames (16kHz 16-bit PCM) during live PA broadcasts.
    """
    await mic_stream_manager.register_listener(
        websocket,
        mac_address=mac_address,
        zone=zone,
        dept=dept,
    )
    try:
        # Send initial confirmation
        await websocket.send_json({
            "event": "LISTENER_CONNECTED",
            "message": "Subscribed to live campus PA voice streams.",
            "mac_address": mac_address,
            "zone": zone or "College-Wide",
        })

        while True:
            # Handle client keepalives and status pings
            data = await websocket.receive_text()
            if data in ("ping", '{"type":"ping"}', '{"event":"ping"}'):
                await websocket.send_text('{"event":"pong"}')
    except WebSocketDisconnect:
        mic_stream_manager.unregister_listener(websocket)
    except Exception as e:
        logger.debug(f"[Live PA] Listener websocket disconnected: {e}")
        mic_stream_manager.unregister_listener(websocket)


@router.websocket("/ws/hardware/mic-stream")
async def websocket_mic_stream_endpoint(
    websocket: WebSocket,
    token: str | None = None,
    zone: str | None = "College-Wide",
    is_emergency: bool = False,
):
    """
    WebSocket endpoint for authorized administrators and faculty to stream
    live microphone audio directly to campus corridor speakers.
    Accepts:
    - Raw binary PCM frames (16-bit mono 16kHz) forwarded immediately (< 120ms)
    - JSON text commands: {"command": "STOP"} or {"command": "CHANGE_ZONE", "zone": "..."}
    """
    broadcaster_name = "Campus Administrator"

    # Only a signed-in staff member with an open session may speak through the campus speakers
    broadcaster = _session_user(token)
    if broadcaster is None:
        logger.warning("[Live PA] Refused mic stream without a valid session.")
        await websocket.close(code=1008, reason="Sign in to use the campus PA microphone.")
        return
    broadcaster_id = broadcaster.official_email or broadcaster.usn or broadcaster.username
    broadcaster_name = broadcaster.full_name or broadcaster_name
    broadcaster_role = broadcaster.role.name if broadcaster.role else "Student"

    # Restrict live broadcast to authorized staff/admin roles
    norm_role = str(broadcaster_role).lower()
    if norm_role in ("student", "guest"):
        logger.warning(f"[Live PA] Unauthorized role '{broadcaster_role}' attempted live broadcast.")
        await websocket.close(code=1008, reason="Students are not authorized to use the campus PA microphone.")
        return

    await websocket.accept()
    session = await mic_stream_manager.start_broadcast_session(
        broadcaster_user_id=broadcaster_id,
        broadcaster_name=broadcaster_name,
        broadcaster_role=broadcaster_role,
        zone=zone or "College-Wide",
        is_emergency=bool(is_emergency),
    )

    await websocket.send_json({
        "event": "SESSION_STARTED",
        "session_id": session.get("session_id"),
        "zone": session.get("zone"),
        "is_emergency": session.get("is_emergency"),
        "listener_count": len(mic_stream_manager.listeners),
    })

    current_zone = zone or "College-Wide"

    try:
        while True:
            # WebSocket receives either binary bytes (audio PCM) or text commands
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                await mic_stream_manager.forward_audio_chunk(audio_bytes, target_zone=current_zone)
            elif "text" in message and message["text"]:
                txt = message["text"].strip()
                if txt in ("ping", '{"type":"ping"}', '{"event":"ping"}'):
                    await websocket.send_text('{"event":"pong"}')
                elif "STOP" in txt.upper():
                    logger.info("[Live PA] Broadcaster sent STOP command.")
                    break
                else:
                    try:
                        import json
                        cmd_obj = json.loads(txt)
                        if cmd_obj.get("command") == "CHANGE_ZONE":
                            new_zone = cmd_obj.get("zone")
                            if new_zone:
                                current_zone = new_zone
                                logger.info(f"[Live PA] Switched target broadcast zone to '{current_zone}'")
                        elif cmd_obj.get("command") == "STOP":
                            break
                    except Exception:
                        pass
    except WebSocketDisconnect:
        logger.info(f"[Live PA] Broadcaster disconnected gracefully.")
    except Exception as e:
        logger.warning(f"[Live PA] Broadcaster stream loop error: {e}")
    finally:
        await mic_stream_manager.end_broadcast_session()
        try:
            await websocket.send_json({"event": "SESSION_ENDED", "message": "Broadcast session ended."})
        except Exception:
            pass

