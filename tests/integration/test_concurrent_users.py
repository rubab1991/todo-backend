import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.models.task import Task
from src.mcp.mcp_tools import add_task, list_tasks, update_task, complete_task, delete_task


@pytest.mark.asyncio
async def test_concurrent_user_isolation_add_task():
    """Test that concurrent users have isolated task spaces when adding tasks"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    # Mock session for both users
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Set up add method mock
            mock_session_instance.add = MagicMock()
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', 1))

            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # Run add tasks concurrently
        task1 = add_task(user_id=user1, title="User 1 task", description="Description for user 1")
        task2 = add_task(user_id=user2, title="User 2 task", description="Description for user 2")

        results = await asyncio.gather(task1, task2)

        # Both tasks should be created successfully
        assert results[0]["status"] == "created"
        assert results[1]["status"] == "created"


@pytest.mark.asyncio
async def test_concurrent_user_isolation_list_tasks():
    """Test that concurrent users can only see their own tasks"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Create mock tasks for different users
            mock_task1 = MagicMock()
            mock_task1.id = 1
            mock_task1.title = "User 1 task"
            mock_task1.status = "pending"
            mock_task1.description = "Description for user 1"
            mock_task1.created_at = "2023-01-01T00:00:00"

            mock_task2 = MagicMock()
            mock_task2.id = 2
            mock_task2.title = "User 2 task"
            mock_task2.status = "pending"
            mock_task2.description = "Description for user 2"
            mock_task2.created_at = "2023-01-01T00:00:00"

            # Mock the result based on the user_id in the query
            async def mock_execute(stmt):
                # This simulates filtering by user_id
                mock_result = AsyncMock()

                # Extract the user_id from the statement (simplified for test)
                # In real scenario, the SQLModel query would filter appropriately
                if "user_1_uuid" in str(stmt):
                    mock_result.scalars().all.return_value = [mock_task1]
                elif "user_2_uuid" in str(stmt):
                    mock_result.scalars().all.return_value = [mock_task2]
                else:
                    # Default to empty for this test
                    mock_result.scalars().all.return_value = []

                return mock_result

            mock_session_instance.execute.side_effect = mock_execute
            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # Run list tasks concurrently
        tasks1 = list_tasks(user_id=user1, status="all")
        tasks2 = list_tasks(user_id=user2, status="all")

        results = await asyncio.gather(tasks1, tasks2)

        # Each user should only see their own tasks
        assert results[0]["count"] == 1
        assert results[0]["tasks"][0]["title"] == "User 1 task"
        assert results[1]["count"] == 1
        assert results[1]["tasks"][0]["title"] == "User 2 task"


@pytest.mark.asyncio
async def test_concurrent_updates_different_tasks():
    """Test concurrent updates to different tasks"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Mock different tasks for different users
            mock_task1 = MagicMock()
            mock_task1.id = 1
            mock_task1.title = "Original User 1 task"
            mock_task1.user_id = user1

            mock_task2 = MagicMock()
            mock_task2.id = 2
            mock_task2.title = "Original User 2 task"
            mock_task2.user_id = user2

            async def mock_execute(stmt):
                mock_result = AsyncMock()

                # Return the appropriate task based on the query
                if "user_1_uuid" in str(stmt) and "1" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task1
                elif "user_2_uuid" in str(stmt) and "2" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task2
                else:
                    mock_result.scalar_one_or_none.return_value = None

                return mock_result

            mock_session_instance.execute.side_effect = mock_execute
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()

            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # Run updates concurrently
        update1 = update_task(user_id=user1, task_id=1, title="Updated User 1 task")
        update2 = update_task(user_id=user2, task_id=2, title="Updated User 2 task")

        results = await asyncio.gather(update1, update2)

        # Both updates should succeed
        assert results[0]["status"] == "updated"
        assert results[0]["title"] == "Updated User 1 task"
        assert results[1]["status"] == "updated"
        assert results[1]["title"] == "Updated User 2 task"


@pytest.mark.asyncio
async def test_concurrent_completes_different_tasks():
    """Test concurrent completion of different tasks"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Mock tasks for both users
            mock_task1 = MagicMock()
            mock_task1.id = 1
            mock_task1.title = "User 1 task"
            mock_task1.status = "pending"
            mock_task1.user_id = user1

            mock_task2 = MagicMock()
            mock_task2.id = 2
            mock_task2.title = "User 2 task"
            mock_task2.status = "pending"
            mock_task2.user_id = user2

            async def mock_execute(stmt):
                mock_result = AsyncMock()

                # Return appropriate task based on query
                if "user_1_uuid" in str(stmt) and "1" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task1
                elif "user_2_uuid" in str(stmt) and "2" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task2
                else:
                    mock_result.scalar_one_or_none.return_value = None

                return mock_result

            mock_session_instance.execute.side_effect = mock_execute
            mock_session_instance.commit = AsyncMock()
            mock_session_instance.refresh = AsyncMock()

            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # Run completions concurrently
        complete1 = complete_task(user_id=user1, task_id=1)
        complete2 = complete_task(user_id=user2, task_id=2)

        results = await asyncio.gather(complete1, complete2)

        # Both completions should succeed
        assert results[0]["status"] == "completed"
        assert results[0]["title"] == "User 1 task"
        assert results[1]["status"] == "completed"
        assert results[1]["title"] == "User 2 task"


