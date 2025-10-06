"""Redis session management with TTL support.

This module provides session management using Redis for:
- Anonymous user sessions before customer creation
- Conversation state persistence
- Session expiration with TTL
- Distributed session sharing across instances
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class SessionConfig:
    """Configuration for session management."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        session_ttl: int = 1800,  # 30 minutes
        session_prefix: str = "session:",
        max_retries: int = 3,
        socket_timeout: float = 5.0,
    ):
        """Initialize session configuration.

        Args:
            redis_url: Redis connection URL
            session_ttl: Session time-to-live in seconds
            session_prefix: Prefix for session keys
            max_retries: Maximum retry attempts
            socket_timeout: Socket timeout in seconds
        """
        self.redis_url = redis_url
        self.session_ttl = session_ttl
        self.session_prefix = session_prefix
        self.max_retries = max_retries
        self.socket_timeout = socket_timeout


class SessionManager:
    """Manages user sessions in Redis.

    This class provides session CRUD operations with automatic TTL
    management and serialization/deserialization of session data.

    Features:
    - Automatic session expiration
    - JSON serialization
    - UUID support
    - Distributed session access
    - Session renewal on access
    """

    def __init__(self, config: SessionConfig):
        """Initialize session manager.

        Args:
            config: Session configuration
        """
        self.config = config
        self.redis_client: Optional[Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self.redis_client = await redis.from_url(
                self.config.redis_url,
                decode_responses=True,
                socket_timeout=self.config.socket_timeout,
                max_connections=10,
            )
            # Test connection
            await self.redis_client.ping()
            logger.info("Connected to Redis for session management")

        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {e}", exc_info=True)
            raise

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    def _make_key(self, session_id: str) -> str:
        """Generate Redis key for session.

        Args:
            session_id: Session identifier

        Returns:
            Prefixed Redis key
        """
        return f"{self.config.session_prefix}{session_id}"

    def _serialize_value(self, value: Any) -> Any:
        """Serialize value for JSON storage.

        Args:
            value: Value to serialize

        Returns:
            JSON-serializable value
        """
        if isinstance(value, UUID):
            return str(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, (list, tuple)):
            return [self._serialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        return value

    def _deserialize_value(self, value: Any) -> Any:
        """Deserialize value from JSON storage.

        Args:
            value: Value to deserialize

        Returns:
            Deserialized value
        """
        # Simple deserialization - could be enhanced with type hints
        if isinstance(value, str):
            # Try to parse as UUID
            try:
                return UUID(value)
            except (ValueError, AttributeError):
                pass

            # Try to parse as datetime
            try:
                if "T" in value and len(value) > 18:
                    return datetime.fromisoformat(value)
            except (ValueError, AttributeError):
                pass

        elif isinstance(value, list):
            return [self._deserialize_value(v) for v in value]
        elif isinstance(value, dict):
            return {k: self._deserialize_value(v) for k, v in value.items()}

        return value

    async def create_session(
        self,
        session_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """Create a new session.

        Args:
            session_id: Optional session ID (generated if not provided)
            data: Initial session data
            ttl: Time-to-live in seconds (uses default if not provided)

        Returns:
            Session ID
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        session_id = session_id or str(uuid4())
        ttl = ttl or self.config.session_ttl
        data = data or {}

        # Add metadata
        session_data = {
            "session_id": session_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            **data,
        }

        # Serialize and store
        serialized = self._serialize_value(session_data)
        key = self._make_key(session_id)

        await self.redis_client.setex(
            key,
            ttl,
            json.dumps(serialized),
        )

        logger.info(f"Created session: {session_id} (TTL: {ttl}s)")
        return session_id

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data.

        Args:
            session_id: Session identifier

        Returns:
            Session data or None if not found
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            data = await self.redis_client.get(key)

            if data is None:
                logger.debug(f"Session not found: {session_id}")
                return None

            # Deserialize
            session_data = json.loads(data)
            deserialized = self._deserialize_value(session_data)

            # Update last accessed time and renew TTL
            await self.update_session(
                session_id,
                {"last_accessed": datetime.utcnow().isoformat()},
                renew_ttl=True,
            )

            return deserialized

        except RedisError as e:
            logger.error(f"Failed to get session {session_id}: {e}", exc_info=True)
            return None

    async def update_session(
        self,
        session_id: str,
        data: Dict[str, Any],
        renew_ttl: bool = True,
    ) -> bool:
        """Update session data.

        Args:
            session_id: Session identifier
            data: Data to update (merged with existing)
            renew_ttl: Whether to renew the TTL

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            # Get existing data
            existing_data = await self.redis_client.get(key)

            if existing_data is None:
                logger.warning(f"Cannot update non-existent session: {session_id}")
                return False

            # Merge with new data
            session_data = json.loads(existing_data)
            session_data.update(self._serialize_value(data))

            # Store updated data
            await self.redis_client.set(
                key,
                json.dumps(session_data),
            )

            # Renew TTL if requested
            if renew_ttl:
                await self.redis_client.expire(key, self.config.session_ttl)

            logger.debug(f"Updated session: {session_id}")
            return True

        except RedisError as e:
            logger.error(f"Failed to update session {session_id}: {e}", exc_info=True)
            return False

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False if not found
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            deleted = await self.redis_client.delete(key)
            if deleted:
                logger.info(f"Deleted session: {session_id}")
                return True
            else:
                logger.debug(f"Session not found for deletion: {session_id}")
                return False

        except RedisError as e:
            logger.error(f"Failed to delete session {session_id}: {e}", exc_info=True)
            return False

    async def exists(self, session_id: str) -> bool:
        """Check if session exists.

        Args:
            session_id: Session identifier

        Returns:
            True if session exists, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            return await self.redis_client.exists(key) > 0
        except RedisError as e:
            logger.error(f"Failed to check session existence: {e}", exc_info=True)
            return False

    async def extend_session(self, session_id: str, additional_ttl: int) -> bool:
        """Extend session TTL.

        Args:
            session_id: Session identifier
            additional_ttl: Additional seconds to add to TTL

        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            # Get current TTL
            current_ttl = await self.redis_client.ttl(key)

            if current_ttl <= 0:
                logger.warning(f"Cannot extend expired/missing session: {session_id}")
                return False

            # Set new TTL
            new_ttl = current_ttl + additional_ttl
            await self.redis_client.expire(key, new_ttl)

            logger.info(f"Extended session {session_id} TTL to {new_ttl}s")
            return True

        except RedisError as e:
            logger.error(f"Failed to extend session {session_id}: {e}", exc_info=True)
            return False

    async def get_ttl(self, session_id: str) -> int:
        """Get remaining TTL for session.

        Args:
            session_id: Session identifier

        Returns:
            Remaining seconds (-1 if no expiry, -2 if not found)
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        key = self._make_key(session_id)

        try:
            return await self.redis_client.ttl(key)
        except RedisError as e:
            logger.error(f"Failed to get TTL for session {session_id}: {e}", exc_info=True)
            return -2

    async def get_all_sessions(self, pattern: str = "*") -> list[str]:
        """Get all session IDs matching a pattern.

        Args:
            pattern: Pattern to match session IDs

        Returns:
            List of matching session IDs
        """
        if not self.redis_client:
            raise RuntimeError("Session manager not connected to Redis")

        try:
            key_pattern = self._make_key(pattern)
            keys = []

            async for key in self.redis_client.scan_iter(match=key_pattern):
                # Remove prefix to get session ID
                session_id = key[len(self.config.session_prefix):]
                keys.append(session_id)

            return keys

        except RedisError as e:
            logger.error(f"Failed to get sessions: {e}", exc_info=True)
            return []

    async def count_sessions(self) -> int:
        """Count total number of active sessions.

        Returns:
            Number of active sessions
        """
        sessions = await self.get_all_sessions()
        return len(sessions)

    async def cleanup_expired(self) -> int:
        """Clean up expired sessions (Redis does this automatically).

        This is a no-op as Redis automatically removes expired keys,
        but can be useful for logging/monitoring.

        Returns:
            Number of sessions checked
        """
        sessions = await self.get_all_sessions()
        return len(sessions)

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        if not self.redis_client:
            return False

        try:
            await self.redis_client.ping()
            return True
        except RedisError:
            return False


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance.

    Returns:
        Global SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        raise RuntimeError("Session manager not initialized. Call initialize_session_manager() first.")
    return _session_manager


async def initialize_session_manager(config: SessionConfig) -> SessionManager:
    """Initialize the global session manager.

    Args:
        config: Session configuration

    Returns:
        Initialized SessionManager instance
    """
    global _session_manager
    _session_manager = SessionManager(config)
    await _session_manager.connect()
    return _session_manager


async def shutdown_session_manager() -> None:
    """Shutdown the global session manager."""
    global _session_manager
    if _session_manager:
        await _session_manager.disconnect()
        _session_manager = None
