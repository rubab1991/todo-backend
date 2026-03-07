from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from ..services.chat_service import process_user_message
from ..middleware.auth import validate_user_id

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None


@router.post("/chat", response_model=dict)
async def chat_endpoint(
    body: ChatRequest,
    user_id: str = Depends(validate_user_id),
):
    """
    Process a user message and return an appropriate response with any task operations performed
    """
    try:
        user_info = {"email": body.user_email, "name": body.user_name}
        response = await process_user_message(user_id, body.message, body.conversation_id, user_info)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))