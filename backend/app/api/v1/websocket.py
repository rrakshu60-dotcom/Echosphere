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
    Requires ?token=<access token> naming an open session.
    """
    # Only signed-in users with an open session may listen; notice titles are not public.
    signed_in = _session_user(token)
    if signed_in is None:
        await websocket.close(code=4401)
        return
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
    from app.core.speaker_auth import SPEAKER_KEY_HEADER, is_valid_device_key

    if not is_valid_device_key(mac, websocket.headers.get(SPEAKER_KEY_HEADER)):
        await websocket.close(code=4401)
        return
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
