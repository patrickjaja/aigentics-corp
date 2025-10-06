"""
Rate Limiting Middleware

Implements rate limiting for API endpoints to prevent abuse.
Uses Redis for distributed rate limiting across multiple instances.
"""

from typing import Optional
from datetime import datetime, timedelta
from fastapi import Header, HTTPException, Response, Request, status
import redis.asyncio as redis
import os


# Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT", "100"))  # requests per window
DEFAULT_WINDOW_SECONDS = int(os.getenv("DEFAULT_WINDOW_SECONDS", "60"))  # 1 minute


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.

    Features:
    - Per-client rate limiting (by API key or IP)
    - Configurable limits and windows
    - X-RateLimit-* headers in responses
    - Distributed support via Redis
    """

    def __init__(
        self,
        redis_url: str = REDIS_URL,
        default_limit: int = DEFAULT_RATE_LIMIT,
        window_seconds: int = DEFAULT_WINDOW_SECONDS
    ):
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self._redis_client: Optional[redis.Redis] = None

    async def get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis_client

    async def check_rate_limit(
        self,
        client_id: str,
        limit: Optional[int] = None,
        window_seconds: Optional[int] = None
    ) -> tuple[bool, int, int, int]:
        """
        Check if client has exceeded rate limit.

        Args:
            client_id: Unique identifier for client (API key or IP)
            limit: Maximum requests per window (uses default if None)
            window_seconds: Window size in seconds (uses default if None)

        Returns:
            Tuple of (allowed, remaining, limit, reset_timestamp)
            - allowed: True if request should be allowed
            - remaining: Number of requests remaining in current window
            - limit: Total limit for the window
            - reset_timestamp: Unix timestamp when window resets
        """
        limit = limit or self.default_limit
        window_seconds = window_seconds or self.window_seconds

        try:
            redis_client = await self.get_redis()

            # Sliding window counter using sorted set
            now = datetime.utcnow()
            window_start = now - timedelta(seconds=window_seconds)

            key = f"rate_limit:{client_id}"

            # Remove old entries outside the window
            await redis_client.zremrangebyscore(
                key,
                "-inf",
                window_start.timestamp()
            )

            # Count requests in current window
            count = await redis_client.zcard(key)

            # Calculate reset time (start of next window)
            reset_time = now + timedelta(seconds=window_seconds)

            if count >= limit:
                # Rate limit exceeded
                return False, 0, limit, int(reset_time.timestamp())

            # Add current request to window
            await redis_client.zadd(
                key,
                {str(now.timestamp()): now.timestamp()}
            )

            # Set expiry on key to clean up old data
            await redis_client.expire(key, window_seconds * 2)

            remaining = limit - count - 1  # -1 for current request

            return True, remaining, limit, int(reset_time.timestamp())

        except Exception as e:
            # If Redis fails, allow the request (fail open)
            # Log error for monitoring
            print(f"Rate limit check failed: {e}")
            return True, limit, limit, int(datetime.utcnow().timestamp())

    async def close(self):
        """Close Redis connection."""
        if self._redis_client:
            await self._redis_client.close()


# Global rate limiter instance
_rate_limiter = RateLimiter()


async def check_rate_limit(
    request: Request,
    response: Response,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> None:
    """
    Dependency for rate limiting.

    Uses API key if available, otherwise falls back to IP address.
    Adds rate limit headers to response.

    Args:
        request: FastAPI request object
        response: FastAPI response object
        x_api_key: Optional API key from header

    Raises:
        HTTPException: 429 if rate limit exceeded
    """
    # Determine client identifier
    if x_api_key:
        client_id = f"api_key:{x_api_key}"
    else:
        # Fall back to IP address
        client_ip = request.client.host if request.client else "unknown"
        client_id = f"ip:{client_ip}"

    # Check rate limit
    allowed, remaining, limit, reset_timestamp = await _rate_limiter.check_rate_limit(
        client_id=client_id
    )

    # Add rate limit headers to response
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_timestamp)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": f"Rate limit of {limit} requests per {_rate_limiter.window_seconds} seconds exceeded",
                "details": {
                    "limit": limit,
                    "reset_at": reset_timestamp
                }
            },
            headers={
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(reset_timestamp),
                "Retry-After": str(_rate_limiter.window_seconds)
            }
        )


async def custom_rate_limit(
    limit: int,
    window_seconds: int = DEFAULT_WINDOW_SECONDS
):
    """
    Custom rate limit dependency with specific limits.

    Usage:
        @router.post("/expensive", dependencies=[Depends(custom_rate_limit(10, 60))])

    Args:
        limit: Maximum requests per window
        window_seconds: Window size in seconds

    Returns:
        Dependency function
    """
    async def rate_limit_checker(
        request: Request,
        response: Response,
        x_api_key: Optional[str] = Header(None, alias="X-API-Key")
    ) -> None:
        # Determine client identifier
        if x_api_key:
            client_id = f"api_key:{x_api_key}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            client_id = f"ip:{client_ip}"

        # Check rate limit with custom limits
        allowed, remaining, actual_limit, reset_timestamp = await _rate_limiter.check_rate_limit(
            client_id=client_id,
            limit=limit,
            window_seconds=window_seconds
        )

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(actual_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_timestamp)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit of {actual_limit} requests per {window_seconds} seconds exceeded",
                    "details": {
                        "limit": actual_limit,
                        "reset_at": reset_timestamp
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(actual_limit),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_timestamp),
                    "Retry-After": str(window_seconds)
                }
            )

    return rate_limit_checker


async def shutdown_rate_limiter():
    """Cleanup function to close Redis connection on app shutdown."""
    await _rate_limiter.close()
