"""
Task Executor — Phase V.
Routes intent results to direct DB operations via MCP tools,
supporting all Phase V fields: priority, tags, dueDate, reminderAt,
recurringInterval, search/filter, sort.
"""
import json
import logging
from typing import Dict, Any, List, Optional

from ..mcp.mcp_tools import add_task, list_tasks, update_task, complete_task, delete_task
from .error_handler import handle_error

logger = logging.getLogger(__name__)


async def execute_task(intent_result: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    """Execute the appropriate task action based on the analyzed intent."""
    intent = intent_result.get("intent", "")
    params = intent_result.get("parameters", {})
    params["user_id"] = user_id

    # Validation: check reminder_at before any API call
    reminder_validation_error = None
    if params.get("reminderAt"):
        from ..utils.validation import validate_reminder_at
        err = validate_reminder_at(params["reminderAt"])
        if err:
            reminder_validation_error = err

    try:
        operation = {}

        if intent == "add_task":
            if reminder_validation_error:
                return {
                    "result": {"error": reminder_validation_error},
                    "operations": [],
                    "status": "validation_error",
                    "validation_error": reminder_validation_error,
                }
            result = await add_task(
                user_id=user_id,
                title=params.get("title", "Untitled task"),
                description=params.get("description"),
                priority=params.get("priority", "medium"),
                tags=params.get("tags", []),
                due_date=params.get("dueDate"),
                recurring_interval=params.get("recurringInterval"),
                reminder_at=params.get("reminderAt"),
            )
            operation = {
                "operation": "create",
                "task_id": result.get("task_id"),
                "status": "success",
                "title": result.get("title", ""),
                "priority": params.get("priority", "medium"),
                "tags": params.get("tags", []),
                "recurringInterval": params.get("recurringInterval"),
                "dueDate": params.get("dueDate"),
                "reminderAt": params.get("reminderAt"),
            }

        elif intent in ("list_tasks", "search_tasks"):
            status_filter = params.get("filter_status", "all")
            search_query = params.get("search_query")
            result = await list_tasks(
                user_id=user_id,
                status=status_filter,
                search_query=search_query,
            )
            tasks_data = result.get("tasks", [])
            operation = {
                "operation": "list",
                "status": "success",
                "count": len(tasks_data),
                "tasks": tasks_data,
                "filter": status_filter,
                "search_query": search_query,
            }

        elif intent == "update_task":
            if reminder_validation_error:
                return {
                    "result": {"error": reminder_validation_error},
                    "operations": [],
                    "status": "validation_error",
                    "validation_error": reminder_validation_error,
                }
            task_id = params.get("task_id")
            if not task_id:
                raise ValueError("No task ID specified for update")
            result = await update_task(
                user_id=user_id,
                task_id=task_id,
                title=params.get("title"),
                description=params.get("description"),
                priority=params.get("priority"),
                tags=params.get("tags"),
                due_date=params.get("dueDate"),
                recurring_interval=params.get("recurringInterval"),
                reminder_at=params.get("reminderAt"),
            )
            operation = {
                "operation": "update",
                "task_id": task_id,
                "status": "success",
                "title": result.get("title", ""),
            }

        elif intent == "complete_task":
            task_id = params.get("task_id")
            if not task_id:
                raise ValueError("No task ID specified for completion")
            result = await complete_task(user_id=user_id, task_id=task_id)
            operation = {
                "operation": "complete",
                "task_id": task_id,
                "status": "success",
            }

        elif intent == "delete_task":
            task_id = params.get("task_id")
            if not task_id:
                raise ValueError("No task ID specified for deletion")
            result = await delete_task(user_id=user_id, task_id=task_id)
            operation = {
                "operation": "delete",
                "task_id": task_id,
                "status": "success",
            }

        elif intent in ("greeting", "help_request", "identity"):
            result = {"message": f"Intent '{intent}' processed", "status": "success"}
            operation = {"operation": "other", "status": "success", "intent": intent}

        else:
            result = {"message": f"Intent '{intent}' processed", "status": "success"}
            operation = {"operation": "other", "status": "success", "intent": intent}

        return {
            "result": result,
            "operations": [operation] if operation else [],
            "status": "success",
        }

    except Exception as e:
        logger.error("task_executor error (intent=%s): %s", intent, e)
        error_result = handle_error(e)
        return {
            "result": {"error": error_result},
            "operations": [],
            "status": "error",
            "error": str(e),
        }
