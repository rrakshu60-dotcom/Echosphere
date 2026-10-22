"""
Instant command push to speaker nodes over a WebSocket.

Speakers keep one socket open to /api/v1/ws/speaker/{mac}. Every command queued for them
(play, pause, stop, volume...) is sent down that socket the moment it is queued, instead of
waiting for the next HTTP heartbeat. Heartbeats still deliver the same commands as a fallback;
the firmware runs each command_id only once.
"""

import asyncio
import json
import logging
import threading
from typing import Dict, Optional, Set

from fastapi import WebSocket

logger = logging.getLogger("echosphere.speaker_push")

_LOCK = threading.Lock()
# MAC (upper case) -> open sockets from that speaker
_SOCKETS: Dict[str, Set[WebSocket]] = {}
# The server event loop that owns the sockets; sync code hands sends to it
_LOOP: Optional[asyncio.AbstractEventLoop] = None


def register(mac: str, websocket: WebSocket) -> None:
    global _LOOP
    _LOOP = asyncio.get_running_loop()
    with _LOCK:
        _SOCKETS.setdefault(mac.upper(), set()).add(websocket)


def unregister(mac: str, websocket: WebSocket) -> None:
    with _LOCK:
        sockets = _SOCKETS.get(mac.upper())
        if sockets:
            sockets.discard(websocket)
            if not sockets:
                _SOCKETS.pop(mac.upper(), None)


def connected_macs() -> Set[str]:
    with _LOCK:
        return set(_SOCKETS)


async def _send(mac: str, websocket: WebSocket, message: str) -> None:
    try:
        await websocket.send_text(message)
    except Exception as e:
        logger.info(f"Speaker push to {mac} failed ({e}); it will get the command by heartbeat")
        unregister(mac, websocket)


def push_command(payload: dict, target_mac: Optional[str] = None) -> int:
    """Send one command to the targeted speaker (or all speakers). Returns how many sockets it went to.

    Safe to call from any thread, including the event loop itself: it never blocks.
    """
    loop = _LOOP
    if loop is None or loop.is_closed():
        return 0
    with _LOCK:
        if not target_mac or target_mac.upper() == "ALL":
            targets = [(mac, ws) for mac, sockets in _SOCKETS.items() for ws in sockets]
        else:
            targets = [(target_mac.upper(), ws) for ws in _SOCKETS.get(target_mac.upper(), ())]
    if not targets:
        return 0
    # Same shape as the heartbeat response, so the firmware parses both the same way
    message = json.dumps({"pending_commands": [payload]}, default=str)
    for mac, ws in targets:
        asyncio.run_coroutine_threadsafe(_send(mac, ws, message), loop)
    return len(targets)
