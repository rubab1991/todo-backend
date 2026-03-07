import logging
import sys
from datetime import datetime
from typing import Any, Dict
from ..config import settings


def setup_logging():
    """
    Set up comprehensive logging for the application
    """
    # Create logger
    logger = logging.getLogger("todo_ai_chatbot")
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    # Prevent adding multiple handlers if function is called multiple times
    if logger.handlers:
        return logger

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, settings.log_level.upper()))

    # Create file handler (optional)
    if settings.debug:
        file_handler = logging.FileHandler("app.log")
        file_handler.setLevel(logging.DEBUG)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    console_handler.setFormatter(formatter)

    if settings.debug:
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Add handlers to logger
    logger.addHandler(console_handler)

    return logger


def log_user_action(user_id: str, action: str, details: Dict[str, Any] = None):
    """
    Log user actions for audit trail
    """
    logger = setup_logging()
    log_data = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
        "details": details or {}
    }
    logger.info(f"USER_ACTION: {log_data}")


def log_api_call(endpoint: str, method: str, user_id: str = None, response_time: float = None):
    """
    Log API calls for monitoring
    """
    logger = setup_logging()
    log_data = {
        "endpoint": endpoint,
        "method": method,
        "user_id": user_id,
        "response_time_ms": response_time,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"API_CALL: {log_data}")


def log_error(error: Exception, context: str = "", user_id: str = None):
    """
    Log errors with context
    """
    logger = setup_logging()
    log_data = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "context": context,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.error(f"ERROR: {log_data}")


def log_task_operation(user_id: str, operation: str, task_id: int = None, details: Dict[str, Any] = None):
    """
    Log task operations for audit trail
    """
    logger = setup_logging()
    log_data = {
        "user_id": user_id,
        "operation": operation,
        "task_id": task_id,
        "details": details or {},
        "timestamp": datetime.utcnow().isoformat()
    }
    logger.info(f"TASK_OPERATION: {log_data}")