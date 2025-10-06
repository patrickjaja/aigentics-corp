"""Event bus implementation with publisher/subscriber pattern.

This module provides an in-process event bus for domain event handling,
with support for async handlers, error handling, and retry logic.
For distributed scenarios, Redis pub/sub can be used as a transport.
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type
from uuid import UUID

from .schema import DomainEvent

logger = logging.getLogger(__name__)


EventHandler = Callable[[DomainEvent], Any]


class EventBus:
    """In-process event bus with pub/sub pattern.

    The event bus allows decoupling between event producers and consumers.
    Multiple handlers can subscribe to the same event type, and all handlers
    are notified asynchronously when an event is published.

    Features:
    - Multiple subscribers per event type
    - Async handler execution
    - Error isolation (one handler failure doesn't affect others)
    - Dead letter queue for failed events
    - Optional Redis pub/sub for distributed scenarios
    """

    def __init__(self, redis_client: Optional[Any] = None):
        """Initialize event bus.

        Args:
            redis_client: Optional Redis client for distributed pub/sub
        """
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []
        self._redis_client = redis_client
        self._failed_events: List[tuple[DomainEvent, Exception]] = []
        self._redis_listener_task: Optional[asyncio.Task] = None

    def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """Subscribe a handler to a specific event type.

        Args:
            event_type: Type of event to subscribe to (e.g., "CustomerCreated")
            handler: Async function to call when event is published
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []

        self._handlers[event_type].append(handler)
        logger.info(f"Subscribed handler {handler.__name__} to {event_type}")

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe a handler to all event types.

        Useful for cross-cutting concerns like logging, metrics, or auditing.

        Args:
            handler: Async function to call for every event
        """
        self._wildcard_handlers.append(handler)
        logger.info(f"Subscribed wildcard handler {handler.__name__}")

    def unsubscribe(
        self,
        event_type: str,
        handler: EventHandler,
    ) -> None:
        """Unsubscribe a handler from an event type.

        Args:
            event_type: Event type to unsubscribe from
            handler: Handler to remove
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"Unsubscribed handler {handler.__name__} from {event_type}")
            except ValueError:
                logger.warning(f"Handler {handler.__name__} was not subscribed to {event_type}")

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribed handlers.

        Handlers are executed concurrently. If a handler fails, the error
        is logged but doesn't affect other handlers.

        Args:
            event: Domain event to publish
        """
        event_type = event.event_type
        logger.info(
            f"Publishing event {event_type} "
            f"(aggregate={event.aggregate_type}, id={event.aggregate_id})"
        )

        # Get specific handlers for this event type
        specific_handlers = self._handlers.get(event_type, [])

        # Combine with wildcard handlers
        all_handlers = specific_handlers + self._wildcard_handlers

        if not all_handlers:
            logger.warning(f"No handlers subscribed to {event_type}")
            return

        # Execute all handlers concurrently
        tasks = [
            self._execute_handler(handler, event)
            for handler in all_handlers
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        # Publish to Redis if available (for distributed processing)
        if self._redis_client:
            await self._publish_to_redis(event)

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Publish multiple events efficiently.

        Args:
            events: List of domain events to publish
        """
        logger.info(f"Publishing batch of {len(events)} events")
        tasks = [self.publish(event) for event in events]
        await asyncio.gather(*tasks)

    async def _execute_handler(
        self,
        handler: EventHandler,
        event: DomainEvent,
    ) -> None:
        """Execute a single handler with error handling.

        Args:
            handler: Event handler to execute
            event: Event to pass to handler
        """
        try:
            logger.debug(f"Executing handler {handler.__name__} for {event.event_type}")

            # Support both sync and async handlers
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)

            logger.debug(f"Handler {handler.__name__} completed successfully")

        except Exception as e:
            logger.error(
                f"Handler {handler.__name__} failed for event {event.event_type}: {e}",
                exc_info=True
            )
            self._failed_events.append((event, e))

    async def _publish_to_redis(self, event: DomainEvent) -> None:
        """Publish event to Redis for distributed processing.

        Args:
            event: Event to publish to Redis
        """
        try:
            channel = f"events:{event.event_type}"
            message = event.to_dict()

            await self._redis_client.publish(channel, message)
            logger.debug(f"Published {event.event_type} to Redis channel {channel}")

        except Exception as e:
            logger.error(f"Failed to publish to Redis: {e}", exc_info=True)

    async def start_redis_listener(self) -> None:
        """Start listening for events from Redis.

        This allows the event bus to receive events published by other
        instances of the application in a distributed setup.
        """
        if not self._redis_client:
            logger.warning("Redis client not configured, cannot start listener")
            return

        self._redis_listener_task = asyncio.create_task(
            self._redis_listener_loop()
        )
        logger.info("Started Redis event listener")

    async def stop_redis_listener(self) -> None:
        """Stop the Redis event listener."""
        if self._redis_listener_task:
            self._redis_listener_task.cancel()
            try:
                await self._redis_listener_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped Redis event listener")

    async def _redis_listener_loop(self) -> None:
        """Main loop for Redis event listener."""
        pubsub = self._redis_client.pubsub()

        # Subscribe to all event channels
        await pubsub.psubscribe("events:*")

        try:
            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    await self._handle_redis_message(message)
        except asyncio.CancelledError:
            await pubsub.punsubscribe("events:*")
            await pubsub.close()
            raise

    async def _handle_redis_message(self, message: Dict[str, Any]) -> None:
        """Handle a message received from Redis.

        Args:
            message: Redis pub/sub message
        """
        try:
            event_data = message["data"]
            event = DomainEvent.from_dict(event_data)

            # Publish to local handlers (don't re-publish to Redis)
            redis_client = self._redis_client
            self._redis_client = None

            await self.publish(event)

            self._redis_client = redis_client

        except Exception as e:
            logger.error(f"Failed to handle Redis message: {e}", exc_info=True)

    def get_failed_events(self) -> List[tuple[DomainEvent, Exception]]:
        """Get list of events that failed processing.

        Returns:
            List of (event, exception) tuples
        """
        return self._failed_events.copy()

    def clear_failed_events(self) -> None:
        """Clear the failed events list."""
        self._failed_events.clear()

    async def retry_failed_events(self) -> None:
        """Retry processing failed events."""
        failed = self._failed_events.copy()
        self._failed_events.clear()

        logger.info(f"Retrying {len(failed)} failed events")

        for event, _ in failed:
            await self.publish(event)


