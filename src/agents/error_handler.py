from typing import Any, Dict
import traceback
import logging


def handle_error(error: Exception) -> str:
    """
    Handle errors and return user-friendly error messages
    """
    # Log the error for debugging purposes
    logging.error(f"Error occurred: {str(error)}")
    logging.error(traceback.format_exc())

    # Map specific error types to user-friendly messages
    error_type = type(error).__name__

    if error_type == "ValueError":
        # These are typically validation errors or business logic errors
        return f"An error occurred: {str(error)}"
    elif error_type == "ConnectionError":
        return "Unable to connect to the required service. Please try again later."
    elif error_type == "TimeoutError":
        return "The request took too long to process. Please try again."
    elif error_type == "AuthenticationError":
        return "Authentication failed. Please check your credentials."
    elif error_type == "PermissionError":
        return "You don't have permission to perform this action."
    elif error_type == "NotFoundError":
        return "The requested item was not found."
    elif error_type == "IntegrityError":
        return "The request could not be completed due to a data integrity issue."
    else:
        # For unexpected errors, return a generic message
        return "An unexpected error occurred. Our team has been notified and is looking into it."


def log_error(error: Exception, context: str = "") -> None:
    """
    Log errors with additional context
    """
    logging.error(f"Error in {context}: {str(error)}")
    logging.error(f"Traceback: {traceback.format_exc()}")


def format_error_response(error: Exception, include_details: bool = False) -> Dict[str, Any]:
    """
    Format error response for API
    """
    response = {
        "error": handle_error(error),
        "success": False
    }

    if include_details:
        response["error_details"] = {
            "type": type(error).__name__,
            "message": str(error),
            "traceback": traceback.format_exc()
        }

    return response