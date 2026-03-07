"""
Dapr Pub/Sub event subscription handler.
Dapr calls these endpoints when events arrive on the configured topics.
"""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any, Dict, Optional
from ..services.websocket_manager import ws_manager
from ..services.recurring_engine import handle_recurring_task_completion
from ..services.audit_service import record_event as audit_record_event  # T066

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dapr", tags=["events"])

PUBSUB_NAME = "kafka-pubsub"


class DaprEventEnvelope(BaseModel):
    """Dapr CloudEvent envelope."""
    data: Optional[Dict[str, Any]] = None
    datacontenttype: Optional[str] = None
    id: Optional[str] = None
    pubsubname: Optional[str] = None
    source: Optional[str] = None
    topic: Optional[str] = None
    type: Optional[str] = None


# ── Dapr subscription declaration ────────────────────────────────────────────

@router.get("/subscribe")
async def dapr_subscribe():
    """Tell Dapr which topics this app subscribes to."""
    return [
        {
            "pubsubname": PUBSUB_NAME,
            "topic": "task-updates",
            "route": "/dapr/events/task-updates",
        },
        {
            "pubsubname": PUBSUB_NAME,
            "topic": "reminders",
            "route": "/dapr/events/reminders",
        },
        {
            "pubsubname": PUBSUB_NAME,
            "topic": "task-events",
            "route": "/dapr/events/task-events",
        },
    ]


# ── task-updates handler (real-time WebSocket broadcast) ─────────────────────

@router.post("/events/task-updates")
async def handle_task_updates(event: DaprEventEnvelope):
    """
    Receive task-updates events from Redpanda and broadcast to connected WebSocket clients.
    """
    data = event.data or {}
    user_id = data.get("user_id")
    if user_id:
        await ws_manager.broadcast_to_user(user_id, {
            "type": "task_update",
            "event_type": data.get("event_type"),
            "task": data.get("task"),
        })
        logger.info("Broadcast task_update to user=%s", user_id)
    return {"status": "SUCCESS"}


# ── reminders handler ─────────────────────────────────────────────────────────

@router.post("/events/reminders")
async def handle_reminders(event: DaprEventEnvelope):
    """
    Receive reminder events and push WebSocket notifications to the user.
    """
    data = event.data or {}
    user_id = data.get("user_id")
    task_id = data.get("task_id")
    title = data.get("title", "Task Reminder")
    if user_id:
        await ws_manager.broadcast_to_user(user_id, {
            "type": "reminder",
            "task_id": task_id,
            "title": title,
            "message": f"Reminder: {title}",
        })
        logger.info("Sent reminder notification to user=%s task=%s", user_id, task_id)
    return {"status": "SUCCESS"}


# ── task-events handler (audit log + recurring tasks) ────────────────────────

@router.post("/events/task-events")
async def handle_task_events(event: DaprEventEnvelope):
    """
    Receive all task CRUD events for audit logging and recurring task handling (T049).
    """
    data = event.data or {}
    event_type = data.get("event_type")
    task_data = data.get("task") or {}
    logger.info(
        "AUDIT | event_type=%s user=%s task_id=%s",
        event_type,
        data.get("user_id"),
        task_data.get("id"),
    )
    # T066: persist audit log entry (non-blocking)
    await audit_record_event(data)
    # T049: spawn next recurring task instance when a recurring task is completed
    if event_type and task_data:
        next_task = await handle_recurring_task_completion(event_type, task_data)
        if next_task:
            logger.info(
                "Recurring engine: spawned next task id=%s title=%s",
                next_task.get("id"),
                next_task.get("title"),
            )
    return {"status": "SUCCESS"}


# ── Dapr Jobs callback ────────────────────────────────────────────────────────

@router.post("/jobs/reminder")
async def job_reminder_callback(request: Request):
    """
    Dapr Jobs API invokes this endpoint when a scheduled reminder fires.
    """
    body = await request.json()
    job_data = body.get("data", body)
    user_id = job_data.get("user_id")
    task_id = job_data.get("task_id")
    title = job_data.get("title", "Task Reminder")

    if user_id:
        await ws_manager.broadcast_to_user(user_id, {
            "type": "reminder",
            "task_id": task_id,
            "title": title,
            "message": f"Reminder: {title}",
        })
        logger.info("Job reminder fired: user=%s task=%s", user_id, task_id)

    return {"status": "SUCCESS"}
