import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.agents.intent_analyzer import analyze_intent


def test_analyze_intent_add_task():
    """Test intent detection for adding tasks"""
    message = "Add task: Buy groceries"
    conversation_history = []

    # Since we're mocking the Cohere API call, we'll simulate the response
    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        # Mock the classify method response
        mock_classification = MagicMock()
        mock_classification.predictions = ['add_task']

        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='add_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "add_task"
        assert result["parameters"]["title"] == "Buy groceries"


def test_analyze_intent_list_tasks():
    """Test intent detection for listing tasks"""
    message = "Show my tasks"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='list_tasks')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "list_tasks"


def test_analyze_intent_complete_task():
    """Test intent detection for completing tasks"""
    message = "Complete task #1"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='complete_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "complete_task"
        assert result["parameters"]["task_id"] == 1


def test_analyze_intent_update_task():
    """Test intent detection for updating tasks"""
    message = "Update task #1 to 'Buy vegetables'"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='update_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "update_task"
        assert result["parameters"]["task_id"] == 1
        assert result["parameters"]["title"] == "Buy vegetables"


def test_analyze_intent_delete_task():
    """Test intent detection for deleting tasks"""
    message = "Delete task #2"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='delete_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "delete_task"
        assert result["parameters"]["task_id"] == 2


def test_analyze_intent_greeting():
    """Test intent detection for greetings"""
    message = "Hello there"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='greeting')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "greeting"


def test_analyze_intent_help_request():
    """Test intent detection for help requests"""
    message = "Help me"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='help_request')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "help_request"


def test_extract_parameters_from_message():
    """Test parameter extraction from message"""
    message = "Update task #1 to 'Buy organic vegetables and fruits'"

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='update_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, [])

        assert result["parameters"]["task_id"] == 1
        assert result["parameters"]["title"] == "Buy organic vegetables and fruits"


def test_extract_parameters_without_task_id():
    """Test parameter extraction when no task ID is mentioned"""
    message = "Add task: Call the plumber"

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='add_task')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, [])

        assert result["parameters"]["title"] == "Call the plumber"
        # task_id should not be in parameters if not mentioned
        assert "task_id" not in result["parameters"]


def test_analyze_intent_other():
    """Test intent detection for other/unrecognized intents"""
    message = "What's the weather like?"
    conversation_history = []

    with patch('src.agents.intent_analyzer.cohere.Client') as mock_cohere:
        mock_response = MagicMock()
        mock_response.classifications = [MagicMock(prediction='other')]

        mock_cohere.return_value = MagicMock()
        mock_cohere.return_value.classify.return_value = mock_response

        result = analyze_intent(message, conversation_history)

        assert result["intent"] == "other"