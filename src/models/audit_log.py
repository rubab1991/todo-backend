"""
AuditLog model — Phase V (T064).
Persists every task CRUD event received via the task-events Dapr topic.
"""
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    event_type: str = Field(nullable=False)          # e.g. "task.created"
    task_id: Optional[str] = Field(default=None)     # stringified task id
    user_id: Optional[str] = Field(default=None)
    snapshot: Optional[str] = Field(default=None)    # JSON-encoded task snapshot
    created_at: datetime = Field(default_factory=datetime.utcnow)
