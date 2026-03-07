from typing import Dict, Any, Optional
from uuid import UUID
from sqlmodel import select
from ..models.task import Task, TaskUpdate
from ..db.session import AsyncSessionLocal


async def get_task_by_id(task_id: int, user_id: UUID) -> Optional[Task]:
    """
    Get a task by its ID for a specific user
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        return result.scalar_one_or_none()


async def validate_task_exists(task_id: int, user_id: UUID) -> bool:
    """
    Check if a task exists for a specific user
    """
    task = await get_task_by_id(task_id, user_id)
    return task is not None


async def update_task_status(task_id: int, user_id: UUID, status: str) -> Optional[Task]:
    """
    Update the status of a task
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return None

        task.status = status
        await session.commit()
        await session.refresh(task)

        return task


async def get_user_tasks(user_id: UUID, status: Optional[str] = None) -> list:
    """
    Get all tasks for a user, optionally filtered by status
    """
    async with AsyncSessionLocal() as session:
        query = select(Task).where(Task.user_id == user_id)

        if status:
            query = query.where(Task.status == status)

        result = await session.execute(query)
        return result.scalars().all()


async def delete_task_by_id(task_id: int, user_id: UUID) -> bool:
    """
    Delete a task by its ID for a specific user
    """
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Task).where(Task.id == task_id).where(Task.user_id == user_id)
        )
        task = result.scalar_one_or_none()

        if not task:
            return False

        await session.delete(task)
        await session.commit()

        return True