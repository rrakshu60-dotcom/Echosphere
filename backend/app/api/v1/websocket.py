import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("echosphere.websocket_api")

router = APIRouter(tags=["Realtime Sync"])


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
    if token and token.strip():
        try:
            from app.core.jwt_handler import verify_access_token
            payload = verify_access_token(token.strip())
            role = payload.get("role")
            user_id = payload.get("id") or payload.get("sub")
        except Exception:
            pass

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
