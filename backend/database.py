"""Database setup and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from contextlib import contextmanager

from .config import get_settings

settings = get_settings()

# Use DATABASE_URL if provided (PostgreSQL for production), otherwise SQLite
if settings.DATABASE_URL:
    DATABASE_URL = settings.DATABASE_URL
    # PostgreSQL doesn't need check_same_thread
    engine = create_engine(DATABASE_URL, echo=False)
else:
    # Ensure data directory exists for SQLite
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite:///{settings.DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Needed for SQLite with FastAPI
        echo=False,
    )

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database session (use outside of FastAPI)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from . import models  # noqa: F401 - Import to register models
    Base.metadata.create_all(bind=engine)
