from typing import Dict, Any, List, Optional
from sqlmodel import select
from ..models.task import Task, TaskCreate
from ..models.user import User
from ..db.session import AsyncSessionLocal
from sqlalchemy.exc import IntegrityError


async def add_task(user_id: str, title: str, description: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    MCP tool to add a new task
    """
    async with AsyncSessionLocal() as session:
        try:
            # Create the task
            task = Task(
                title=title,
                description=description,
                status="pending",
                user_id=user_id
            )

            session.add(task)
            await session.commit()
            await session.refresh(task)

            return {
                "task_id": task.id,
                "status": "created",
                "title": task.title
            }
        except IntegrityError as e:
            await session.rollback()
            raise ValueError(f"Error creating task: {str(e)}")


async def list_tasks(user_id: str, status: str = "all") -> Dict[str, Any]:
    """
    MCP tool to list tasks
    """
    async with AsyncSessionLocal() as session:
        # Build query based on status
        query = select(Task).where(Task.user_id == user_id)

        if status != "all":
            query = query.where(Task.status == status)

        result = await session.execute(query)
        tasks = result.scalars().all()

        return {
            "tasks": [{"id": task.id, "title": task.title, "status": task.status,
                      "description": task.description, "created_at": task.created_at} for task in tasks],
            "status": "retrieved",
            "count": len(tasks)
        }


async def update_task(user_id: str, task_id: int, title: Optional[str] = None,
                     description: Optional[str] = None) -> Dict[str, Any]:
    """
    MCP tool to update a task
    """
    async with AsyncSessionLocal() as session:
        # Get the task
        result = await session.execute(select(Task).where(Task.id == task_id).where(Task.user_id == user_id))
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        # Update the task if new values are provided
        if title is not None:
            task.title = title
        if description is not None:
            task.description = description

        await session.commit()
        await session.refresh(task)

        return {
            "task_id": task.id,
            "status": "updated",
            "title": task.title
        }


async def complete_task(user_id: str, task_id: int) -> Dict[str, Any]:
    """
    MCP tool to complete a task
    """
    async with AsyncSessionLocal() as session:
        # Get the task
        result = await session.execute(select(Task).where(Task.id == task_id).where(Task.user_id == user_id))
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        # Update status to completed
        task.status = "completed"
        await session.commit()
        await session.refresh(task)

        return {
            "task_id": task.id,
            "status": "completed",
            "title": task.title
        }


async def delete_task(user_id: str, task_id: int) -> Dict[str, Any]:
    """
    MCP tool to delete a task
    """
    async with AsyncSessionLocal() as session:
        # Get the task
        result = await session.execute(select(Task).where(Task.id == task_id).where(Task.user_id == user_id))
        task = result.scalar_one_or_none()

        if not task:
            raise ValueError(f"Task with id {task_id} not found for user {user_id}")

        # Delete the task
        await session.delete(task)
        await session.commit()

        return {
            "task_id": task.id,
            "status": "deleted",
            "title": task.title
        }