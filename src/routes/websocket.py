"""
WebSocket endpoint for real-time task updates.
Clients connect to /ws/{user_id} to receive live task events.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from ..services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    user_id: str,
    websocket: WebSocket,
    token: str = Query(None, description="Bearer token for auth (optional pre-flight)"),
):
    """
    WebSocket endpoint for real-time task sync.
    Connects the client to the per-user broadcast channel.
    """
    await ws_manager.connect(user_id, websocket)
    # Send initial connection acknowledgement
    await websocket.send_json({"type": "connected", "user_id": user_id})
    try:
        while True:
            # Keep alive — clients may send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected cleanly: user=%s", user_id)
    except Exception as e:
        logger.error("WebSocket error for user=%s: %s", user_id, e)
        ws_manager.disconnect(user_id, websocket)
