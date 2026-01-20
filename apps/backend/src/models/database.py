"""
Database session management and configuration.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Generator
from pathlib import Path

from .domain import Base
from ..utils.logger import logger


# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data" / "db"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "fsia.db"

# SQLite connection string
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    connect_args={"check_same_thread": False}  # Needed for SQLite
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Initialize database by creating all tables.
    Safe to call multiple times.
    """
    logger.info(f"Initializing database at: {DB_PATH}")
    Base.metadata.create_all(bind=engine)
    logger.success("Database tables created successfully")


def drop_db():
    """Drop all tables. Use with caution!"""
    logger.warning("Dropping all database tables!")
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Get database session with automatic cleanup.
    
    Usage:
        with get_db() as db:
            technician = db.query(Technician).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def get_db_session() -> Generator[Session, None, None]:
    """
    Get database session for FastAPI dependency injection.
    
    Usage:
        @app.get("/technicians")
        def get_technicians(db: Session = Depends(get_db_session)):
            return db.query(Technician).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
