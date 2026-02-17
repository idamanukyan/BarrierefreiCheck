"""
User Context Middleware

Extracts user information from JWT tokens or API keys and sets it
in request.state for use by rate limiters and other middleware.

This middleware runs early in the request lifecycle to enable
plan-based rate limiting before route handlers execute.
"""

import logging
from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from app.config import settings
from app.database import SessionLocal
from app.models import User, APIKey, hash_api_key
from app.services.cache import is_token_blacklisted

logger = logging.getLogger(__name__)

# API Key header name (same as in auth.py)
API_KEY_HEADER = "X-API-Key"


class UserContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract user context from authentication tokens.

    This enables plan-based rate limiting by making user information
    available before rate limit decorators are evaluated.

    Note: This middleware does NOT enforce authentication - it only
    extracts user info when available. Authentication is still
    enforced by the get_current_user dependency.
    """

    async def dispatch(self, request: Request, call_next):
        # Initialize user as None
        request.state.user = None
        request.state.user_plan = "free"

        # Skip for certain paths (health checks, etc.)
        skip_paths = ["/health", "/metrics", "/api/docs", "/api/openapi.json"]
        if any(request.url.path.startswith(path) for path in skip_paths):
            return await call_next(request)

        # Try to extract user from auth token or API key
        db: Optional[Session] = None
        try:
            db = SessionLocal()
            user = await self._extract_user(request, db)
            if user:
                request.state.user = user
                request.state.user_plan = user.plan.value if hasattr(user, 'plan') else "free"
                logger.debug(f"User context set: {user.email} (plan: {request.state.user_plan})")
        except Exception as e:
            # Don't fail the request if user extraction fails
            # Authentication will be enforced by route dependencies
            logger.debug(f"User context extraction failed: {e}")
        finally:
            if db:
                db.close()

        response = await call_next(request)
        return response

    async def _extract_user(self, request: Request, db: Session) -> Optional[User]:
        """Extract user from JWT token or API key."""

        # Try API key first
        api_key = request.headers.get(API_KEY_HEADER)
        if api_key:
            return await self._get_user_from_api_key(api_key, db)

        # Try JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            return await self._get_user_from_token(token, db)

        return None

    async def _get_user_from_api_key(self, api_key: str, db: Session) -> Optional[User]:
        """Authenticate user via API key."""
        if not api_key or not api_key.startswith("ac_"):
            return None

        try:
            key_hash = hash_api_key(api_key)
            api_key_record = db.query(APIKey).filter(
                APIKey.key_hash == key_hash,
            ).first()

            if not api_key_record or not api_key_record.is_valid:
                return None

            user = db.query(User).filter(User.id == api_key_record.user_id).first()

            if user and user.is_active:
                return user
        except Exception as e:
            logger.debug(f"API key validation failed: {e}")

        return None

    async def _get_user_from_token(self, token: str, db: Session) -> Optional[User]:
        """Extract user from JWT token."""
        try:
            # Check if token is blacklisted
            if is_token_blacklisted(token):
                return None

            payload = jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm]
            )
            email: str = payload.get("sub")
            if not email:
                return None

            user = db.query(User).filter(User.email == email).first()

            if user and user.is_active:
                return user
        except JWTError as e:
            logger.debug(f"JWT validation failed: {e}")
        except Exception as e:
            logger.debug(f"Token validation error: {e}")

        return None
