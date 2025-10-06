from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime


class ChatMessage(BaseModel):
    role: Literal["user", "agent", "system"]
    text: str
    metadata: Optional[dict] = None
    timestamp: datetime


class ConversationCreate(BaseModel):
    # user_id is optional because the server will infer the user from the
    # authenticated JWT. Clients do not need to (and should not) provide it.
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: Optional[str] = None


class ConversationOut(BaseModel):
    id: str
    user_id: str
    session_id: Optional[str]
    title: Optional[str]
    messages: List[ChatMessage]
    created_at: datetime
    updated_at: datetime


class AppendMessagePayload(BaseModel):
    conversation_id: str
    message: ChatMessage
