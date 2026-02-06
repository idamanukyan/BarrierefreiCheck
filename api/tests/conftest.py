"""
Test configuration and fixtures.
"""

import os
import pytest
from typing import Generator, AsyncGenerator
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment before importing app
os.environ["APP_ENV"] = "test"
os.environ["JWT_SECRET"] = "test-secret-key-that-is-at-least-32-characters-long"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.main import app
from app.database import Base, get_db
from app.models import User, Scan, ScanStatus
from app.routers.auth import get_password_hash, create_access_token


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    """Override database dependency for tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """Create test client with database override."""
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        company="Test Company",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_user_token(test_user: User) -> str:
    """Create access token for test user."""
    return create_access_token(data={"sub": test_user.email})


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def test_scan(db: Session, test_user: User) -> Scan:
    """Create a test scan."""
    scan = Scan(
        user_id=test_user.id,
        url="https://example.com",
        crawl=False,
        max_pages=1,
        status=ScanStatus.COMPLETED,
        score=85.5,
        pages_scanned=1,
        issues_count=5,
        issues_critical=1,
        issues_serious=2,
        issues_moderate=1,
        issues_minor=1,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    with patch("app.services.cache.get_redis_client") as mock:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_client.get.return_value = None
        mock_client.setex.return_value = True
        mock.return_value = mock_client
        yield mock_client
