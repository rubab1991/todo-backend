from sqlmodel import select, func
from sqlalchemy import text
from ..models.task import Task
from ..models.conversation import Conversation
from ..models.message import Message
from ..models.user import User
from ..db.session import AsyncSessionLocal
from typing import Dict, List, Tuple
import time
import asyncio


class DatabaseOptimizer:
    """
    Service for optimizing database queries and performance
    """
    def __init__(self):
        self.query_performance_stats = {}

    async def optimize_user_tasks_query(self, user_id: str, status: str = "all") -> List[Task]:
        """
        Optimized query to get user tasks with proper indexing and joins
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            statement = select(Task).where(Task.user_id == user_id)

            if status != "all":
                statement = statement.where(Task.status == status)

            # Order by creation date descending for most recent first
            statement = statement.order_by(Task.created_at.desc())

            result = await session.exec(statement)
            tasks = result.all()

            query_time = time.time() - start_time

            # Log performance for monitoring
            await self._log_query_performance("get_user_tasks", query_time, len(tasks))

            return tasks

    async def optimize_conversation_history_query(self, conversation_id: str, limit: int = 50) -> List[Message]:
        """
        Optimized query to get conversation history with proper limits
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            # Get most recent messages first
            statement = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.desc())
                .limit(limit)
            )

            result = await session.exec(statement)
            messages = result.all()

            query_time = time.time() - start_time

            # Log performance
            await self._log_query_performance("get_conversation_history", query_time, len(messages))

            return messages

    async def get_user_statistics(self, user_id: str) -> Dict[str, int]:
        """
        Optimized query to get user statistics without multiple round trips
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            # Get task statistics in a single query
            pending_count_statement = select(func.count(Task.id)).where(
                (Task.user_id == user_id) & (Task.status == "pending")
            )
            completed_count_statement = select(func.count(Task.id)).where(
                (Task.user_id == user_id) & (Task.status == "completed")
            )
            total_tasks_statement = select(func.count(Task.id)).where(Task.user_id == user_id)

            pending_result = await session.exec(pending_count_statement)
            completed_result = await session.exec(completed_count_statement)
            total_result = await session.exec(total_tasks_statement)

            stats = {
                "pending_tasks": pending_result.one(),
                "completed_tasks": completed_result.one(),
                "total_tasks": total_result.one()
            }

            query_time = time.time() - start_time

            # Log performance
            await self._log_query_performance("get_user_statistics", query_time, 3)

            return stats

    async def batch_create_tasks(self, user_id: str, tasks_data: List[Dict]) -> List[Task]:
        """
        Optimized batch creation of tasks
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            created_tasks = []
            for task_data in tasks_data:
                task = Task(
                    title=task_data["title"],
                    description=task_data.get("description"),
                    status=task_data.get("status", "pending"),
                    user_id=user_id
                )
                session.add(task)
                created_tasks.append(task)

            await session.commit()

            # Refresh to get IDs
            for task in created_tasks:
                await session.refresh(task)

            query_time = time.time() - start_time

            # Log performance
            await self._log_query_performance("batch_create_tasks", query_time, len(created_tasks))

            return created_tasks

    async def bulk_update_tasks(self, user_id: str, updates: List[Dict]) -> int:
        """
        Optimized bulk update of tasks
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            updated_count = 0
            for update_data in updates:
                task_id = update_data["task_id"]

                # Get the task
                statement = select(Task).where(
                    (Task.id == task_id) & (Task.user_id == user_id)
                )
                result = await session.exec(statement)
                task = result.first()

                if task:
                    # Update fields
                    if "title" in update_data:
                        task.title = update_data["title"]
                    if "description" in update_data:
                        task.description = update_data["description"]
                    if "status" in update_data:
                        task.status = update_data["status"]

                    updated_count += 1

            await session.commit()

            query_time = time.time() - start_time

            # Log performance
            await self._log_query_performance("bulk_update_tasks", query_time, updated_count)

            return updated_count

    async def get_tasks_with_pagination(self, user_id: str, page: int = 1, page_size: int = 10,
                                      status: str = "all") -> Tuple[List[Task], int]:
        """
        Optimized paginated query for tasks
        """
        async with AsyncSessionLocal() as session:
            start_time = time.time()

            # Calculate offset
            offset = (page - 1) * page_size

            # Build query
            statement = select(Task).where(Task.user_id == user_id)

            if status != "all":
                statement = statement.where(Task.status == status)

            # Count total for pagination
            count_statement = select(func.count(Task.id)).where(Task.user_id == user_id)
            if status != "all":
                count_statement = count_statement.where(Task.status == status)

            count_result = await session.exec(count_statement)
            total_count = count_result.one()

            # Apply ordering and pagination
            statement = statement.order_by(Task.created_at.desc()).offset(offset).limit(page_size)

            result = await session.exec(statement)
            tasks = result.all()

            query_time = time.time() - start_time

            # Log performance
            await self._log_query_performance("get_tasks_with_pagination", query_time, len(tasks))

            return tasks, total_count

    async def _log_query_performance(self, query_name: str, execution_time: float, result_count: int):
        """
        Log query performance metrics
        """
        if query_name not in self.query_performance_stats:
            self.query_performance_stats[query_name] = []

        self.query_performance_stats[query_name].append({
            "execution_time": execution_time,
            "result_count": result_count,
            "timestamp": time.time()
        })

        # Keep only last 100 measurements per query
        if len(self.query_performance_stats[query_name]) > 100:
            self.query_performance_stats[query_name] = self.query_performance_stats[query_name][-100:]

    def get_slow_queries(self, threshold: float = 0.1) -> Dict[str, List[Dict]]:
        """
        Get queries that are slower than the threshold
        """
        slow_queries = {}

        for query_name, measurements in self.query_performance_stats.items():
            slow_measurements = [m for m in measurements if m["execution_time"] > threshold]
            if slow_measurements:
                slow_queries[query_name] = slow_measurements

        return slow_queries

    async def analyze_performance(self) -> Dict[str, Dict[str, float]]:
        """
        Analyze overall performance of queries
        """
        analysis = {}

        for query_name, measurements in self.query_performance_stats.items():
            if measurements:
                execution_times = [m["execution_time"] for m in measurements]
                avg_time = sum(execution_times) / len(execution_times)
                min_time = min(execution_times)
                max_time = max(execution_times)

                analysis[query_name] = {
                    "avg_execution_time": avg_time,
                    "min_execution_time": min_time,
                    "max_execution_time": max_time,
                    "call_count": len(measurements),
                    "total_time": sum(execution_times)
                }

        return analysis

    async def suggest_indexes(self) -> List[str]:
        """
        Suggest indexes based on query patterns
        """
        suggestions = []

        # Index on user_id for all tables since it's used in almost every query
        suggestions.append("CREATE INDEX idx_task_user_id ON tasks(user_id)")
        suggestions.append("CREATE INDEX idx_conversation_user_id ON conversations(user_id)")
        suggestions.append("CREATE INDEX idx_message_user_id ON messages(user_id)")

        # Index on status for filtering
        suggestions.append("CREATE INDEX idx_task_status ON tasks(status)")

        # Index on timestamps for ordering
        suggestions.append("CREATE INDEX idx_task_created_at ON tasks(created_at)")
        suggestions.append("CREATE INDEX idx_message_timestamp ON messages(timestamp)")

        # Composite indexes for common filters
        suggestions.append("CREATE INDEX idx_task_user_id_status ON tasks(user_id, status)")

        return suggestions


# Global optimizer instance
db_optimizer = DatabaseOptimizer()