"""
Input validation utilities — Phase V.
"""
from datetime import datetime, timezone
from typing import Optional


def validate_reminder_at(reminder_at: Optional[str]) -> Optional[str]:
    """
    Validate that a reminder_at timestamp is in the future.
    Returns an error message string if invalid, or None if valid.
    """
    if not reminder_at:
        return None
    try:
        # Parse ISO format; assume UTC if no timezone
        dt = datetime.fromisoformat(reminder_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        if dt <= now:
            return "Reminder time must be in the future. Please provide a future date and time."
        return None
    except ValueError:
        return "Invalid reminder time format. Please use ISO 8601 format (e.g. 2026-04-10T09:00:00Z)."
