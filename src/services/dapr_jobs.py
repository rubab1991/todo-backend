"""
Dapr Jobs API integration for scheduling task reminders.
Uses the Dapr Jobs HTTP API to schedule exact one-shot reminders.
"""
import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

DAPR_HTTP_PORT = int(os.getenv("DAPR_HTTP_PORT", "3500"))
DAPR_BASE_URL = f"http://localhost:{DAPR_HTTP_PORT}"
APP_ID = os.getenv("DAPR_APP_ID", "todo-backend")


async def schedule_reminder(task_id: int, user_id: str, title: str, due_iso: str) -> bool:
    """
    Schedule a one-shot reminder job via Dapr Jobs API.
    The job will invoke /api/jobs/reminder on this service at the due time.
    """
    job_name = f"reminder-{task_id}-{user_id}"
    url = f"{DAPR_BASE_URL}/v1.0-alpha1/jobs/{job_name}"
    payload = {
        "schedule": due_iso,  # RFC3339 / ISO8601 trigger time
        "repeats": 1,
        "data": {
            "task_id": task_id,
            "user_id": user_id,
            "title": title,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code in (200, 204):
                logger.info("Scheduled reminder job '%s' for %s", job_name, due_iso)
                return True
            logger.warning("Dapr Jobs API returned %d for job '%s'", resp.status_code, job_name)
            return False
    except httpx.ConnectError:
        logger.debug("Dapr sidecar not reachable — skipping job scheduling for task %d", task_id)
        return False
    except Exception as exc:
        logger.error("Failed to schedule reminder job '%s': %s", job_name, exc)
        return False


async def cancel_reminder(task_id: int, user_id: str) -> bool:
    """Cancel a previously scheduled reminder job."""
    job_name = f"reminder-{task_id}-{user_id}"
    url = f"{DAPR_BASE_URL}/v1.0-alpha1/jobs/{job_name}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.delete(url)
            return resp.status_code in (200, 204, 404)
    except Exception as exc:
        logger.error("Failed to cancel reminder '%s': %s", job_name, exc)
        return False
