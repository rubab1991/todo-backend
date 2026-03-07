from .user import User, UserRead, UserCreate
from .task import Task, TaskRead, TaskCreate, TaskUpdate
from .conversation import Conversation, ConversationRead, ConversationCreate, ConversationUpdate
from .message import Message, MessageRead, MessageCreate
from .audit_log import AuditLog  # T064: Phase V audit logging

# Import all models here to ensure SQLAlchemy registers them properly
__all__ = [
    "User",
    "UserRead",
    "UserCreate",
    "Task",
    "TaskRead",
    "TaskCreate",
    "TaskUpdate",
    "Conversation",
    "ConversationRead",
    "ConversationCreate",
    "ConversationUpdate",
    "Message",
    "MessageRead",
    "MessageCreate",
    "AuditLog",
]