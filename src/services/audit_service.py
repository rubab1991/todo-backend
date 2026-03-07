"""
Audit Service — Phase V (T065).
Persists task-events to the audit_logs table for observability and compliance.
"""
import json
import logging
from typing import Any, Dict

from ..db import get_async_session
from ..models.audit_log import AuditLog

logger = logging.getLogger(__name__)


async def record_event(event_data: Dict[str, Any]) -> None:
    """
    Persist a single task event to the audit_logs table.
    Silently skips on DB error so that audit failures never block the event pipeline.
    """
    try:
        task_data = event_data.get("task") or {}
        task_id = str(task_data.get("id")) if task_data.get("id") is not None else None
        async with get_async_session() as session:
            entry = AuditLog(
                event_type=event_data.get("event_type", "unknown"),
                task_id=task_id,
                user_id=event_data.get("user_id"),
                snapshot=json.dumps(task_data) if task_data else None,
            )
            session.add(entry)
            # commit is handled by the context manager
        logger.debug("Audit recorded: event_type=%s task_id=%s", entry.event_type, task_id)
    except Exception as exc:
        logger.warning("Audit record failed (non-fatal): %s", exc)
