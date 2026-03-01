from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field
from typing import Optional

class ChatMessage(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: str = Field(index=True)
    role: str # 'user' or 'assistant'
    content: str
    context_id: str = Field(index=True, default="default") # 'my-day', 'upcoming', 'completed', etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)
