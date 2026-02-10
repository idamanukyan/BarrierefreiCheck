"""
WebSocket Router

Real-time updates for scan progress and notifications.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Set, Tuple
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        # Map of scan_id -> set of connected websockets
        self._scan_connections: Dict[str, Set[WebSocket]] = {}
        # Map of user_id -> set of connected websockets
        self._user_connections: Dict[str, Set[WebSocket]] = {}
        # Map of websocket -> user_id for cleanup
        self._websocket_users: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: str, scan_id: str = None):
        """Accept connection and register for updates."""
        await websocket.accept()

        async with self._lock:
            # Register user connection
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)
            self._websocket_users[websocket] = user_id

            # Register scan connection if specified
            if scan_id:
                if scan_id not in self._scan_connections:
                    self._scan_connections[scan_id] = set()
                self._scan_connections[scan_id].add(websocket)

        logger.info(f"WebSocket connected: user={user_id}, scan={scan_id}")

    async def disconnect(self, websocket: WebSocket, scan_id: str = None):
        """Remove connection from all registrations."""
        async with self._lock:
            # Get user_id for cleanup
            user_id = self._websocket_users.pop(websocket, None)

            # Remove from user connections
            if user_id and user_id in self._user_connections:
                self._user_connections[user_id].discard(websocket)
                if not self._user_connections[user_id]:
                    del self._user_connections[user_id]

            # Remove from scan connections
            if scan_id and scan_id in self._scan_connections:
                self._scan_connections[scan_id].discard(websocket)
                if not self._scan_connections[scan_id]:
                    del self._scan_connections[scan_id]

        logger.info(f"WebSocket disconnected: user={user_id}, scan={scan_id}")

    async def send_to_user(self, user_id: str, message: dict):
        """Send message to all connections for a user."""
        async with self._lock:
            connections = self._user_connections.get(user_id, set()).copy()

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to user {user_id}: {e}")

    async def send_to_scan(self, scan_id: str, message: dict):
        """Send message to all connections watching a scan."""
        async with self._lock:
            connections = self._scan_connections.get(scan_id, set()).copy()

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send to scan {scan_id}: {e}")

    async def broadcast_scan_progress(
        self,
        scan_id: str,
        user_id: str,
        status: str,
        progress: dict,
        score: float = None
    ):
        """Broadcast scan progress update."""
        message = {
            "type": "scan_progress",
            "scan_id": scan_id,
            "status": status,
            "progress": progress,
            "score": score,
        }
        await self.send_to_scan(scan_id, message)
        await self.send_to_user(user_id, message)

    async def broadcast_scan_completed(
        self,
        scan_id: str,
        user_id: str,
        score: float,
        issues_count: int,
        pages_scanned: int
    ):
        """Broadcast scan completion."""
        message = {
            "type": "scan_completed",
            "scan_id": scan_id,
            "score": score,
            "issues_count": issues_count,
            "pages_scanned": pages_scanned,
        }
        await self.send_to_scan(scan_id, message)
        await self.send_to_user(user_id, message)

    async def broadcast_scan_failed(self, scan_id: str, user_id: str, error: str):
        """Broadcast scan failure."""
        message = {
            "type": "scan_failed",
            "scan_id": scan_id,
            "error": error,
        }
        await self.send_to_scan(scan_id, message)
        await self.send_to_user(user_id, message)


# Global connection manager instance
manager = ConnectionManager()


def verify_ws_token(token: str) -> Optional[Tuple[str, str]]:
    """
    Verify JWT token and return (user_id, email) tuple.

    Returns None if token is invalid.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm]
        )
        email = payload.get("sub")
        user_id = payload.get("user_id")

        if email is None:
            return None

        # If user_id is in the token, use it directly
        if user_id:
            return (user_id, email)

        # Otherwise, return email as identifier (backwards compatibility)
        # In production, the token should always include user_id
        return (email, email)
    except JWTError:
        return None


