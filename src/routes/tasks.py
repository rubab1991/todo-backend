import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import List, Optional
from sqlmodel import select
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel
from ..models import Task, TaskRead, TaskCreate, TaskUpdate
from ..db import get_async_session_dep, get_or_create_user
from ..auth import verify_user_id_match_with_email
from ..services.event_publisher import publish_task_event, publish_reminder_event
from ..services.dapr_jobs import schedule_reminder, cancel_reminder
from ..utils.tags import normalise_tags
from ..utils.validation import validate_reminder_at

logger = logging.getLogger(__name__)


# ── Frontend-compatible request models ──────────────────────────────────────

class FrontendTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    isComplete: Optional[bool] = False
    dueDate: Optional[str] = None
    priority: str = "medium"
    tags: Optional[List[str]] = None
    recurringInterval: Optional[str] = None
    reminderAt: Optional[str] = None


class FrontendTaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    isComplete: Optional[bool] = None
    dueDate: Optional[str] = None
    priority: Optional[str] = None
    tags: Optional[List[str]] = None
    recurringInterval: Optional[str] = None
    reminderAt: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _encode_tags(tags: Optional[List[str]]) -> Optional[str]:
    normalised = normalise_tags(tags)
    return json.dumps(normalised) if normalised else None


def _decode_tags(tags_str: Optional[str]) -> List[str]:
    if not tags_str:
        return []
    try:
        return json.loads(tags_str)
    except (json.JSONDecodeError, TypeError):
        return []


def _task_to_dict(task: Task) -> dict:
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "isComplete": task.completed,
        "userId": task.user_id,
        "dueDate": task.due_date,
        "priority": task.priority,
        "tags": _decode_tags(task.tags),
        "recurringInterval": task.recurring_interval,
        "reminderAt": task.reminder_at,
        "createdAt": task.created_at.isoformat(),
        "updatedAt": task.updated_at.isoformat(),
    }


router = APIRouter()


# ── GET /tasks ───────────────────────────────────────────────────────────────

