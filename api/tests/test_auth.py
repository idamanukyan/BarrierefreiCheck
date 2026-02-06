"""
Tests for authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.routers.auth import get_password_hash


class TestRegister:
    """Tests for user registration."""

    def test_register_success(self, client: TestClient, db: Session):
        """Test successful user registration."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User",
                "company": "New Company",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["name"] == "New User"

    def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registration with existing email."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "anotherpassword123",
                "name": "Another User",
            },
        )
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    def test_register_invalid_email(self, client: TestClient):
        """Test registration with invalid email format."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "name": "Test User",
            },
        )
        assert response.status_code == 422

    def test_register_missing_password(self, client: TestClient):
        """Test registration without password."""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "name": "Test User",
            },
        )
        assert response.status_code == 422


class TestLogin:
    """Tests for user login."""

    def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "token" in data
        assert data["user"]["email"] == test_user.email

    def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "anypassword",
            },
        )
        assert response.status_code == 401

    def test_login_inactive_user(self, client: TestClient, db: Session):
        """Test login with inactive user."""
        user = User(
            email="inactive@example.com",
            password_hash=get_password_hash("password123"),
            is_active=False,
        )
        db.add(user)
        db.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "inactive@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 400
        assert "deactivated" in response.json()["detail"].lower()


class TestGetMe:
    """Tests for getting current user profile."""

    def test_get_me_authenticated(self, client: TestClient, auth_headers: dict, test_user: User):
        """Test getting profile when authenticated."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == str(test_user.id)

    def test_get_me_no_auth(self, client: TestClient):
        """Test getting profile without authentication."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client: TestClient):
        """Test getting profile with invalid token."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )
        assert response.status_code == 401


class TestLogout:
    """Tests for logout endpoint."""

    def test_logout_success(self, client: TestClient, auth_headers: dict):
        """Test successful logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        assert response.status_code == 200
        assert "logged out" in response.json()["message"].lower()

    def test_logout_no_auth(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401
