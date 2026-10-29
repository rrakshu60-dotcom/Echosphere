import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import WebSocket

logger = logging.getLogger("echosphere.websocket")


# Students only ever see published notices, so they are not told about drafts, pending or rejected ones.
_STAFF_ONLY_EVENTS = {"ANNOUNCEMENT_REJECTED"}


def _visible_to_role(message: Dict[str, Any], role: str | None) -> bool:
    if (role or "Student") != "Student":
        return True
    event = str(message.get("event", ""))
    if event in _STAFF_ONLY_EVENTS:
        return False
    if event == "ANNOUNCEMENT_CREATED":
        return str(message.get("status", "")).strip().lower() == "published"
    return True


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_meta: Dict[WebSocket, Dict[str, Any]] = {}
        # The server's event loop, which owns every WebSocket. Sync code (threadpool endpoints,
        # the queue daemon) must hand broadcasts to this loop, not send from a private loop.
        self._loop: asyncio.AbstractEventLoop | None = None

    async def connect(self, websocket: WebSocket, role: str | None = None, user_id: int | None = None):
        self._loop = asyncio.get_running_loop()
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
            if not _visible_to_role(message, meta.get("role")):
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
        if not self.active_connections:
            return
        loop = self._loop
        if loop is not None and loop.is_running():
            try:
                if asyncio.get_running_loop() is loop:
                    loop.create_task(self.broadcast(message, target_roles))
                    return
            except RuntimeError:
                pass  # called from a worker thread: no running loop here
            asyncio.run_coroutine_threadsafe(self.broadcast(message, target_roles), loop)
            return
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
