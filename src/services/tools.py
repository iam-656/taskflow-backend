from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime
from ..models.db import engine
from ..models.task import Task

# Tool definitions
def create_task_tool(title: str, description: str = "", priority: str = "medium", due_date: str = "", workspace_id: str = None):
    """
    Creates a new task in the database.
    
    Args:
        title: The title of the task.
        description: A brief description of the task.
        priority: Priority level (low, medium, high).
        due_date: Due date in ISO format (YYYY-MM-DD). Leave empty string "" if not provided.
        workspace_id: The UUID of the workspace (list) to add the task to. Optional.
    """
    with Session(engine) as session:
        due_date_obj = None
        if due_date and due_date.strip():
            try:
                due_date_obj = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError:
                pass # Ignore invalid date format for now or handle better
        
        # Validate workspace_id if provided
        workspace_uuid = None
        if workspace_id:
            try:
                from uuid import UUID
                workspace_uuid = UUID(workspace_id)
            except ValueError:
                pass # Invalid UUID, ignore or handle error

        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date_obj,
            status="todo",
            workspace_id=workspace_uuid
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        return f"Task created successfully: {task.title} (ID: {task.id})"

def list_tasks_tool(status: str = ""):
    """
    Lists tasks from the database, optionally filtered by status.
    
    Args:
        status: Filter by status (todo, in_progress, done). Leave empty string "" to list all.
    """
    with Session(engine) as session:
        query = select(Task)
        if status and status.strip():
            query = query.where(Task.status == status)
        
        tasks = session.exec(query).all()
        
        if not tasks:
            return "No tasks found."
            
        return "\n".join([f"- {t.title} ({t.status}, {t.priority})" for t in tasks])

# List of tools to pass to Gemini
tools_list = [create_task_tool, list_tasks_tool]