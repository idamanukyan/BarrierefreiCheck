"""
Database Configuration

Sets up SQLAlchemy engine and session management with production-ready pooling.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

# Create engine with production-ready connection pool settings
engine = create_engine(
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

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database sessions.
    Yields a database session and closes it after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Called on application startup.
    """
    Base.metadata.create_all(bind=engine)
