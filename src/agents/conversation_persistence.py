from typing import List, Dict, Any, Optional
import uuid
from sqlmodel import select
from ..models.conversation import Conversation, ConversationCreate
from ..models.message import Message, MessageCreate
from ..db.session import AsyncSessionLocal, get_or_create_user


async def get_conversation_history(user_id: str, conversation_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch conversation history from database
    """
    async with AsyncSessionLocal() as session:
        if conversation_id:
            # Get messages for specific conversation
            stmt = (
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.timestamp.asc())
            )
        else:
            # Ensure user exists before creating conversation
            await get_or_create_user(session, user_id)
            await session.commit()

            # Get most recent conversation for the user, or create a new one
            conversation_id = str(uuid.uuid4())
            conversation_data = ConversationCreate(
                title=f"Conversation with {user_id}",
            )

            conversation = Conversation(
                **conversation_data.dict(),
                id=conversation_id,
                user_id=user_id
            )

            session.add(conversation)
            await session.commit()

        # Fetch messages for the conversation
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
        )

        result = await session.execute(stmt)
        messages = result.scalars().all()

        # Convert to the format expected by the AI model
        history = []
        for msg in messages:
            history.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat() if msg.timestamp else None
            })

        return history


async def save_conversation(
    user_id: str,
    conversation_id: Optional[str],
    user_message: str,
    assistant_response: str,
    tool_calls: List[Dict[str, Any]]
) -> str:
    """
    Save user message and assistant response to database
    """
    async with AsyncSessionLocal() as session:
        # If no conversation_id provided, create a new one
        if not conversation_id:
            # Ensure user exists before creating conversation
            await get_or_create_user(session, user_id)
            await session.commit()

            conversation_id = str(uuid.uuid4())
            conversation_data = ConversationCreate(
                title=f"Conversation with {user_id}",
            )

            conversation = Conversation(
                **conversation_data.dict(),
                id=conversation_id,
                user_id=user_id
            )

            session.add(conversation)
            await session.commit()

        # Save user message
        user_message_obj = Message(
            role="user",
            content=user_message,
            conversation_id=conversation_id,
            user_id=user_id
        )

        session.add(user_message_obj)

        # Save assistant response
        assistant_message_obj = Message(
            role="assistant",
            content=assistant_response,
            conversation_id=conversation_id,
            user_id=user_id,
            tool_calls=str(tool_calls) if tool_calls else None
        )

        session.add(assistant_message_obj)

        await session.commit()

        return conversation_id
