from sqlmodel import create_engine, text
from src.models.db import DATABASE_URL

engine = create_engine(DATABASE_URL)

def check_tables():
    with engine.connect() as connection:
        for table in ["chatmessage", "task", "user", "workspace"]:
            try:
                connection.execute(text(f"SELECT 1 FROM \"{table}\" LIMIT 1;"))
                print(f"Table '{table}' exists.")
            except Exception as e:
                print(f"Table '{table}' error: {e}")

if __name__ == "__main__":
    check_tables()
