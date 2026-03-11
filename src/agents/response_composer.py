"""
Response Composer — Phase V.
Builds user-friendly chatbot responses for all task operations including
search/filter results, validation errors, and reminder notifications.
"""
from typing import Dict, Any, List, Optional
from .error_handler import handle_error


def compose_response(
    task_result: Dict[str, Any],
    intent_result: Dict[str, Any],
    user_info: Optional[Dict[str, Any]] = None,
) -> str:
    intent = intent_result.get("intent", "")
    original_message = intent_result.get("original_message", "")
    user_info = user_info or {}

    # Validation errors (e.g. past reminder)
    if task_result.get("status") == "validation_error":
        err = task_result.get("validation_error", "Invalid input.")
        return f"I couldn't save that: {err}"

    if task_result.get("status") == "error":
        error_msg = task_result.get("result", {}).get("error", "Unknown error occurred")
        return f"Sorry, I encountered an error: {error_msg}"

    operations = task_result.get("operations", [])

    if intent == "add_task":
        if operations:
            op = operations[0]
            if op.get("status") == "success":
                parts = [f"Task '{op.get('title', 'unnamed')}' added successfully!"]
                if op.get("priority"):
                    parts.append(f"Priority: {op['priority']}")
                if op.get("tags"):
                    parts.append(f"Tags: {', '.join(op['tags'])}")
                if op.get("dueDate"):
                    parts.append(f"Due: {op['dueDate']}")
                if op.get("reminderAt"):
                    parts.append(f"Reminder set for {op['reminderAt']}")
                if op.get("recurringInterval"):
                    parts.append(f"Repeats {op['recurringInterval']}")
                return " | ".join(parts)
        return "I tried to add your task, but something went wrong."

    elif intent in ("list_tasks", "search_tasks"):
        if operations:
            op = operations[0]
            task_count = op.get("count", 0)
            if op.get("status") == "success":
                if task_count == 0:
                    # T029/T033: "no matching tasks" message
                    if op.get("search_query") or op.get("filter") not in (None, "all"):
                        return "No tasks found matching your criteria."
                    return "You have no tasks at the moment. Try adding one!"
                tasks = op.get("tasks", [])
                header = f"Here are your {task_count} task{'s' if task_count != 1 else ''}:"
                if op.get("search_query"):
                    header = f"Found {task_count} task{'s' if task_count != 1 else ''} matching '{op['search_query']}':"
                lines = [header]
                for task in tasks:
                    task_id = task.get("id", "?")
                    title = task.get("title", "Untitled")
                    status = task.get("status", "pending")
                    priority = task.get("priority", "medium")
                    tags = task.get("tags", [])
                    due = task.get("dueDate", "")
                    status_icon = "✅" if status == "completed" else "⏳"
                    prio_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "")
                    tag_str = f" [{', '.join(tags)}]" if tags else ""
                    due_str = f" (due {due})" if due else ""
                    lines.append(f"  {status_icon} {prio_icon} #{task_id}: {title}{tag_str}{due_str}")
                return "\n".join(lines)
        return "I couldn't retrieve your tasks. Please try again."

    elif intent == "update_task":
        if operations:
            op = operations[0]
            if op.get("status") == "success":
                return f"Task #{op.get('task_id')} updated successfully."
        return "I couldn't update your task. Please try again."

    elif intent == "complete_task":
        if operations:
            op = operations[0]
            if op.get("status") == "success":
                return f"Task #{op.get('task_id')} marked complete! ✅"
        return "I couldn't complete your task. Please try again."

    elif intent == "delete_task":
        if operations:
            op = operations[0]
            if op.get("status") == "success":
                return f"Task #{op.get('task_id')} deleted."
        return "I couldn't delete your task. Please try again."

    elif intent == "greeting":
        user_name = user_info.get("name")
        if user_name:
            return f"Hello, {user_name}! I'm your AI task manager. Ask me to add, search, sort, or manage tasks."
        return "Hello! I'm your AI task manager. You can add, search, filter, sort, and manage tasks."

    elif intent == "help_request":
        return (
            "Here's what I can do:\n"
            "- Add: 'Create a high-priority task: submit report, tagged work'\n"
            "- Search: 'Show all high-priority tasks tagged work'\n"
            "- Sort: 'List tasks sorted by due date'\n"
            "- Due dates: 'Add task: file taxes, due April 15'\n"
            "- Reminders: 'Remind me April 10 at 9am'\n"
            "- Recurring: 'Add daily task: team standup'\n"
            "- Complete: 'Mark task #1 as complete'\n"
            "- Delete: 'Delete task #2'"
        )

    elif intent == "identity":
        msg_lower = original_message.lower().strip()
        if "who are you" in msg_lower or "what are you" in msg_lower:
            return "I'm your AI task manager — I can create, search, sort, and manage tasks."
        user_email = user_info.get("email")
        user_name = user_info.get("name")
        if user_name and user_email:
            return f"You are {user_name} ({user_email})."
        elif user_email:
            return f"Logged in as {user_email}."
        return "I know you're logged in but don't have your profile details."

    else:
        msg_lower = original_message.lower().strip()
        if any(p in msg_lower for p in ("thank", "thanks", "thx")):
            return "You're welcome! Let me know if you need anything else."
        return (
            "I'm not sure how to help with that. Try: 'add task: buy groceries', "
            "'show high-priority tasks', or 'list tasks sorted by due date'."
        )
