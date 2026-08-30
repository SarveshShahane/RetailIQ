from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class ChatMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="The chat message content")
    session_id: str | None = Field(None, min_length=1, max_length=100, description="Optional session ID to continue an existing chat session")

class ChatMessageOut(BaseModel):
    id: int
    business_id: int
    user_id: int
    session_id: str
    sender: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ChatSessionOut(BaseModel):
    session_id: str
    last_message: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
