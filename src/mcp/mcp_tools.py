import json
from typing import Dict, Any, List, Optional
from sqlmodel import select
from ..models.task import Task, TaskCreate
from ..models.user import User
from ..db.session import AsyncSessionLocal, get_or_create_user
from sqlalchemy.exc import IntegrityError


async def add_task(
    user_id: str,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    tags: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    recurring_interval: Optional[str] = None,
    reminder_at: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """MCP tool to add a new task (supports Phase V fields)."""
    async with AsyncSessionLocal() as session:
        try:
            await get_or_create_user(session, user_id)
            await session.commit()

            task = Task(
                title=title,
                description=description,
                status="pending",
                user_id=user_id,
                priority=priority,
                tags=json.dumps(tags) if tags else None,
                due_date=due_date,
                recurring_interval=recurring_interval,
                reminder_at=reminder_at,
            )

            session.add(task)
            await session.commit()
            await session.refresh(task)

            return {
                "task_id": task.id,
                "status": "created",
                "title": task.title,
                "priority": task.priority,
                "tags": json.loads(task.tags) if task.tags else [],
            }
        except IntegrityError as e:
            await session.rollback()
            raise ValueError(f"Error creating task: {str(e)}")


async def list_tasks(
    user_id: str,
    status: str = "all",
    search_query: Optional[str] = None,
) -> Dict[str, Any]:
    """MCP tool to list tasks with optional filtering."""
    async with AsyncSessionLocal() as session:
        query = select(Task).where(Task.user_id == user_id)

        if status and status != "all":
            query = query.where(Task.status == status)

        if search_query:
            query = query.where(Task.title.ilike(f"%{search_query}%"))

        result = await session.execute(query)
        tasks = result.scalars().all()

        return {
            "tasks": [
                {
                    "id": task.id,
                    "title": task.title,
                    "status": task.status,
                    "description": task.description,
                    "priority": task.priority,
                    "tags": json.loads(task.tags) if task.tags else [],
                    "dueDate": task.due_date,
                    "recurringInterval": task.recurring_interval,
                    "reminderAt": task.reminder_at,
                    "created_at": task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ],
            "status": "retrieved",
            "count": len(tasks),
        }


async def update_task(
    user_id: str,
    task_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    tags: Optional[List[str]] = None,
    due_date: Optional[str] = None,
    recurring_interval: Optional[str] = None,
    reminder_at: Optional[str] = None,
) -> Dict[str, Any]:
    """MCP tool to update a task (supports Phase V fields)."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        if title is not None:
            task.title = title
        if description is not None:
            task.description = description
        if priority is not None:
            task.priority = priority
        if tags is not None:
            task.tags = json.dumps(tags)
        if due_date is not None:
            task.due_date = due_date
        if recurring_interval is not None:
            task.recurring_interval = recurring_interval
        if reminder_at is not None:
            task.reminder_at = reminder_at

        await session.commit()
        await session.refresh(task)

        return {
            "task_id": task.id,
            "status": "updated",
            "title": task.title,
        }


async def complete_task(user_id: str, task_id: int) -> Dict[str, Any]:
    """MCP tool to complete a task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        task.status = "completed"
        task.completed = True
        await session.commit()
        await session.refresh(task)

        return {
            "task_id": task.id,
            "status": "completed",
            "title": task.title,
        }


async def delete_task(user_id: str, task_id: int) -> Dict[str, Any]:
    """MCP tool to delete a task."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        await session.delete(task)
        await session.commit()

        return {
            "task_id": task.id,
            "status": "deleted",
            "title": task.title,
        }
