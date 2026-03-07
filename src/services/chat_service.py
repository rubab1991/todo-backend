import asyncio
from typing import Dict, Any, Optional
from uuid import UUID
from ..models.message import MessageCreate
from ..agents.main_agent import process_with_agents


async def process_user_message(
    user_id: str,
    message: str,
    conversation_id: Optional[str] = None,
    user_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Process a user message through the AI agents and return a response
    """
    try:
        # Call the main agent processing function
        result = await process_with_agents(user_id, message, conversation_id, user_info)

        return result
    except Exception as e:
        # Log the error appropriately in a real implementation
        print(f"Error processing user message: {e}")
        return {
            "response": "Sorry, I encountered an error processing your request.",
            "error": str(e)
        }


async def save_message_to_db(
    db,
    message_data: MessageCreate
) -> None:
    """
    Save a message to the database
    """
    # Implementation will be added in later tasks
    pass