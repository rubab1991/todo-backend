import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp.mcp_tools import add_task, list_tasks, update_task, complete_task, delete_task


@pytest.mark.asyncio
async def test_add_task_success():
    """Test successful task creation"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock the task object
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "Test task"

        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock()
        mock_session_instance.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, 'id', 1))

        result = await add_task(user_id="test_user", title="Test task", description="Test description")

        assert result["task_id"] == 1
        assert result["status"] == "created"
        assert result["title"] == "Test task"


@pytest.mark.asyncio
async def test_list_tasks_success():
    """Test successful retrieval of tasks"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock the result — execute returns an awaitable, result itself has sync methods
        mock_result = MagicMock()
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "Test task"
        mock_task.status = "pending"
        mock_task.description = "Test description"
        mock_task.created_at = "2023-01-01T00:00:00"
        mock_result.scalars.return_value.all.return_value = [mock_task]

        mock_session_instance.execute = AsyncMock(return_value=mock_result)

        result = await list_tasks(user_id="test_user", status="all")

        assert result["count"] == 1
        assert len(result["tasks"]) == 1
        assert result["tasks"][0]["id"] == 1
        assert result["tasks"][0]["title"] == "Test task"


@pytest.mark.asyncio
async def test_update_task_success():
    """Test successful task update"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock the result — sync result with sync scalar_one_or_none
        mock_scalar_result = MagicMock()
        mock_scalar_result.id = 1
        mock_scalar_result.title = "Updated task"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scalar_result

        mock_session_instance.execute = AsyncMock(return_value=mock_result)
        mock_session_instance.commit = AsyncMock()
        mock_session_instance.refresh = AsyncMock()

        result = await update_task(user_id="test_user", task_id=1, title="Updated task")

        assert result["task_id"] == 1
        assert result["status"] == "updated"
        assert result["title"] == "Updated task"


@pytest.mark.asyncio
async def test_complete_task_success():
    """Test successful task completion"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        mock_scalar_result = MagicMock()
        mock_scalar_result.id = 1
        mock_scalar_result.title = "Test task"
        mock_scalar_result.status = "pending"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scalar_result

        mock_session_instance.execute = AsyncMock(return_value=mock_result)
        mock_session_instance.commit = AsyncMock()
        mock_session_instance.refresh = AsyncMock()

        result = await complete_task(user_id="test_user", task_id=1)

        assert result["task_id"] == 1
        assert result["status"] == "completed"
        assert result["title"] == "Test task"


@pytest.mark.asyncio
async def test_delete_task_success():
    """Test successful task deletion"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        mock_scalar_result = MagicMock()
        mock_scalar_result.id = 1
        mock_scalar_result.title = "Test task"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_scalar_result

        mock_session_instance.execute = AsyncMock(return_value=mock_result)
        mock_session_instance.delete = AsyncMock()
        mock_session_instance.commit = AsyncMock()

        result = await delete_task(user_id="test_user", task_id=1)

        assert result["task_id"] == 1
        assert result["status"] == "deleted"
        assert result["title"] == "Test task"


@pytest.mark.asyncio
async def test_add_task_missing_title():
    """Test task creation with missing title raises error"""
    with pytest.raises(TypeError):
        await add_task(user_id="test_user")


@pytest.mark.asyncio
async def test_list_tasks_invalid_status():
    """Test list tasks with invalid status"""
    with patch('src.mcp.mcp_tools.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session_instance.execute = AsyncMock(return_value=mock_result)

        result = await list_tasks(user_id="test_user", status="invalid_status")

        assert result["count"] == 0
        assert len(result["tasks"]) == 0
