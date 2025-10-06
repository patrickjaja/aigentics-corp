"""Event store schema with TimescaleDB hypertable support.

This module defines the event sourcing schema for storing all domain events
in a TimescaleDB hypertable for efficient time-series queries and audit trails.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

Base = declarative_base()


class DomainEvent(Base):
    """Domain event for event sourcing with complete metadata.

    All state changes in the system are recorded as immutable events
    in this table, which is configured as a TimescaleDB hypertable
    for efficient time-based queries and retention policies.

    Attributes:
        event_id: Unique identifier for this event
        aggregate_id: ID of the aggregate root this event belongs to
        aggregate_type: Type name of the aggregate (Customer, Offer, etc.)
        event_type: Name of the event (CustomerCreated, OfferApproved, etc.)
        event_version: Schema version for event evolution
        occurred_at: When the event occurred (partition key for hypertable)
        correlation_id: Groups related events (e.g., all events in a transaction)
        causation_id: Event that caused this event (for tracing)
        actor_id: User/system that triggered this event
        metadata: Additional context (IP, user agent, etc.)
        payload: Event data specific to the event type
    """

    __tablename__ = "domain_events"

    # Core identifiers
    event_id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    aggregate_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False, index=True)

    # Event metadata
    event_type = Column(String(100), nullable=False, index=True)
    event_version = Column(Integer, nullable=False, default=1)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True)

    # Tracing and causality
    correlation_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    causation_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Actor information
    actor_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    # Data
    metadata = Column(JSON, nullable=False, default=dict)
    payload = Column(JSON, nullable=False)

    # Indexes for common queries
    __table_args__ = (
        Index("idx_aggregate_events", "aggregate_id", "occurred_at"),
        Index("idx_event_type_time", "event_type", "occurred_at"),
        Index("idx_correlation", "correlation_id", "occurred_at"),
        Index("idx_actor_events", "actor_id", "occurred_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation."""
        return {
            "event_id": str(self.event_id),
            "aggregate_id": str(self.aggregate_id),
            "aggregate_type": self.aggregate_type,
            "event_type": self.event_type,
            "event_version": self.event_version,
            "occurred_at": self.occurred_at.isoformat(),
            "correlation_id": str(self.correlation_id),
            "causation_id": str(self.causation_id) if self.causation_id else None,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "metadata": self.metadata,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainEvent":
        """Create event from dictionary representation."""
        return cls(
            event_id=UUID(data["event_id"]) if "event_id" in data else uuid4(),
            aggregate_id=UUID(data["aggregate_id"]),
            aggregate_type=data["aggregate_type"],
            event_type=data["event_type"],
            event_version=data.get("event_version", 1),
            occurred_at=datetime.fromisoformat(data["occurred_at"]) if isinstance(data.get("occurred_at"), str) else data.get("occurred_at", datetime.utcnow()),
            correlation_id=UUID(data["correlation_id"]),
            causation_id=UUID(data["causation_id"]) if data.get("causation_id") else None,
            actor_id=UUID(data["actor_id"]) if data.get("actor_id") else None,
            metadata=data.get("metadata", {}),
            payload=data["payload"],
        )


class EventStore:
    """Repository for storing and retrieving domain events.

    This class provides high-level operations for working with the event store,
    including appending events, retrieving event streams, and querying by
    various criteria.
    """

    def __init__(self, session: Session):
        """Initialize event store with database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    async def append(self, event: DomainEvent) -> None:
        """Append a new event to the store.

        Args:
            event: Domain event to store

        Raises:
            ValueError: If event is invalid
            Exception: If database operation fails
        """
        self.session.add(event)
        await self.session.flush()

    async def append_batch(self, events: List[DomainEvent]) -> None:
        """Append multiple events atomically.

        Args:
            events: List of domain events to store

        Raises:
            ValueError: If any event is invalid
            Exception: If database operation fails
        """
        self.session.add_all(events)
        await self.session.flush()

    async def get_aggregate_stream(
        self,
        aggregate_id: UUID,
        from_version: int = 0,
    ) -> List[DomainEvent]:
        """Get all events for an aggregate in chronological order.

        Args:
            aggregate_id: ID of the aggregate root
            from_version: Only return events after this version (inclusive)

        Returns:
            List of domain events ordered by occurred_at
        """
        query = (
            self.session.query(DomainEvent)
            .filter(DomainEvent.aggregate_id == aggregate_id)
            .filter(DomainEvent.event_version >= from_version)
            .order_by(DomainEvent.occurred_at)
        )
        return query.all()

    async def get_events_by_type(
        self,
        event_type: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[DomainEvent]:
        """Get events of a specific type within a time range.

        Args:
            event_type: Type of events to retrieve
            from_time: Start of time range (inclusive)
            to_time: End of time range (exclusive)
            limit: Maximum number of events to return

        Returns:
            List of domain events ordered by occurred_at
        """
        query = self.session.query(DomainEvent).filter(
            DomainEvent.event_type == event_type
        )

        if from_time:
            query = query.filter(DomainEvent.occurred_at >= from_time)
        if to_time:
            query = query.filter(DomainEvent.occurred_at < to_time)

        query = query.order_by(DomainEvent.occurred_at).limit(limit)
        return query.all()

    async def get_events_by_correlation(
        self,
        correlation_id: UUID,
    ) -> List[DomainEvent]:
        """Get all events that share a correlation ID.

        Useful for tracing all events that occurred as part of a
        single business transaction or process.

        Args:
            correlation_id: Correlation ID to filter by

        Returns:
            List of domain events ordered by occurred_at
        """
        query = (
            self.session.query(DomainEvent)
            .filter(DomainEvent.correlation_id == correlation_id)
            .order_by(DomainEvent.occurred_at)
        )
        return query.all()

    async def get_events_by_actor(
        self,
        actor_id: UUID,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[DomainEvent]:
        """Get all events triggered by a specific actor.

        Args:
            actor_id: ID of the actor (user or system)
            from_time: Start of time range (inclusive)
            to_time: End of time range (exclusive)
            limit: Maximum number of events to return

        Returns:
            List of domain events ordered by occurred_at
        """
        query = self.session.query(DomainEvent).filter(
            DomainEvent.actor_id == actor_id
        )

        if from_time:
            query = query.filter(DomainEvent.occurred_at >= from_time)
        if to_time:
            query = query.filter(DomainEvent.occurred_at < to_time)

        query = query.order_by(DomainEvent.occurred_at).limit(limit)
        return query.all()

    async def count_events(
        self,
        aggregate_type: Optional[str] = None,
        event_type: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> int:
        """Count events matching specified criteria.

        Args:
            aggregate_type: Filter by aggregate type
            event_type: Filter by event type
            from_time: Start of time range (inclusive)
            to_time: End of time range (exclusive)

        Returns:
            Number of matching events
        """
        query = self.session.query(DomainEvent)

        if aggregate_type:
            query = query.filter(DomainEvent.aggregate_type == aggregate_type)
        if event_type:
            query = query.filter(DomainEvent.event_type == event_type)
        if from_time:
            query = query.filter(DomainEvent.occurred_at >= from_time)
        if to_time:
            query = query.filter(DomainEvent.occurred_at < to_time)

        return query.count()


# SQL for creating TimescaleDB hypertable
# This should be run as a migration after the table is created
CREATE_HYPERTABLE_SQL = """
-- Convert events table to TimescaleDB hypertable
SELECT create_hypertable(
    'domain_events',
    'occurred_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create retention policy: keep events for 10 years (legal requirement)
SELECT add_retention_policy(
    'domain_events',
    INTERVAL '10 years',
    if_not_exists => TRUE
);

-- Create continuous aggregate for daily event counts
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_event_counts
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', occurred_at) AS day,
    aggregate_type,
    event_type,
    COUNT(*) as event_count
FROM domain_events
GROUP BY day, aggregate_type, event_type
WITH NO DATA;

-- Add refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy(
    'daily_event_counts',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Create compression policy: compress chunks older than 30 days
SELECT add_compression_policy(
    'domain_events',
    INTERVAL '30 days',
    if_not_exists => TRUE
);
"""