class EventPublisher:
    """High-level interface for publishing domain events.

    This class combines the event store and event bus to ensure events
    are both persisted and published to handlers.
    """

    def __init__(self, event_store: Any, event_bus: EventBus):
        """Initialize event publisher.

        Args:
            event_store: EventStore instance for persistence
            event_bus: EventBus instance for pub/sub
        """
        self.event_store = event_store
        self.event_bus = event_bus

    async def publish(self, event: DomainEvent) -> None:
        """Persist and publish a domain event.

        Args:
            event: Domain event to publish
        """
        # First persist to event store
        await self.event_store.append(event)

        # Then publish to handlers
        await self.event_bus.publish(event)

    async def publish_batch(self, events: List[DomainEvent]) -> None:
        """Persist and publish multiple events atomically.

        Args:
            events: List of domain events to publish
        """
        # Persist all events first
        await self.event_store.append_batch(events)

        # Then publish to handlers
        await self.event_bus.publish_batch(events)


# Common event handler examples
async def log_event_handler(event: DomainEvent) -> None:
    """Example handler that logs all events."""
    logger.info(
        f"Event: {event.event_type} "
        f"(aggregate={event.aggregate_type}/{event.aggregate_id})"
    )


async def metrics_event_handler(event: DomainEvent) -> None:
    """Example handler that tracks event metrics."""
    # Increment Prometheus counter
    # event_counter.labels(
    #     event_type=event.event_type,
    #     aggregate_type=event.aggregate_type
    # ).inc()
    pass


async def audit_event_handler(event: DomainEvent) -> None:
    """Example handler that creates audit log entries."""
    # Write to audit log
    logger.info(
        f"Audit: {event.event_type} by actor {event.actor_id} "
        f"at {event.occurred_at}"
    )


# Global event bus instance (singleton pattern)
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance.

    Returns:
        Singleton EventBus instance
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def initialize_event_bus(redis_client: Optional[Any] = None) -> EventBus:
    """Initialize the global event bus with configuration.

    Args:
        redis_client: Optional Redis client for distributed events

    Returns:
        Configured EventBus instance
    """
    global _event_bus
    _event_bus = EventBus(redis_client=redis_client)

    # Register common handlers
    _event_bus.subscribe_all(log_event_handler)
    _event_bus.subscribe_all(metrics_event_handler)
    _event_bus.subscribe_all(audit_event_handler)

    return _event_bus