def get_user_id_from_token(token: str, db: Session) -> Optional[str]:
    """
    Get user ID from token, looking up by email if needed.

    This ensures we always use user ID for WebSocket identification,
    even with older tokens that only have email.
    """
    token_data = verify_ws_token(token)
    if not token_data:
        return None

    user_id, email = token_data

    # If we got a proper user_id from the token, use it
    if user_id and user_id != email:
        return user_id

    # Otherwise, look up the user by email to get their ID
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None

    return str(user.id)


@router.websocket("/ws/scans/{scan_id}")
async def scan_websocket(
    websocket: WebSocket,
    scan_id: str,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time scan progress updates.

    Connect with: ws://host/api/v1/ws/scans/{scan_id}?token={jwt_token}

    Messages received:
    - scan_progress: {"type": "scan_progress", "status": "...", "progress": {...}}
    - scan_completed: {"type": "scan_completed", "score": 85.5, "issues_count": 10}
    - scan_failed: {"type": "scan_failed", "error": "..."}
    """
    # Import here to avoid circular imports
    from app.database import SessionLocal

    # Verify token and get user ID
    db = SessionLocal()
    try:
        user_id = get_user_id_from_token(token, db)
    finally:
        db.close()

    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    try:
        await manager.connect(websocket, user_id, scan_id)

        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "scan_id": scan_id,
            "message": "Connected to scan updates",
            "max_duration_seconds": settings.ws_max_connection_duration_seconds,
        })

        # Track connection start time for max duration enforcement
        import time
        connection_start = time.time()
        last_activity = time.time()

        # Keep connection alive and handle incoming messages
        while True:
            # Check max connection duration
            if time.time() - connection_start > settings.ws_max_connection_duration_seconds:
                await websocket.send_json({
                    "type": "connection_expired",
                    "message": "Maximum connection duration reached. Please reconnect."
                })
                break

            # Check idle timeout
            if time.time() - last_activity > settings.ws_idle_timeout_seconds:
                await websocket.send_json({
                    "type": "idle_timeout",
                    "message": "Connection closed due to inactivity."
                })
                break

            try:
                # Wait for ping/pong or client messages (configurable timeout)
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.ws_ping_interval_seconds)
                )

                # Update last activity time on any message
                last_activity = time.time()

                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                # Send keep-alive ping
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, scan_id)


@router.websocket("/ws/notifications")
async def notifications_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for user notifications.

    Connect with: ws://host/api/v1/ws/notifications?token={jwt_token}

    Receives all scan updates for the authenticated user.
    """
    # Import here to avoid circular imports
    from app.database import SessionLocal

    # Verify token and get user ID
    db = SessionLocal()
    try:
        user_id = get_user_id_from_token(token, db)
    finally:
        db.close()

    if not user_id:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    try:
        await manager.connect(websocket, user_id)

        await websocket.send_json({
            "type": "connected",
            "message": "Connected to notifications",
            "max_duration_seconds": settings.ws_max_connection_duration_seconds,
        })

        # Track connection start time for max duration enforcement
        import time
        connection_start = time.time()
        last_activity = time.time()

        while True:
            # Check max connection duration
            if time.time() - connection_start > settings.ws_max_connection_duration_seconds:
                await websocket.send_json({
                    "type": "connection_expired",
                    "message": "Maximum connection duration reached. Please reconnect."
                })
                break

            # Check idle timeout
            if time.time() - last_activity > settings.ws_idle_timeout_seconds:
                await websocket.send_json({
                    "type": "idle_timeout",
                    "message": "Connection closed due to inactivity."
                })
                break

            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=float(settings.ws_ping_interval_seconds)
                )

                # Update last activity time on any message
                last_activity = time.time()

                if data == "ping":
                    await websocket.send_text("pong")

            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket)


# Helper function to get the manager (for use in other modules)
def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return manager
