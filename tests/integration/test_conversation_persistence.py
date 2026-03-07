import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.agents.conversation_persistence import get_conversation_history, save_conversation


@pytest.mark.asyncio
async def test_get_conversation_history_new_conversation():
    """Test getting conversation history for a new conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock the result for conversation query
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = []

        mock_session_instance.execute.return_value = mock_result

        # Mock the message query result
        mock_msg_result = AsyncMock()
        mock_msg_result.scalars().all.return_value = []
        mock_session_instance.execute.return_value = mock_msg_result

        history = await get_conversation_history(user_id="test_user")

        # Should return an empty history
        assert history == []


@pytest.mark.asyncio
async def test_get_conversation_history_existing_conversation():
    """Test getting conversation history for an existing conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock a message
        mock_message = MagicMock()
        mock_message.role = "assistant"
        mock_message.content = "Hello! How can I help you?"
        mock_message.timestamp = MagicMock()
        mock_message.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        # Mock the result
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_message]

        mock_session_instance.execute.return_value = mock_result

        history = await get_conversation_history(user_id="test_user", conversation_id="test_conv")

        # Should return history with the message
        assert len(history) == 1
        assert history[0]["role"] == "assistant"
        assert history[0]["content"] == "Hello! How can I help you?"
        assert history[0]["timestamp"] == "2023-01-01T00:00:00"


@pytest.mark.asyncio
async def test_save_conversation_new_conversation():
    """Test saving conversation for a new conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock conversation and message creation
        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock()

        conversation_id = await save_conversation(
            user_id="test_user",
            conversation_id=None,
            user_message="Hello bot",
            assistant_response="Hello user!",
            tool_calls=[]
        )

        # Should create a new conversation and return its ID
        assert conversation_id is not None
        assert len(conversation_id) > 0  # UUID should be generated


@pytest.mark.asyncio
async def test_save_conversation_existing_conversation():
    """Test saving conversation for an existing conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock conversation and message creation
        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock()

        conversation_id = await save_conversation(
            user_id="test_user",
            conversation_id="existing_conv_id",
            user_message="Follow up message",
            assistant_response="Got it!",
            tool_calls=[{"tool_name": "add_task", "parameters": {"title": "test"}}]
        )

        # Should return the same conversation ID
        assert conversation_id == "existing_conv_id"


@pytest.mark.asyncio
async def test_save_conversation_with_tool_calls():
    """Test saving conversation with tool calls"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock conversation and message creation
        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock()

        tool_calls = [
            {"tool_name": "add_task", "parameters": {"title": "Buy groceries"}},
            {"tool_name": "list_tasks", "parameters": {"status": "pending"}}
        ]

        conversation_id = await save_conversation(
            user_id="test_user",
            conversation_id="test_conv",
            user_message="Add task and show my tasks",
            assistant_response="Task added and tasks shown",
            tool_calls=tool_calls
        )

        # Should return the conversation ID
        assert conversation_id == "test_conv"


@pytest.mark.asyncio
async def test_get_conversation_history_ordering():
    """Test that conversation history is ordered chronologically"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock multiple messages in chronological order
        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "First message"
        mock_msg1.timestamp = MagicMock()
        mock_msg1.timestamp.isoformat.return_value = "2023-01-01T00:00:00"

        mock_msg2 = MagicMock()
        mock_msg2.role = "assistant"
        mock_msg2.content = "First response"
        mock_msg2.timestamp = MagicMock()
        mock_msg2.timestamp.isoformat.return_value = "2023-01-01T00:00:01"

        mock_msg3 = MagicMock()
        mock_msg3.role = "user"
        mock_msg3.content = "Second message"
        mock_msg3.timestamp = MagicMock()
        mock_msg3.timestamp.isoformat.return_value = "2023-01-01T00:00:02"

        # Mock the result with messages in order
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = [mock_msg1, mock_msg2, mock_msg3]

        mock_session_instance.execute.return_value = mock_result

        history = await get_conversation_history(user_id="test_user", conversation_id="test_conv")

        # Should return history in chronological order
        assert len(history) == 3
        assert history[0]["content"] == "First message"
        assert history[1]["content"] == "First response"
        assert history[2]["content"] == "Second message"


@pytest.mark.asyncio
async def test_save_conversation_multiple_messages():
    """Test saving multiple messages to the same conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock conversation and message creation
        mock_session_instance.add = MagicMock()
        mock_session_instance.commit = AsyncMock()

        # Save first message
        conv_id1 = await save_conversation(
            user_id="test_user",
            conversation_id=None,
            user_message="Hello",
            assistant_response="Hi there!",
            tool_calls=[]
        )

        # Save follow-up message
        conv_id2 = await save_conversation(
            user_id="test_user",
            conversation_id=conv_id1,
            user_message="How are you?",
            assistant_response="I'm doing well!",
            tool_calls=[]
        )

        # Both should return the same conversation ID
        assert conv_id1 == conv_id2


@pytest.mark.asyncio
async def test_get_conversation_history_empty():
    """Test getting conversation history when no messages exist"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock empty result
        mock_result = AsyncMock()
        mock_result.scalars().all.return_value = []

        mock_session_instance.execute.return_value = mock_result

        history = await get_conversation_history(user_id="test_user", conversation_id="nonexistent_conv")

        # Should return empty history
        assert history == []


@pytest.mark.asyncio
async def test_save_conversation_error_handling():
    """Test error handling in save_conversation"""
    with patch('src.agents.conversation_persistence.AsyncSessionLocal') as mock_session:
        mock_session_instance = AsyncMock()
        mock_session.return_value.__aenter__.return_value = mock_session_instance

        # Mock an exception during commit
        mock_session_instance.commit.side_effect = Exception("Database error")

        with pytest.raises(Exception):
            await save_conversation(
                user_id="test_user",
                conversation_id="test_conv",
                user_message="Test message",
                assistant_response="Test response",
                tool_calls=[]
            )