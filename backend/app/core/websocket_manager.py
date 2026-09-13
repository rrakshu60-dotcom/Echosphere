import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import WebSocket

logger = logging.getLogger("echosphere.websocket")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_meta: Dict[WebSocket, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, role: str | None = None, user_id: int | None = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_meta[websocket] = {"role": role, "user_id": user_id}
        logger.info(f"WebSocket client connected (role={role}, user_id={user_id}). Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        self.connection_meta.pop(websocket, None)
        logger.info(f"WebSocket client disconnected. Remaining connections: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any], target_roles: List[str] | None = None):
        """
        Broadcast JSON payload to all connected clients or filtered by target_roles.
        Dead connections are pruned.
        """
        if not self.active_connections:
            return

        payload_str = json.dumps(message)
        dead_connections = []

        for connection in list(self.active_connections):
            meta = self.connection_meta.get(connection, {})
            if target_roles is not None:
                client_role = meta.get("role")
                if client_role not in target_roles:
                    continue

            try:
                await connection.send_text(payload_str)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket client: {e}")
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def broadcast_sync(self, message: Dict[str, Any], target_roles: List[str] | None = None):
        """
        Thread-safe synchronous helper to schedule broadcast on the active event loop.
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(message, target_roles), loop)
            else:
                loop.run_until_complete(self.broadcast(message, target_roles))
        except Exception:
            try:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(self.broadcast(message, target_roles))
                new_loop.close()
            except Exception as ex:
                logger.warning(f"Failed to sync broadcast WebSocket event: {ex}")


ws_manager = ConnectionManager()
