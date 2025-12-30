"""Database connection for synchronous operations."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Create engine
engine = create_engine('sqlite:///./data/mcparr.db', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()