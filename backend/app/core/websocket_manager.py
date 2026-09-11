import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import WebSocket

logger = logging.getLogger("echosphere.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        Broadcast JSON payload to all connected clients.
        Dead connections are pruned.
        """
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        dead_connections = []

        for connection in list(self.active_connections):
            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def broadcast_sync(self, message: Dict[str, Any]):
        """
        Thread-safe synchronous helper to schedule broadcast on the active event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message), loop)
            else:
                loop.run_until_complete(self.broadcast(message))
        except Exception:
            try:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(self.broadcast(message))
                new_loop.close()
            except Exception as ex:
                logger.warning(f"Failed to sync broadcast WebSocket event: {ex}")


ws_manager = ConnectionManager()
