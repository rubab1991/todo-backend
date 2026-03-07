"""
Task Executor — Phase V.
Routes intent results to MCP tool calls, passing all Phase V fields:
priority, tags, dueDate, reminderAt, recurringInterval, search/filter, sort.
"""
import logging
import os
from typing import Dict, Any, List, Optional

import httpx

from ..mcp.mcp_tools import add_task, list_tasks, update_task, complete_task, delete_task
from .error_handler import handle_error

logger = logging.getLogger(__name__)

INTERNAL_API_BASE = os.getenv("INTERNAL_API_BASE", "http://localhost:8000")


async def _api_create_task(user_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a task via the HTTP API (supports all Phase V fields)."""
    url = f"{INTERNAL_API_BASE}/api/{user_id}/tasks"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _api_update_task(user_id: str, task_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Update a task via the HTTP API (supports all Phase V fields)."""
    url = f"{INTERNAL_API_BASE}/api/{user_id}/tasks/{task_id}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.put(url, json=payload)
        resp.raise_for_status()
        return resp.json()


async def _api_list_tasks(user_id: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """List/search/filter/sort tasks via the HTTP API."""
    url = f"{INTERNAL_API_BASE}/api/{user_id}/tasks"
    query = {}
    if params.get("search_query"):
        query["search"] = params["search_query"]
    if params.get("filter_priority"):
        query["priority"] = params["filter_priority"]
    if params.get("filter_status"):
        query["status"] = params["filter_status"]
    if params.get("filter_tags"):
        query["tag"] = params["filter_tags"][0]  # API supports one tag filter
    if params.get("sort_by"):
        query["sort_by"] = params["sort_by"]
        query["sort_order"] = params.get("sort_order", "asc")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=query)
        resp.raise_for_status()
        return resp.json()


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
            payload = {
                "title": params.get("title", "Untitled task"),
                "description": params.get("description"),
                "isComplete": False,
                "dueDate": params.get("dueDate"),
                "priority": params.get("priority", "medium"),
                "tags": params.get("tags", []),
                "recurringInterval": params.get("recurringInterval"),
                "reminderAt": params.get("reminderAt"),
            }
            result = await _api_create_task(user_id, payload)
            operation = {
                "operation": "create",
                "task_id": result.get("id"),
                "status": "success",
                "title": result.get("title", ""),
                "priority": result.get("priority"),
                "tags": result.get("tags", []),
                "recurringInterval": result.get("recurringInterval"),
                "dueDate": result.get("dueDate"),
                "reminderAt": result.get("reminderAt"),
            }

        elif intent in ("list_tasks", "search_tasks"):
            tasks_data = await _api_list_tasks(user_id, params)
            operation = {
                "operation": "list",
                "status": "success",
                "count": len(tasks_data),
                "tasks": tasks_data,
                "filter": params.get("filter_status", "all"),
                "search_query": params.get("search_query"),
                "sort_by": params.get("sort_by"),
            }
            result = {"tasks": tasks_data, "count": len(tasks_data)}

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
            payload = {k: v for k, v in {
                "title": params.get("title"),
                "description": params.get("description"),
                "dueDate": params.get("dueDate"),
                "priority": params.get("priority"),
                "tags": params.get("tags"),
                "recurringInterval": params.get("recurringInterval"),
                "reminderAt": params.get("reminderAt"),
            }.items() if v is not None}
            result = await _api_update_task(user_id, task_id, payload)
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
