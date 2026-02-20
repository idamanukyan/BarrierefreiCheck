"""
Database Configuration

Sets up SQLAlchemy engine and session management with production-ready pooling
and retry logic for transient connection failures.
"""

import logging
import time
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError, DBAPIError
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds
RETRY_DELAY_MAX = 10.0  # seconds


def _create_engine_with_retry():
    """Create SQLAlchemy engine with retry logic for initial connection."""
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            eng = create_engine(
                settings.database_url,
                echo=settings.debug,
                # Connection pool settings
                pool_size=20,              # Number of connections to keep open
                max_overflow=10,           # Additional connections allowed beyond pool_size
                pool_pre_ping=True,        # Verify connections before using (handles stale connections)
                pool_recycle=3600,         # Recycle connections after 1 hour (prevents timeout issues)
                pool_timeout=30,           # Seconds to wait for a connection from pool
                # SQLite compatibility (no-op for PostgreSQL)
                connect_args={} if "postgresql" in settings.database_url else {"check_same_thread": False},
            )

            # Test the connection
            with eng.connect() as conn:
                conn.execute("SELECT 1" if "postgresql" in settings.database_url else "SELECT 1")

            logger.info("Database connection established successfully")
            return eng

        except OperationalError as e:
            last_error = e
            delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
            logger.warning(
                f"Database connection failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {delay:.1f}s: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    # If all retries failed, create engine anyway (it might work later)
    logger.error(f"Database connection failed after {MAX_RETRIES} attempts: {last_error}")
    return create_engine(
        settings.database_url,
        echo=settings.debug,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_timeout=30,
        connect_args={} if "postgresql" in settings.database_url else {"check_same_thread": False},
    )


# Create engine with retry logic
engine = _create_engine_with_retry()


# Add event listener for connection checkout errors
@event.listens_for(engine, "handle_error")
def handle_connection_error(exception_context):
    """Handle database connection errors with logging."""
    if isinstance(exception_context.original_exception, (OperationalError, DBAPIError)):
        logger.warning(
            f"Database connection error handled: {exception_context.original_exception}"
        )


# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions.
    Yields a database session and closes it after use.
    Includes retry logic for transient connection failures.
    """
    db = None
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            db = SessionLocal()
            # Verify connection is working
            db.execute("SELECT 1" if "postgresql" in settings.database_url else "SELECT 1")
            break
        except OperationalError as e:
            last_error = e
            if db:
                db.close()
                db = None
            delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
            logger.warning(
                f"Database session creation failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {delay:.1f}s: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    if db is None:
        logger.error(f"Failed to create database session after {MAX_RETRIES} attempts")
        raise last_error or OperationalError("Database connection unavailable")

    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for getting database sessions.
    Use this for non-FastAPI contexts (e.g., background tasks).

    Includes retry logic for transient connection failures.

    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = None
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            db = SessionLocal()
            # Verify connection is working
            db.execute("SELECT 1" if "postgresql" in settings.database_url else "SELECT 1")
            break
        except OperationalError as e:
            last_error = e
            if db:
                db.close()
                db = None
            delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
            logger.warning(
                f"Database context creation failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {delay:.1f}s: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    if db is None:
        logger.error(f"Failed to create database context after {MAX_RETRIES} attempts")
        raise last_error or OperationalError("Database connection unavailable")

    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Called on application startup.
    Includes retry logic for connection failures during startup.
    """
    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized successfully")
            return
        except OperationalError as e:
            last_error = e
            delay = min(RETRY_DELAY_BASE * (2 ** attempt), RETRY_DELAY_MAX)
            logger.warning(
                f"Database initialization failed (attempt {attempt + 1}/{MAX_RETRIES}), "
                f"retrying in {delay:.1f}s: {e}"
            )
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)

    logger.error(f"Database initialization failed after {MAX_RETRIES} attempts: {last_error}")
    raise last_error
