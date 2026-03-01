from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    id: str = Field(primary_key=True)  # Clerk ID
    email: str = Field(index=True, unique=True)
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    
    # Relationships
    tasks: List["Task"] = Relationship(back_populates="assignee")