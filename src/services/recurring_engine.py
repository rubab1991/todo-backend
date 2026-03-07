"""
Recurring Task Engine — Phase V (T006/T047/T048/T050).
When a recurring task is completed, automatically spawns the next instance
with a computed due date based on the recurrence interval.
"""
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from calendar import monthrange

import httpx

logger = logging.getLogger(__name__)

# Internal API base URL — backend calls itself
INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")


def compute_next_due_date(
    current_due: Optional[str],
    interval: str,
    created_at: datetime,
) -> str:
    """
    Compute the next due date string (ISO format) from a recurrence interval.

    Args:
        current_due: ISO date/datetime string of the current due date (may be None)
        interval: "daily", "weekly", or "monthly"
        created_at: Task creation time, used as fallback base when due date is missing

    Returns:
        ISO date string (YYYY-MM-DD) for the next occurrence
    """
    if current_due:
        try:
            base = datetime.fromisoformat(current_due.replace("Z", "+00:00"))
        except ValueError:
            base = created_at
    else:
        # No due date: use today + interval from task creation
        base = datetime.now(tz=timezone.utc)

    if interval == "daily":
        next_dt = base + timedelta(days=1)
    elif interval == "weekly":
        next_dt = base + timedelta(weeks=1)
    elif interval == "monthly":
        year, month, day = base.year, base.month, base.day
        # Advance month by 1, handling year rollover
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        # Clamp day to max days in the new month (e.g. Jan 31 → Feb 28)
        max_day = monthrange(year, month)[1]
        day = min(day, max_day)
        next_dt = base.replace(year=year, month=month, day=day)
    else:
        logger.warning("Unknown recurrence interval '%s'; defaulting to daily", interval)
        next_dt = base + timedelta(days=1)

    return next_dt.strftime("%Y-%m-%d")


async def handle_recurring_task_completion(
    event_type: str, task_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """
    If a completed task has a recurringInterval, create the next instance
    by calling the internal task creation API.

    Returns the newly created task dict, or None if not applicable.
    """
    # Only act on task completion events for recurring tasks
    if event_type != "task.updated":
        return None
    if not task_data.get("isComplete"):
        return None
    recurring_interval = task_data.get("recurringInterval")
    if not recurring_interval:
        return None

    user_id = task_data.get("userId")
    title = task_data.get("title", "")
    created_at_str = task_data.get("createdAt", datetime.utcnow().isoformat())
    current_due = task_data.get("dueDate")

    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        created_at = datetime.now(tz=timezone.utc)

    next_due = compute_next_due_date(current_due, recurring_interval, created_at)

    new_task_payload = {
        "title": title,
        "description": task_data.get("description"),
        "isComplete": False,
        "dueDate": next_due,
        "priority": task_data.get("priority", "medium"),
        "tags": task_data.get("tags", []),
        "recurringInterval": recurring_interval,
        "reminderAt": None,  # Do not copy reminder to next instance
    }

    url = f"{INTERNAL_API_BASE}/api/{user_id}/tasks"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Internal call — pass a special header to bypass auth for self-calls
            resp = await client.post(
                url,
                json=new_task_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Call": "recurring-engine",
                },
            )
            if resp.status_code in (200, 201):
                logger.info(
                    "Recurring engine: created next instance of '%s' due %s (interval=%s)",
                    title, next_due, recurring_interval,
                )
                return resp.json()
            else:
                logger.warning(
                    "Recurring engine: failed to create next task — HTTP %d: %s",
                    resp.status_code, resp.text,
                )
                return None
    except Exception as exc:
        logger.error("Recurring engine error for task '%s': %s", title, exc)
        return None
