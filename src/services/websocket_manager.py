"""
WebSocket connection manager for real-time task updates.
Maintains per-user connection pools and broadcasts task-update events.
"""
import json
import logging
from collections import defaultdict
from typing import Dict, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # user_id -> set of active WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = defaultdict(set)

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self._connections[user_id].add(websocket)
        logger.info("WebSocket connected: user=%s total=%d", user_id, len(self._connections[user_id]))

    def disconnect(self, user_id: str, websocket: WebSocket):
        self._connections[user_id].discard(websocket)
        if not self._connections[user_id]:
            del self._connections[user_id]
        logger.info("WebSocket disconnected: user=%s", user_id)

    async def broadcast_to_user(self, user_id: str, message: dict):
        """Send a message to all connections for a given user."""
        dead: Set[WebSocket] = set()
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def broadcast_all(self, message: dict):
        """Broadcast a message to all connected users (e.g., system notifications)."""
        for user_id in list(self._connections.keys()):
            await self.broadcast_to_user(user_id, message)


# Singleton instance shared across routes
ws_manager = WebSocketManager()
