import os
from typing import Dict, Any, Optional
from ..config import settings
from .intent_analyzer import analyze_intent
from .task_executor import execute_task
from .conversation_persistence import get_conversation_history, save_conversation
from .response_composer import compose_response
from .error_handler import handle_error


async def process_with_agents(
    user_id: str,
    message: str,
    conversation_id: Optional[str] = None,
    user_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main function to process user message through all AI agents
    """
    try:
        # Step 1: Get conversation history
        conversation_history = await get_conversation_history(user_id, conversation_id)

        # Step 2: Analyze intent from user message
        intent_result = analyze_intent(message, conversation_history)

        # Step 3: Execute appropriate task based on intent
        task_result = await execute_task(intent_result, user_id)

        # Step 4: Compose response based on task result
        response = compose_response(task_result, intent_result, user_info)

        # Step 5: Save the conversation to DB
        conversation_id = await save_conversation(
            user_id,
            conversation_id,
            message,
            response,
            intent_result.get('tool_calls', [])
        )

        return {
            "response": response,
            "conversation_id": conversation_id,
            "task_operations": task_result.get("operations", []),
            "tool_calls": intent_result.get("tool_calls", [])
        }

    except Exception as e:
        # Step 6: Handle any errors
        error_response = handle_error(e)
        return {
            "response": error_response,
            "error": str(e)
        }