@pytest.mark.asyncio
async def test_concurrent_deletes_different_tasks():
    """Test concurrent deletion of different tasks"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Mock tasks for both users
            mock_task1 = MagicMock()
            mock_task1.id = 1
            mock_task1.title = "User 1 task"
            mock_task1.user_id = user1

            mock_task2 = MagicMock()
            mock_task2.id = 2
            mock_task2.title = "User 2 task"
            mock_task2.user_id = user2

            async def mock_execute(stmt):
                mock_result = AsyncMock()

                # Return appropriate task based on query
                if "user_1_uuid" in str(stmt) and "1" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task1
                elif "user_2_uuid" in str(stmt) and "2" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = mock_task2
                else:
                    mock_result.scalar_one_or_none.return_value = None

                return mock_result

            mock_session_instance.execute.side_effect = mock_execute
            mock_session_instance.delete = MagicMock()
            mock_session_instance.commit = AsyncMock()

            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # Run deletions concurrently
        delete1 = delete_task(user_id=user1, task_id=1)
        delete2 = delete_task(user_id=user2, task_id=2)

        results = await asyncio.gather(delete1, delete2)

        # Both deletions should succeed
        assert results[0]["status"] == "deleted"
        assert results[0]["title"] == "User 1 task"
        assert results[1]["status"] == "deleted"
        assert results[1]["title"] == "User 2 task"


@pytest.mark.asyncio
async def test_user_data_isolation():
    """Test that users cannot access each other's data"""
    user1 = "user_1_uuid"
    user2 = "user_2_uuid"

    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        async def mock_session_context():
            mock_session_instance = AsyncMock()

            # Mock task for user1 only
            mock_task1 = MagicMock()
            mock_task1.id = 1
            mock_task1.title = "User 1 task"
            mock_task1.user_id = user1

            async def mock_execute(stmt):
                mock_result = AsyncMock()

                # User 1 should find their task, User 2 should not
                if "user_1_uuid" in str(stmt):
                    mock_result.scalars().all.return_value = [mock_task1]
                    mock_result.scalar_one_or_none.return_value = mock_task1
                else:
                    # For user2 or mismatched queries, return None/empty
                    mock_result.scalars().all.return_value = []
                    mock_result.scalar_one_or_none.return_value = None

                return mock_result

            mock_session_instance.execute.side_effect = mock_execute
            return mock_session_instance

        mock_session.return_value.__aenter__.side_effect = mock_session_context

        # User 1 should be able to list their tasks
        user1_tasks = await list_tasks(user_id=user1, status="all")
        assert user1_tasks["count"] == 1

        # User 2 should see no tasks
        user2_tasks = await list_tasks(user_id=user2, status="all")
        assert user2_tasks["count"] == 0

        # User 2 should not be able to access user 1's specific task
        with pytest.raises(ValueError, match="Task with id 1 not found for user"):
            await update_task(user_id=user2, task_id=1, title="Unauthorized update")


@pytest.mark.asyncio
async def test_concurrent_high_volume():
    """Test system behavior under high concurrent load"""
    num_users = 10
    tasks_per_user = 5

    # Create mock users and tasks
    users = [f"user_{i}_uuid" for i in range(num_users)]

    async def create_tasks_for_user(user_id, num_tasks):
        tasks = []
        for i in range(num_tasks):
            task = add_task(
                user_id=user_id,
                title=f"Task {i} for {user_id}",
                description=f"Description for task {i} of {user_id}"
            )
            tasks.append(task)
        return await asyncio.gather(*tasks)

    # Create tasks concurrently for all users
    all_create_tasks = [
        create_tasks_for_user(user, tasks_per_user)
        for user in users
    ]

    # Execute all concurrently
    results = await asyncio.gather(*all_create_tasks)

    # Verify all tasks were created
    for user_results in results:
        assert len(user_results) == tasks_per_user
        for result in user_results:
            assert result["status"] == "created"