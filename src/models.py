from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


# -------------------------------
# USER MODEL
# -------------------------------
class User(SQLModel, table=True):
    id: str = Field(primary_key=True)
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# -------------------------------
# TASK MODELS
# -------------------------------
class TaskBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    user_id: str  # reference to User.id
    due_date: Optional[str] = Field(default=None)  # due date field
    priority: str = Field(default="medium")  # priority field (low, medium, high)


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Schemas
class TaskCreate(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)
    completed: bool = Field(default=False)
    due_date: Optional[str] = Field(default=None)  # due date field
    priority: str = Field(default="medium")  # priority field (low, medium, high)
    # user_id is not included in TaskCreate since it's derived from the JWT/auth


class TaskRead(SQLModel):
    id: int
    title: str
    description: Optional[str] = None
    completed: bool
    user_id: str
    due_date: Optional[str] = None
    priority: str
    created_at: datetime
    updated_at: datetime


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
