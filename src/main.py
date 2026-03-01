import os
import logging
from dotenv import load_dotenv
from typing import List, Optional
from uuid import UUID

from fastapi import FastAPI, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
from pydantic import BaseModel
from groq import Groq

from .models.db import init_db, get_session
from .models.task import Task, TaskCreate, TaskUpdate
from .models.workspace import Workspace
from .models.chat import ChatMessage
from .api.deps import get_current_user
from .services.llm import chat_with_gemini

# Load env vars before anything else
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TaskFlow API")

# Configure CORS
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],  # Configurable for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Requests ---
class ChatMessagePayload(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessagePayload] = []
    context_id: str = "default"

class WorkspaceCreate(BaseModel):
    name: str

@app.on_event("startup")
def on_startup():
    init_db()
    
    # --- Groq model discovery ---
    from .services.llm import GROQ_API_KEY
    if GROQ_API_KEY:
        try:
            client = Groq(api_key=GROQ_API_KEY)
            models = client.models.list()
            print("\n=== AVAILABLE GROQ MODELS ===")
            for m in models.data:
                print(m.id)
            print("============================\n")
        except Exception as e:
            print(f"Failed to list Groq models: {e}")

@app.get("/")
def read_root():
    return {"message": "Welcome to TaskFlow API"}

@app.get("/me")
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user

# --- TASKS ---

@app.get("/tasks", response_model=List[Task])
def read_tasks(
    workspace_id: Optional[UUID] = None,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    query = select(Task)
    
    if workspace_id:
        query = query.where(Task.workspace_id == workspace_id)
    
    tasks = session.exec(query).all()
    return tasks

@app.post("/tasks", response_model=Task)
def create_task(
    task: TaskCreate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_task = Task.from_orm(task)
    # Assign to current user (creator)
    # db_task.assignee_id = current_user['id'] # Optional depending on logic

    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

@app.patch("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: UUID,
    task_update: TaskUpdate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task_data = task_update.dict(exclude_unset=True)
    for key, value in task_data.items():
        setattr(db_task, key, value)
        
    session.add(db_task)
    session.commit()
    session.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_task = session.get(Task, task_id)
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    session.delete(db_task)
    session.commit()
    return None

# --- WORKSPACES ---

@app.post("/workspaces", response_model=Workspace)
def create_workspace(
    workspace: WorkspaceCreate,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_workspace = Workspace(name=workspace.name, user_id=current_user['id'])
    session.add(db_workspace)
    session.commit()
    session.refresh(db_workspace)
    return db_workspace

@app.get("/workspaces", response_model=List[Workspace])
def read_workspaces(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    query = select(Workspace).where(Workspace.user_id == current_user['id'])
    return session.exec(query).all()

@app.delete("/workspaces/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: UUID,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    db_workspace = session.get(Workspace, workspace_id)
    if not db_workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if db_workspace.user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Not authorized to delete this workspace")

    # Manually delete tasks associated with this workspace first
    tasks_to_delete = session.exec(select(Task).where(Task.workspace_id == workspace_id)).all()
    for task in tasks_to_delete:
        session.delete(task)

    session.delete(db_workspace)
    session.commit()
    return None

# --- CHAT ---

@app.get("/chat/history", response_model=List[ChatMessage])
def get_chat_history(
    context_id: str = Query("default"),
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    query = select(ChatMessage).where(
        ChatMessage.user_id == current_user['id'],
        ChatMessage.context_id == context_id
    ).order_by(ChatMessage.created_at.asc())
    return session.exec(query).all()

@app.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    logger.info(f"Chat request received: {request.message} (Context: {request.context_id})")
    
    # 1. Save User Message
    user_msg = ChatMessage(
        user_id=current_user['id'],
        role="user",
        content=request.message,
        context_id=request.context_id
    )
    session.add(user_msg)
    session.commit()

    try:
        # 2. Get Response from LLM
        # Convert Pydantic models to dicts for the service
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
        response_text = await chat_with_gemini(request.message, history_dicts, context_id=request.context_id)
        
        # 3. Save Assistant Message
        ai_msg = ChatMessage(
            user_id=current_user['id'],
            role="assistant",
            content=response_text,
            context_id=request.context_id
        )
        session.add(ai_msg)
        session.commit()
        
        logger.info(f"Gemini response: {response_text}")
        return {"role": "assistant", "content": response_text}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/auth/status")
def get_auth_status():
    return {"message": "Auth integration enabled."}
