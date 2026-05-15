from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import BASE_DIR
SQLALCHEMY_DATABASE_URL = f"sqlite:///{BASE_DIR}/opus_pro.db"

# Setting check_same_thread=False is needed for SQLite when used with FastAPI/threads
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
