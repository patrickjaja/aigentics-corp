"""Base repository interface for aggregate roots.

This module provides the abstract base class for repositories that
implement event sourcing patterns. Repositories load aggregates from
events and persist new events.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID

from ..events.schema import DomainEvent, EventStore

T = TypeVar("T")  # Aggregate type


class Repository(ABC, Generic[T]):
    """Abstract base repository for event-sourced aggregates.

    This repository implements the Repository pattern with event sourcing.
    Instead of loading/saving full objects, it works with event streams.

    Key concepts:
    - Load: Reconstruct aggregate from event stream
    - Save: Append new events to stream
    - Optimistic concurrency via version checking
    """

    def __init__(self, event_store: EventStore, aggregate_type: Type[T]):
        """Initialize repository.

        Args:
            event_store: Event store for persistence
            aggregate_type: Type of aggregate this repository manages
        """
        self.event_store = event_store
        self.aggregate_type = aggregate_type

    async def get_by_id(self, aggregate_id: UUID) -> Optional[T]:
        """Load aggregate by ID from event stream.

        Args:
            aggregate_id: ID of aggregate to load

        Returns:
            Reconstructed aggregate or None if not found
        """
        events = await self.event_store.get_aggregate_stream(aggregate_id)

        if not events:
            return None

        return self._reconstruct_from_events(events)

    async def save(
        self,
        aggregate: T,
        expected_version: Optional[int] = None,
    ) -> None:
        """Save aggregate by appending new events.

        Args:
            aggregate: Aggregate to save
            expected_version: Expected version for optimistic concurrency

        Raises:
            ConcurrencyError: If version mismatch detected
        """
        # Get uncommitted events from aggregate
        new_events = self._get_uncommitted_events(aggregate)

        if not new_events:
            return  # No changes to save

        # Check version if optimistic locking requested
        if expected_version is not None:
            current_version = await self._get_current_version(
                self._get_aggregate_id(aggregate)
            )
            if current_version != expected_version:
                raise ConcurrencyError(
                    f"Version mismatch: expected {expected_version}, "
                    f"got {current_version}"
                )

        # Append events to store
        await self.event_store.append_batch(new_events)

        # Mark events as committed
        self._mark_events_committed(aggregate)

    async def exists(self, aggregate_id: UUID) -> bool:
        """Check if aggregate exists.

        Args:
            aggregate_id: ID to check

        Returns:
            True if aggregate has any events
        """
        events = await self.event_store.get_aggregate_stream(
            aggregate_id,
            from_version=0,
        )
        return len(events) > 0

    async def delete(self, aggregate_id: UUID) -> None:
        """Soft delete aggregate by appending a deletion event.

        Note: Events are never physically deleted (append-only).
        A tombstone event marks the aggregate as deleted.

        Args:
            aggregate_id: ID of aggregate to delete
        """
        deletion_event = self._create_deletion_event(aggregate_id)
        await self.event_store.append(deletion_event)

    async def _get_current_version(self, aggregate_id: UUID) -> int:
        """Get current version of aggregate.

        Args:
            aggregate_id: ID of aggregate

        Returns:
            Current version number
        """
        events = await self.event_store.get_aggregate_stream(aggregate_id)
        return len(events)

    @abstractmethod
    def _reconstruct_from_events(self, events: List[DomainEvent]) -> T:
        """Reconstruct aggregate from event stream.

        This method replays events to rebuild the aggregate state.

        Args:
            events: List of events in chronological order

        Returns:
            Reconstructed aggregate
        """
        pass

    @abstractmethod
    def _get_uncommitted_events(self, aggregate: T) -> List[DomainEvent]:
        """Get list of uncommitted events from aggregate.

        Args:
            aggregate: Aggregate to extract events from

        Returns:
            List of new events not yet persisted
        """
        pass

    @abstractmethod
    def _mark_events_committed(self, aggregate: T) -> None:
        """Mark aggregate events as committed.

        Args:
            aggregate: Aggregate whose events were persisted
        """
        pass

    @abstractmethod
    def _get_aggregate_id(self, aggregate: T) -> UUID:
        """Get ID from aggregate.

        Args:
            aggregate: Aggregate instance

        Returns:
            Aggregate ID
        """
        pass

    @abstractmethod
    def _create_deletion_event(self, aggregate_id: UUID) -> DomainEvent:
        """Create deletion/tombstone event.

        Args:
            aggregate_id: ID of aggregate being deleted

        Returns:
            Deletion event
        """
        pass


class ConcurrencyError(Exception):
    """Raised when optimistic concurrency check fails."""

    pass
