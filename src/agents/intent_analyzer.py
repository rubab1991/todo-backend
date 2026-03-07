"""
Intent Analyzer — Phase V.
Classifies user message intent and extracts all task parameters:
priority, tags, search/filter, sort, due dates, reminders, recurring intervals.
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional


# ── Intent patterns ───────────────────────────────────────────────────────────

INTENT_PATTERNS = {
    "add_task": [
        r'\b(add|create|new|make|remember|remind)\b.*\b(task|todo|item)\b',
        r'\b(add|create|new|make)\b\s+',
        r'\bremember\s+to\b',
        r'\bremind\s+me\b',
        r'\bneed\s+to\b.*\b(remember|do|finish|complete|pay|buy|call|send|write|clean|fix)\b',
    ],
    "search_tasks": [
        r'\b(search|find|look\s+for)\b.*\b(task|todo)\b',
        r'\bshow\s+(me\s+)?(all\s+)?tasks?\b.*\b(tagged|with\s+tag|priority|high|medium|low)\b',
        r'\bfilter\b.*\btask',
        r'\b(all\s+)?(high|medium|low)\s*-?\s*priority\b.*\btask',
        r'\btasks?\b.*(tagged|tag\s+)',
        r'\bsearch\s+\w+',
    ],
    "list_tasks": [
        r'\b(show|list|view|display|get|see)\b.*\b(task|todo|item|all)\b',
        r'\bwhat\b.*\b(task|todo|pending|completed|done)\b',
        r'\bmy\s+tasks\b',
        r'\bpending\b',
        r'\bwhat\s+have\s+i\s+(completed|done|finished)\b',
        r'\bwhat\'?s\s+pending\b',
        r'\bcompleted\s+tasks?\b',
    ],
    "update_task": [
        r'\b(update|change|rename|modify|edit)\b.*\b(task|todo|item)\b',
        r'\b(update|change|rename|modify|edit)\b\s+task\s+',
        r'\bchange\s+task\s+',
    ],
    "complete_task": [
        r'\b(complete|finish|done|mark)\b.*\b(task|todo|item)\b',
        r'\bdone\s+with\b',
        r'\bfinish\b',
        r'\bmark.*complete\b',
        r'\bmark\s+task\s+#?\d+',
    ],
    "delete_task": [
        r'\b(delete|remove|cancel|drop)\b.*\b(task|todo|item)\b',
        r'\b(delete|remove|cancel)\b\s+task\s+',
    ],
    "greeting": [
        r'^(hi|hello|hey|howdy|greetings|good\s+(morning|afternoon|evening)|yo|sup)\b',
    ],
    "help_request": [
        r'\b(help|how\s+do\s+i|how\s+to|what\s+can\s+you|instructions|guide)\b',
    ],
    "identity": [
        r'\bwho\s+am\s+i\b',
        r'\bwhat\s+is\s+my\s+(name|email)\b',
        r'\bwho\s+are\s+you\b',
        r'\bwhat\s+are\s+you\b',
        r'\bmy\s+(name|email|account|profile)\b',
    ],
}


# ── Priority extraction ───────────────────────────────────────────────────────

def _extract_priority(message: str) -> Optional[str]:
    """Extract priority level from message text."""
    msg = message.lower()
    # Explicit priority adjectives
    if re.search(r'\b(high[\s-]*priority|urgent|critical|important)\b', msg):
        return "high"
    if re.search(r'\b(low[\s-]*priority|minor|trivial|whenever)\b', msg):
        return "low"
    if re.search(r'\b(medium[\s-]*priority|normal|medium|regular)\b', msg):
        return "medium"
    # Standalone priority: "priority: high"
    m = re.search(r'\bpriority[:\s]+(high|medium|low)\b', msg)
    if m:
        return m.group(1)
    return None


# ── Tag extraction ────────────────────────────────────────────────────────────

def _extract_tags(message: str) -> List[str]:
    """
    Extract tags from message.
    Supports: "tagged work, urgent", "tag: work", "#work", "tags: a, b"
    """
    tags = []
    msg = message.lower()

    # "tagged X, Y, Z" or "tagged X and Y"
    m = re.search(r'tagged?\s+([a-z0-9,\s]+?)(?:\.|$|\band\b|\bwith\b|\bpriority\b|\bdue\b|\bremind)', msg)
    if m:
        raw = m.group(1).replace(" and ", ",")
        tags += [t.strip() for t in raw.split(",") if t.strip()]

    # "tags: X, Y"
    m = re.search(r'tags?[:\s]+([a-z0-9,\s]+?)(?:\.|$|\band\b)', msg)
    if m:
        raw = m.group(1)
        tags += [t.strip() for t in raw.split(",") if t.strip()]

    # "#hashtag" style
    tags += re.findall(r'#([a-z0-9]+)', msg)

    # Deduplicate
    seen, result = set(), []
    for t in tags:
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    return result


# ── Date/time extraction ──────────────────────────────────────────────────────

_MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sep": 9, "october": 10, "oct": 10,
    "november": 11, "nov": 11, "december": 12, "dec": 12,
}


def _parse_date_expression(expr: str) -> Optional[str]:
    """Parse a natural-language date expression to ISO date string (YYYY-MM-DD)."""
    expr = expr.strip().lower()
    now = datetime.now(tz=timezone.utc)

    # ISO format: 2026-04-10 or 2026-04-10T09:00:00
    iso_m = re.match(r'(\d{4}-\d{2}-\d{2}(?:t\d{2}:\d{2}(?::\d{2})?(?:z|[+-]\d{2}:\d{2})?)?)', expr)
    if iso_m:
        return iso_m.group(1).upper().replace("T", "T")

    if expr in ("today",):
        return now.strftime("%Y-%m-%d")
    if expr in ("tomorrow",):
        return (now + timedelta(days=1)).strftime("%Y-%m-%d")
    if expr == "next week":
        return (now + timedelta(weeks=1)).strftime("%Y-%m-%d")

    # "April 15", "15th April", "Apr 15"
    m = re.match(r'([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?', expr)
    if m and m.group(1) in _MONTH_MAP:
        month = _MONTH_MAP[m.group(1)]
        day = int(m.group(2))
        year = now.year if month >= now.month else now.year + 1
        return f"{year}-{month:02d}-{day:02d}"

    m = re.match(r'(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)', expr)
    if m and m.group(2) in _MONTH_MAP:
        month = _MONTH_MAP[m.group(2)]
        day = int(m.group(1))
        year = now.year if month >= now.month else now.year + 1
        return f"{year}-{month:02d}-{day:02d}"

    # "in N days/weeks"
    m = re.match(r'in\s+(\d+)\s+(day|week|month)s?', expr)
    if m:
        n = int(m.group(1))
        unit = m.group(2)
        if unit == "day":
            return (now + timedelta(days=n)).strftime("%Y-%m-%d")
        elif unit == "week":
            return (now + timedelta(weeks=n)).strftime("%Y-%m-%d")
        elif unit == "month":
            month = now.month + n
            year = now.year + (month - 1) // 12
            month = ((month - 1) % 12) + 1
            return f"{year}-{month:02d}-{now.day:02d}"

    return None


def _extract_due_date(message: str) -> Optional[str]:
    """Extract due date from message."""
    msg = message.lower()
    # "due April 15", "due by tomorrow", "due 2026-04-10"
    m = re.search(r'due\s+(?:by\s+|on\s+)?([a-z0-9\s\-:t+z]+?)(?:\.|,|remind|tag|priority|$)', msg)
    if m:
        return _parse_date_expression(m.group(1).strip())
    return None


def _extract_reminder_at(message: str) -> Optional[str]:
    """Extract reminder time from message."""
    msg = message.lower()
    # "remind me on/at April 10 9am", "reminder at 2026-04-10T09:00:00Z"
    m = re.search(
        r'remind(?:\s+me)?(?:\s+on|\s+at)?\s+([a-z0-9\s\-:t+z]+?)(?:\.|,|due|tag|priority|$)',
        msg
    )
    if m:
        return _parse_date_expression(m.group(1).strip())
    return None


# ── Recurring interval extraction ─────────────────────────────────────────────

def _extract_recurring_interval(message: str) -> Optional[str]:
    """Extract recurrence pattern: daily, weekly, monthly."""
    msg = message.lower()
    if re.search(r'\b(every\s+day|daily|each\s+day)\b', msg):
        return "daily"
    if re.search(r'\b(every\s+week|weekly|each\s+week)\b', msg):
        return "weekly"
    if re.search(r'\b(every\s+month|monthly|each\s+month)\b', msg):
        return "monthly"
    return None


# ── Sort extraction ───────────────────────────────────────────────────────────

def _extract_sort(message: str) -> Dict[str, str]:
    """Extract sort_by and sort_order from message."""
    msg = message.lower()
    sort_by = None
    sort_order = "asc"

    if re.search(r'\bdue\s*date\b', msg):
        sort_by = "due_date"
    elif re.search(r'\bpriority\b', msg):
        sort_by = "priority"
    elif re.search(r'\bcreated?\b', msg):
        sort_by = "created_at"

    if re.search(r'\b(desc|descending|newest|highest|latest)\b', msg):
        sort_order = "desc"
    elif re.search(r'\b(asc|ascending|oldest|lowest|earliest)\b', msg):
        sort_order = "asc"

    return {"sort_by": sort_by, "sort_order": sort_order}


# ── Main analyze_intent ───────────────────────────────────────────────────────

def analyze_intent(message: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
    """
    Analyze user intent from natural language message.
    Returns intent name plus all extracted parameters.
    """
    msg_lower = message.lower().strip()

    predicted_intent = "other"
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, msg_lower):
                predicted_intent = intent
                break
        if predicted_intent != "other":
            break

    params = extract_parameters(message, predicted_intent)

    return {
        "intent": predicted_intent,
        "parameters": params,
        "original_message": message,
    }


def extract_parameters(message: str, intent: str) -> Dict[str, Any]:
    """Extract all parameters from a message for the given intent."""
    params = {}

    # Task ID
    task_id_match = re.search(r'task\s+#?(\d+)', message, re.IGNORECASE)
    if task_id_match:
        params['task_id'] = int(task_id_match.group(1))
    if 'task_id' not in params:
        m = re.search(r'#(\d+)', message)
        if m:
            params['task_id'] = int(m.group(1))

    # Phase V: priority + tags + recurring + dates (for add/update)
    priority = _extract_priority(message)
    if priority:
        params['priority'] = priority

    tags = _extract_tags(message)
    if tags:
        params['tags'] = tags

    recurring = _extract_recurring_interval(message)
    if recurring:
        params['recurringInterval'] = recurring

    due_date = _extract_due_date(message)
    if due_date:
        params['dueDate'] = due_date

    reminder_at = _extract_reminder_at(message)
    if reminder_at:
        params['reminderAt'] = reminder_at

    # Title extraction
    if intent == 'add_task':
        title = _extract_add_title(message)
        if title:
            params['title'] = _clean_title_of_metadata(title)

    elif intent == 'update_task':
        title = _extract_update_title(message)
        if title:
            params['title'] = title

    # Status filter for list/search
    if intent in ('list_tasks', 'search_tasks'):
        msg_lower = message.lower()
        if re.search(r'\b(pending|not\s+done|incomplete|active)\b', msg_lower):
            params['filter_status'] = 'pending'
        elif re.search(r'\b(completed|done|finished)\b', msg_lower):
            params['filter_status'] = 'completed'

        # Search query (for search_tasks)
        if intent == 'search_tasks':
            m = re.search(r'\bsearch(?:\s+for)?\s+(.+?)(?:\s+tagged|\s+priority|\.|$)', msg_lower)
            if m:
                params['search_query'] = m.group(1).strip()
            if priority:
                params['filter_priority'] = priority
            if tags:
                params['filter_tags'] = tags

        # Sort extraction
        if re.search(r'\bsort(ed)?\s+by\b|\bby\s+(priority|due|created)', msg_lower):
            sort_info = _extract_sort(message)
            if sort_info['sort_by']:
                params['sort_by'] = sort_info['sort_by']
                params['sort_order'] = sort_info['sort_order']

    if intent == 'complete_task':
        params['status'] = 'completed'

    # Description after title
    if intent in ['add_task', 'update_task'] and params.get('title'):
        title_pos = message.find(params['title'])
        if title_pos != -1:
            after_title = message[title_pos + len(params['title']):].strip()
            # Don't include metadata as description
            if after_title and len(after_title) < 100 and not re.search(
                r'\b(tag|priority|due|remind|every|daily|weekly|monthly)\b', after_title, re.I
            ):
                params['description'] = after_title

    return params


def _clean_title_of_metadata(title: str) -> str:
    """Strip metadata phrases from extracted title."""
    # Remove priority suffixes: "submit report high-priority"
    title = re.sub(r'\s+(high|medium|low)[\s-]*priority\b.*', '', title, flags=re.I)
    # Remove "tagged X" suffixes
    title = re.sub(r'\s+tagged?\s+.*', '', title, flags=re.I)
    # Remove "due ..." suffixes
    title = re.sub(r'\s+due\s+.*', '', title, flags=re.I)
    # Remove "every day/week..." suffixes
    title = re.sub(r'\s+(every|daily|weekly|monthly).*', '', title, flags=re.I)
    # Remove "remind me..." suffixes
    title = re.sub(r'\s+remind.*', '', title, flags=re.I)
    return re.sub(r'[.:,;!?]+$', '', title.strip())


def _extract_add_title(message: str) -> str:
    """Extract task title from an add_task message."""
    msg = message.strip()

    # "create a high-priority task: submit report"
    m = re.search(r'(?:add|create|make|new)\s+(?:a\s+)?(?:[\w\s-]*?task)[:\s]+(.+?)(?:\.|$)', msg, re.I)
    if m:
        return m.group(1).strip()

    # "remember to pay bills" / "remind me to call mom"
    m = re.search(r'(?:remember|remind\s+me)\s+to\s+(.+?)(?:\.|$)', msg, re.I)
    if m:
        return m.group(1).strip()

    # "I need to finish report"
    m = re.search(r'need\s+to\s+(?:remember\s+to\s+)?(.+?)(?:\.|$)', msg, re.I)
    if m:
        return m.group(1).strip()

    # Fallback: strip command verb
    clean = re.sub(r'^(add|create|remember|make|new)\s+', '', msg, flags=re.I)
    clean = re.sub(r'^(a\s+)?task\s*[:\s]*', '', clean, flags=re.I)
    clean = re.sub(r'^to\s+', '', clean, flags=re.I)
    return clean.strip()


def _extract_update_title(message: str) -> str:
    """Extract new title from an update_task message."""
    m = re.search(
        r'(?:update|change|rename|modify|edit)\s+task\s+#?\d+\s+(?:to|as)\s+[\'"]?(.+?)[\'"]?\s*$',
        message, re.I
    )
    if m:
        return re.sub(r'[.:,;!?]+$', '', m.group(1).strip())
    return ""
