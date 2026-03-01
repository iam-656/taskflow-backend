from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, Relationship

class TaskBase(SQLModel):
    title: str
    description: Optional[str] = None
    status: str = Field(default="todo")
    priority: str = Field(default="medium")
    due_date: Optional[datetime] = None
    assignee_id: Optional[str] = Field(default=None, foreign_key="user.id")
    workspace_id: Optional[UUID] = Field(
    default=None,
    foreign_key="workspace.id",
    index=True)

class Task(TaskBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    assignee: Optional["User"] = Relationship(back_populates="tasks")
    workspace: Optional["Workspace"] = Relationship(back_populates="tasks")

class TaskCreate(TaskBase):
    pass

class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    assignee_id: Optional[str] = None
    workspace_id: Optional[UUID] = None