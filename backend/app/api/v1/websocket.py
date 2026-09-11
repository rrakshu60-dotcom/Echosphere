import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.websocket_manager import ws_manager

logger = logging.getLogger("echosphere.websocket_api")

router = APIRouter(tags=["Realtime Sync"])


@router.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket endpoint for instant multi-device synchronization of:
    - Notice approval & rejection events
    - New notice creation
    - Notice updates and deletions
    """
    await ws_manager.connect(websocket)
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
