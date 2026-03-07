from sqlmodel import SQLModel, Field, Relationship
from typing import Optional
from datetime import datetime
import uuid


class MessageBase(SQLModel):
    role: str = Field(nullable=False)  # "user" or "assistant"
    content: str = Field(nullable=False)


class Message(MessageBase, table=True):
    __tablename__ = "messages"

    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", nullable=False)
    user_id: str = Field(foreign_key="users.id", nullable=False)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Optional fields for tool calls
    tool_calls: Optional[str] = Field(default=None)  # JSON string
    tool_responses: Optional[str] = Field(default=None)  # JSON string

    # Relationships
    conversation: "Conversation" = Relationship(back_populates="messages")
    user: "User" = Relationship()


class MessageRead(MessageBase):
    id: str
    conversation_id: str
    user_id: str
    timestamp: datetime
    tool_calls: Optional[str]
    tool_responses: Optional[str]


class MessageCreate(MessageBase):
    conversation_id: str
    user_id: str
    tool_calls: Optional[str] = None
    tool_responses: Optional[str] = None