@router.get("/{user_id}/tasks", tags=["tasks"])
async def get_tasks(
    user_id: str,
    search: Optional[str] = Query(None, description="Full-text search on title/description"),
    priority: Optional[str] = Query(None, description="Filter: low|medium|high"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    status: Optional[str] = Query(None, description="Filter: pending|completed"),
    sort_by: Optional[str] = Query("created_at", description="Sort: created_at|due_date|priority"),
    sort_order: Optional[str] = Query("desc", description="asc|desc"),
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, _ = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = await session.execute(select(Task).where(Task.user_id == user_id))
    tasks = result.scalars().all()

    if search and search.strip():  # T076: empty search = return all
        q = search.strip().lower()
        tasks = [t for t in tasks if q in (t.title or "").lower() or q in (t.description or "").lower()]
    if priority:
        tasks = [t for t in tasks if t.priority == priority]
    if status:
        is_complete = status == "completed"
        tasks = [t for t in tasks if t.completed == is_complete]
    if tag:
        tasks = [t for t in tasks if tag in _decode_tags(t.tags)]

    reverse = sort_order == "desc"
    _prio_order = {"high": 3, "medium": 2, "low": 1}
    if sort_by == "due_date":
        tasks = sorted(tasks, key=lambda t: t.due_date or "", reverse=reverse)
    elif sort_by == "priority":
        tasks = sorted(tasks, key=lambda t: _prio_order.get(t.priority, 0), reverse=reverse)
    else:
        tasks = sorted(tasks, key=lambda t: t.created_at, reverse=reverse)

    return [_task_to_dict(t) for t in tasks]


# ── POST /tasks ──────────────────────────────────────────────────────────────

@router.post("/{user_id}/tasks", status_code=201, tags=["tasks"])
async def create_task(
    user_id: str,
    task_data: FrontendTaskCreate,
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, email = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    try:
        user = await get_or_create_user(session, user_id, email=email)

        # T039: Validate reminder_at must be in future
        if task_data.reminderAt:
            reminder_err = validate_reminder_at(task_data.reminderAt)
            if reminder_err:
                raise HTTPException(status_code=422, detail=reminder_err)

        task = Task(
            title=task_data.title,
            description=task_data.description,
            completed=task_data.isComplete or False,
            due_date=task_data.dueDate,
            priority=task_data.priority,
            tags=_encode_tags(task_data.tags),
            recurring_interval=task_data.recurringInterval,
            reminder_at=task_data.reminderAt,
            user_id=user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)

        task_dict = _task_to_dict(task)

        await publish_task_event("task.created", task_dict, user_id)

        if task.reminder_at and task.id:
            await schedule_reminder(task.id, user_id, task.title, task.reminder_at)
            await publish_reminder_event(task.id, user_id, task.title, task.reminder_at)

        return task_dict
    except IntegrityError as e:
        logger.error("Integrity error creating task: %s", e)
        raise HTTPException(status_code=422, detail="Invalid task data")
    except Exception as e:
        logger.error("Error creating task: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── GET /tasks/{task_id} ──────────────────────────────────────────────────────

@router.get("/{user_id}/tasks/{task_id}", tags=["tasks"])
async def get_task(
    user_id: str,
    task_id: int = Path(..., gt=0),
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, _ = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = await session.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(task)


# ── PUT /tasks/{task_id} ──────────────────────────────────────────────────────

@router.put("/{user_id}/tasks/{task_id}", tags=["tasks"])
async def update_task(
    user_id: str,
    task_id: int = Path(..., gt=0),
    task_update: FrontendTaskUpdate = None,
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, _ = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = await session.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        update_data = task_update.dict(exclude_unset=True)
        field_map = {
            "isComplete": "completed",
            "dueDate": "due_date",
            "recurringInterval": "recurring_interval",
            "reminderAt": "reminder_at",
        }
        for field, value in update_data.items():
            backend_field = field_map.get(field, field)
            if field == "tags":
                task.tags = _encode_tags(value)
            elif hasattr(task, backend_field):
                setattr(task, backend_field, value)

        # T039: Validate new reminder_at if provided
        if "reminderAt" in update_data:
            reminder_err = validate_reminder_at(update_data.get("reminderAt"))
            if reminder_err:
                raise HTTPException(status_code=422, detail=reminder_err)

        task.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(task)

        task_dict = _task_to_dict(task)
        await publish_task_event("task.updated", task_dict, user_id)

        if "reminderAt" in update_data and task.reminder_at:
            await cancel_reminder(task_id, user_id)
            await schedule_reminder(task_id, user_id, task.title, task.reminder_at)
            await publish_reminder_event(task_id, user_id, task.title, task.reminder_at)

        return task_dict
    except IntegrityError as e:
        logger.error("Integrity error updating task: %s", e)
        raise HTTPException(status_code=422, detail="Invalid task data")
    except Exception as e:
        logger.error("Error updating task: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── DELETE /tasks/{task_id} ───────────────────────────────────────────────────

@router.delete("/{user_id}/tasks/{task_id}", status_code=204, tags=["tasks"])
async def delete_task(
    user_id: str,
    task_id: int = Path(..., gt=0),
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, _ = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = await session.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task_dict = _task_to_dict(task)
        await session.delete(task)
        await session.commit()
        await publish_task_event("task.deleted", task_dict, user_id)
        await cancel_reminder(task_id, user_id)
    except Exception as e:
        logger.error("Error deleting task: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── PATCH /tasks/{task_id}/complete ──────────────────────────────────────────

@router.patch("/{user_id}/tasks/{task_id}/complete", tags=["tasks"])
async def toggle_task_completion(
    user_id: str,
    task_id: int = Path(..., gt=0),
    user_data: tuple = Depends(verify_user_id_match_with_email),
    session=Depends(get_async_session_dep),
):
    authenticated_user_id, _ = user_data
    if authenticated_user_id != user_id:
        raise HTTPException(status_code=403, detail="Access forbidden")

    result = await session.execute(select(Task).where(Task.id == task_id, Task.user_id == user_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    try:
        task.completed = not task.completed
        task.status = "completed" if task.completed else "pending"
        task.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(task)

        task_dict = _task_to_dict(task)
        await publish_task_event("task.updated", task_dict, user_id)
        return task_dict
    except Exception as e:
        logger.error("Error toggling task: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")
