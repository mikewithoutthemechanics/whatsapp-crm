"""
WhatsApp CRM SA — Database Session Layer
========================================
SQLAlchemy session factory + FastAPI dependency for database access.
Supports PostgreSQL (Supabase) and SQLite fallback for local development.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import StaticPool
import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Engine Setup ─────────────────────────────────────────────

def get_engine():
    """Create SQLAlchemy engine based on DATABASE_URL."""
    db_url = settings.DATABASE_URL

    if db_url.startswith("sqlite"):
        # SQLite: no async, WAL mode for better concurrency
        engine = create_engine(
            db_url,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Enable WAL mode for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        # PostgreSQL with connection pooling
        engine = create_engine(
            db_url,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )

    return engine


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ─── FastAPI Dependency ───────────────────────────────────────

def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Table Creation ──────────────────────────────────────────

def init_db():
    """Create all tables defined in models."""
    from app.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


# ─── Helper for direct access (non-FastAPI contexts) ─────────

def get_session() -> Session:
    """Get a database session for background tasks, scripts, etc."""
    return SessionLocal()
