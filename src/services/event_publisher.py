"""
Dapr Pub/Sub event publisher for task events.
Publishes to Redpanda (Kafka-compatible) topics via Dapr sidecar HTTP API.
Credentials are managed by Dapr — never hardcoded here.
"""
import json
import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

# Dapr sidecar base URL (injected by Dapr runtime)
DAPR_HTTP_PORT = int(os.getenv("DAPR_HTTP_PORT", "3500"))
DAPR_BASE_URL = f"http://localhost:{DAPR_HTTP_PORT}"

# Pub/Sub component name (matches infra/dapr/components/kafka-pubsub.yaml)
PUBSUB_NAME = "kafka-pubsub"

# Topic names
TOPIC_TASK_EVENTS = "task-events"
TOPIC_REMINDERS = "reminders"
TOPIC_TASK_UPDATES = "task-updates"


async def publish_event(topic: str, event_data: Dict[str, Any]) -> bool:
    """Publish an event to a Dapr pub/sub topic."""
    url = f"{DAPR_BASE_URL}/v1.0/publish/{PUBSUB_NAME}/{topic}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                url,
                json=event_data,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code in (200, 204):
                logger.info("Published event to topic '%s': %s", topic, event_data.get("event_type"))
                return True
            else:
                logger.warning("Dapr publish returned %d for topic '%s'", resp.status_code, topic)
                return False
    except httpx.ConnectError:
        # Dapr sidecar not available (e.g., local dev without Dapr) — log and continue
        logger.debug("Dapr sidecar not reachable — skipping event publish for topic '%s'", topic)
        return False
    except Exception as exc:
        logger.error("Failed to publish event to '%s': %s", topic, exc)
        return False


async def publish_task_event(event_type: str, task_data: Dict[str, Any], user_id: str) -> bool:
    """Publish a task CRUD event to task-events and task-updates topics."""
    payload = {
        "event_type": event_type,  # "task.created", "task.updated", "task.deleted"
        "user_id": user_id,
        "task": task_data,
    }
    # Publish to task-events (audit / processing) and task-updates (real-time sync)
    results = [
        await publish_event(TOPIC_TASK_EVENTS, payload),
        await publish_event(TOPIC_TASK_UPDATES, payload),
    ]
    return all(results)


async def publish_reminder_event(task_id: int, user_id: str, title: str, reminder_at: str) -> bool:
    """Publish a reminder scheduling event to the reminders topic."""
    payload = {
        "event_type": "reminder.scheduled",
        "task_id": task_id,
        "user_id": user_id,
        "title": title,
        "reminder_at": reminder_at,
    }
    return await publish_event(TOPIC_REMINDERS, payload)
