from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime


class TaskBase(SQLModel):
    title: str = Field(nullable=False)
    description: Optional[str] = None
    status: str = Field(default="pending", nullable=False)  # "pending" or "completed"
    completed: bool = Field(default=False)
    due_date: Optional[str] = Field(default=None)
    priority: str = Field(default="medium")  # "low", "medium", "high"
    # Phase V: tags, recurring, reminder
    tags: Optional[str] = Field(default=None)  # JSON-encoded list e.g. '["work","urgent"]'
    recurring_interval: Optional[str] = Field(default=None)  # "daily","weekly","monthly"
    reminder_at: Optional[str] = Field(default=None)  # ISO datetime string


class Task(TaskBase, table=True):
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    # Relationship
    user: "User" = Relationship(back_populates="tasks")


class TaskRead(TaskBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime


class TaskCreate(TaskBase):
    pass


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[str] = None
    recurring_interval: Optional[str] = None
    reminder_at: Optional[str] = None
