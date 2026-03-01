from sqlmodel import create_engine, text
from src.models.db import DATABASE_URL

engine = create_engine(DATABASE_URL)

def check_chat_table():
    with engine.connect() as connection:
        try:
            connection.execute(text("SELECT 1 FROM chatmessage LIMIT 1;"))
            print("ChatMessage table exists.")
        except Exception as e:
            print(f"ChatMessage table error: {e}")
            # Try to create it? main.py startup does this.

if __name__ == "__main__":
    check_chat_table()
