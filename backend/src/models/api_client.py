"""APIClient entity and related models for API rate limiting and usage tracking."""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class RateLimit(BaseModel):
    """
    Rate limiting configuration using token bucket algorithm.

    Implements a token bucket rate limiter that refills tokens at a constant rate
    and allows for burst traffic up to burst_size.
    """

    requests_per_minute: int = Field(
        default=100,
        description="Maximum number of requests allowed per minute (refill rate)"
    )
    burst_size: int = Field(
        default=200,
        description="Maximum number of tokens in the bucket (burst capacity)"
    )
    current_tokens: int = Field(
        ...,
        description="Current number of available tokens in the bucket"
    )
    last_refill: datetime = Field(
        ...,
        description="Timestamp of the last token refill operation"
    )

    def refill_tokens(self) -> None:
        """
        Refill tokens based on time elapsed since last refill.

        Calculates tokens to add based on requests_per_minute rate and
        caps at burst_size to prevent unlimited accumulation.
        """
        now = datetime.utcnow()
        time_elapsed = (now - self.last_refill).total_seconds()

        # Calculate tokens to add: (elapsed_seconds / 60) * requests_per_minute
        tokens_to_add = int((time_elapsed / 60.0) * self.requests_per_minute)

        if tokens_to_add > 0:
            # Add tokens but cap at burst_size
            new_token_count = min(self.current_tokens + tokens_to_add, self.burst_size)
            object.__setattr__(self, 'current_tokens', new_token_count)
            object.__setattr__(self, 'last_refill', now)

    def consume_token(self) -> bool:
        """
        Attempt to consume one token for a request.

        Returns:
            bool: True if token was available and consumed, False if rate limit exceeded
        """
        # First refill tokens based on elapsed time
        self.refill_tokens()

        if self.current_tokens > 0:
            object.__setattr__(self, 'current_tokens', self.current_tokens - 1)
            return True
        return False

    class Config:
        """Pydantic configuration."""
        frozen = True


class UsageStats(BaseModel):
    """
    Usage statistics for API client tracking and billing analytics.

    Tracks request counts, success rates, and offer generation metrics
    for monitoring and billing purposes.
    """

    total_requests: int = Field(
        default=0,
        description="Total number of API requests made by this client"
    )
    successful_requests: int = Field(
        default=0,
        description="Number of successfully completed requests"
    )
    failed_requests: int = Field(
        default=0,
        description="Number of failed requests"
    )
    total_offers_generated: int = Field(
        default=0,
        description="Total number of offers generated through this API client"
    )
    last_30_days_requests: int = Field(
        default=0,
        description="Number of requests in the last 30 days (for billing)"
    )

    def record_request(self, success: bool, offers_generated: int = 0) -> "UsageStats":
        """
        Record a new API request and return updated statistics.

        Args:
            success: Whether the request completed successfully
            offers_generated: Number of offers generated in this request

        Returns:
            UsageStats: New instance with updated statistics
        """
        return UsageStats(
            total_requests=self.total_requests + 1,
            successful_requests=self.successful_requests + (1 if success else 0),
            failed_requests=self.failed_requests + (0 if success else 1),
            total_offers_generated=self.total_offers_generated + offers_generated,
            last_30_days_requests=self.last_30_days_requests + 1
        )

    def get_success_rate(self) -> float:
        """
        Calculate success rate as percentage.

        Returns:
            float: Success rate between 0.0 and 1.0, or 0.0 if no requests made
        """
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests

    class Config:
        """Pydantic configuration."""
        frozen = True


class APIClient(BaseModel):
    """
    API Client entity for external system access control.

    Manages API client credentials, rate limiting, and usage tracking.
    Enforces rate limits at the gateway level using token bucket algorithm.

    Invariants:
    - API key must be unique (stored hashed for security)
    - Rate limiting enforced at gateway level
    - Usage tracked for billing and analytics

    Business Rules:
    - Rate limits prevent system abuse
    - Disabled clients cannot make requests
    - Usage statistics enable usage-based billing
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Internal API client identifier"
    )
    name: str = Field(
        ...,
        description="Human-readable name for the API client"
    )
    api_key: str = Field(
        ...,
        description="Hashed API key for authentication (never store plain text)"
    )
    organization: str = Field(
        ...,
        description="Organization or company name that owns this API client"
    )
    rate_limit: RateLimit = Field(
        ...,
        description="Rate limiting configuration and state"
    )
    usage_statistics: UsageStats = Field(
        default_factory=UsageStats,
        description="Usage statistics for monitoring and billing"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this API client is enabled (can be disabled to revoke access)"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when API client was created"
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp of the last successful API request"
    )

    def is_request_allowed(self) -> bool:
        """
        Check if a request is allowed based on enabled status and rate limit.

        Returns:
            bool: True if request is allowed, False if client is disabled or rate limited
        """
        if not self.enabled:
            return False

        return self.rate_limit.consume_token()

    def record_usage(self, success: bool, offers_generated: int = 0) -> None:
        """
        Record API usage and update last_used_at timestamp.

        Args:
            success: Whether the request completed successfully
            offers_generated: Number of offers generated in this request
        """
        new_stats = self.usage_statistics.record_request(success, offers_generated)
        object.__setattr__(self, 'usage_statistics', new_stats)

        if success:
            object.__setattr__(self, 'last_used_at', datetime.utcnow())

    def disable(self) -> None:
        """
        Disable this API client, preventing all future requests.

        Used for revoking access without deleting the client record.
        """
        if self.enabled:
            object.__setattr__(self, 'enabled', False)

    def enable(self) -> None:
        """
        Re-enable this API client, allowing requests again.
        """
        if not self.enabled:
            object.__setattr__(self, 'enabled', True)

    def update_rate_limit(self, requests_per_minute: int, burst_size: int) -> None:
        """
        Update rate limit configuration for this client.

        Args:
            requests_per_minute: New requests per minute limit
            burst_size: New burst capacity
        """
        new_rate_limit = RateLimit(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size,
            current_tokens=burst_size,  # Reset to full burst capacity
            last_refill=datetime.utcnow()
        )
        object.__setattr__(self, 'rate_limit', new_rate_limit)

    def get_usage_summary(self) -> dict:
        """
        Get a summary of usage statistics for reporting.

        Returns:
            dict: Usage summary including success rate and key metrics
        """
        return {
            "total_requests": self.usage_statistics.total_requests,
            "successful_requests": self.usage_statistics.successful_requests,
            "failed_requests": self.usage_statistics.failed_requests,
            "success_rate": self.usage_statistics.get_success_rate(),
            "total_offers_generated": self.usage_statistics.total_offers_generated,
            "last_30_days_requests": self.usage_statistics.last_30_days_requests,
            "last_used_at": self.last_used_at
        }

    class Config:
        """Pydantic configuration."""
        frozen = True
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Partner Integration API",
                "api_key": "hashed_api_key_value_here",
                "organization": "Partner Corp",
                "rate_limit": {
                    "requests_per_minute": 100,
                    "burst_size": 200,
                    "current_tokens": 200,
                    "last_refill": "2025-09-30T12:00:00Z"
                },
                "usage_statistics": {
                    "total_requests": 1500,
                    "successful_requests": 1450,
                    "failed_requests": 50,
                    "total_offers_generated": 750,
                    "last_30_days_requests": 450
                },
                "enabled": True,
                "created_at": "2025-09-01T10:00:00Z",
                "last_used_at": "2025-09-30T11:45:00Z"
            }
        }
