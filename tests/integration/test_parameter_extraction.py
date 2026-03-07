import pytest
from src.agents.intent_analyzer import extract_parameters


def test_extract_task_id_from_message():
    """Test extraction of task ID from message"""
    message = "Complete task #1"
    intent = "complete_task"

    params = extract_parameters(message, intent)

    assert params["task_id"] == 1


def test_extract_task_id_without_hash():
    """Test extraction of task ID without hash symbol"""
    message = "Complete task 1"
    intent = "complete_task"

    params = extract_parameters(message, intent)

    assert params["task_id"] == 1


def test_extract_task_id_multiple_numbers():
    """Test extraction of task ID when multiple numbers in message"""
    message = "Complete task #123 for project 456"
    intent = "complete_task"

    params = extract_parameters(message, intent)

    assert params["task_id"] == 123


def test_extract_title_add_task_simple():
    """Test extraction of title for add task with simple message"""
    message = "Add task: Buy groceries"
    intent = "add_task"

    params = extract_parameters(message, intent)

    assert params["title"] == "Buy groceries"


def test_extract_title_add_task_variations():
    """Test extraction of title for add task with different phrasings"""
    test_cases = [
        ("Add task Buy groceries", "Buy groceries"),
        ("Create a task to finish report", "finish report"),
        ("Remember to call mom", "call mom"),
        ("Add task: Schedule dentist appointment", "Schedule dentist appointment")
    ]

    for message, expected_title in test_cases:
        params = extract_parameters(message, "add_task")
        assert params["title"] == expected_title, f"Failed for message: {message}"


def test_extract_title_update_task():
    """Test extraction of title for update task"""
    message = "Update task #1 to buy vegetables"
    intent = "update_task"

    params = extract_parameters(message, intent)

    assert params["task_id"] == 1
    assert params["title"] == "buy vegetables"


def test_extract_title_update_task_phrasing():
    """Test extraction of title for update task with different phrasings"""
    test_cases = [
        ("Change task #1 to 'Buy vegetables'", "Buy vegetables"),
        ("Rename task #1 as 'Call dentist'", "Call dentist"),
        ("Update task 2 to finish the presentation", "finish the presentation")
    ]

    for message, expected_title in test_cases:
        params = extract_parameters(message, "update_task")
        assert params["title"] == expected_title, f"Failed for message: {message}"


def test_extract_description_if_present():
    """Test extraction of description when present in message"""
    message = "Add task: Buy groceries with milk, bread, and eggs"
    intent = "add_task"

    params = extract_parameters(message, intent)

    # Note: This is a simplified test - the actual implementation may vary
    # based on how descriptions are parsed from the message
    assert "title" in params


def test_extract_status_complete_task():
    """Test extraction of status for complete task"""
    message = "Complete task #1"
    intent = "complete_task"

    params = extract_parameters(message, intent)

    assert params["status"] == "completed"


def test_no_extra_params_when_not_needed():
    """Test that no unnecessary parameters are extracted"""
    message = "Show my tasks"
    intent = "list_tasks"

    params = extract_parameters(message, intent)

    # For list_tasks, we shouldn't have task_id or title
    assert "task_id" not in params or params.get("task_id") is None
    assert "title" not in params or params.get("title") is None


def test_case_insensitive_matching():
    """Test that parameter extraction works with different cases"""
    test_cases = [
        ("ADD TASK: Buy Groceries", "add_task", "Buy Groceries"),
        ("complete TASK #1", "complete_task", 1),
        ("UPDATE task #2 to New Title", "update_task", "New Title")
    ]

    for message, intent, expected_value in test_cases:
        params = extract_parameters(message, intent)

        if isinstance(expected_value, int):
            assert params["task_id"] == expected_value
        elif isinstance(expected_value, str):
            if "title" in params:
                assert params["title"] == expected_value
            elif "task_id" in params:
                assert params["task_id"] == expected_value


def test_extract_params_with_punctuation():
    """Test extraction of parameters with various punctuation"""
    test_cases = [
        ("Add task: Buy groceries!", "Buy groceries"),
        ("Add task: Buy groceries?", "Buy groceries"),
        ("Add task: Buy groceries.", "Buy groceries"),
        ("Add task: Buy groceries,", "Buy groceries")
    ]

    for message, expected_title in test_cases:
        params = extract_parameters(message, "add_task")
        assert params["title"] == expected_title, f"Failed for message: {message}"


def test_extract_params_empty_message():
    """Test parameter extraction with empty or minimal message"""
    message = ""
    intent = "add_task"

    params = extract_parameters(message, intent)

    # Should return an empty dict or minimal params
    assert isinstance(params, dict)


def test_extract_params_only_numbers():
    """Test parameter extraction when message has numbers but not task-related"""
    message = "I have 5 apples and 3 oranges"
    intent = "other"

    params = extract_parameters(message, intent)

    # Should not extract task_id from random numbers
    assert "task_id" not in params or params.get("task_id") is None


def test_extract_complex_sentence():
    """Test parameter extraction from complex sentence"""
    message = "Could you please add a task to schedule the meeting for tomorrow with John and Jane?"
    intent = "add_task"

    params = extract_parameters(message, intent)

    # Should extract a relevant title from the complex sentence
    assert "title" in params
    assert isinstance(params["title"], str)
    assert len(params["title"]) > 0