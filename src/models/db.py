import os
from pathlib import Path
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session

# Load .env from backend root
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

# Use pool_pre_ping to handle disconnected connections (common with serverless DBs like Neon)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

def init_db():
    from .user import User
    from .task import Task
    from .chat import ChatMessage
    from .workspace import Workspace
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
