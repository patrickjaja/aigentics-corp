"""CQRS projection handlers for read models.

This module implements the read side of CQRS by projecting events from
the event store into optimized read models. Each projection handler
subscribes to relevant events and updates denormalized views.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
from uuid import UUID

from sqlalchemy import Column, DateTime, Integer, Numeric, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session

from ..events.schema import DomainEvent

logger = logging.getLogger(__name__)

Base = declarative_base()


# Read Model Tables (Projections)


class OfferReadModel(Base):
    """Denormalized read model for offers.

    This table is optimized for queries like:
    - Get all offers for a customer
    - Search offers by status
    - Find offers expiring soon
    """

    __tablename__ = "offers_read_model"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    offer_number = Column(String(20), unique=True, nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    # Customer information (denormalized)
    customer_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)

    # Project information (denormalized)
    project_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    project_name = Column(String(255), nullable=False)

    # Offer details
    status = Column(String(50), nullable=False, index=True)
    total_value = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="EUR")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    valid_until = Column(DateTime(timezone=True), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    viewed_at = Column(DateTime(timezone=True), nullable=True)
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Approval workflow
    approval_required = Column(String(10), default="false")
    approval_status = Column(String(50), nullable=True, index=True)
    approved_by = Column(PG_UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Summary data
    work_package_count = Column(Integer, default=0)
    total_hours = Column(Numeric(10, 2), nullable=True)

    # Full data for detail view
    work_packages = Column(JSONB, nullable=True)
    metadata = Column(JSONB, nullable=True)


class ConversationReadModel(Base):
    """Denormalized read model for conversations."""

    __tablename__ = "conversations_read_model"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)

    # Customer information
    customer_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    customer_name = Column(String(255), nullable=True)

    # Status
    status = Column(String(50), nullable=False, index=True)
    language = Column(String(10), nullable=False)
    completion_percentage = Column(Integer, default=0)

    # Timestamps
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_interaction_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Summary
    interaction_count = Column(Integer, default=0)
    question_count = Column(Integer, default=0)
    requirements_gathered = Column(Integer, default=0)

    # Latest interaction preview
    latest_message = Column(Text, nullable=True)

    # Full context for detail view
    context = Column(JSONB, nullable=True)


class CustomerReadModel(Base):
    """Denormalized read model for customers."""

    __tablename__ = "customers_read_model"

    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    external_id = Column(String(255), unique=True, nullable=False, index=True)

    # Basic information
    company_name = Column(String(255), nullable=False, index=True)
    contact_person = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)

    # Preferences
    language_preference = Column(String(10), nullable=False)

    # GDPR
    gdpr_consent_given_at = Column(DateTime(timezone=True), nullable=True)
    gdpr_consent_withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False)

    # Statistics (computed from events)
    total_conversations = Column(Integer, default=0)
    total_offers = Column(Integer, default=0)
    accepted_offers = Column(Integer, default=0)
    total_value = Column(Numeric(12, 2), default=0)


# Projection Handlers


class ProjectionHandler(ABC):
    """Base class for projection handlers.

    Each projection handler subscribes to relevant events and updates
    its read model accordingly. Handlers are idempotent and can replay
    events to rebuild projections.
    """

    def __init__(self, session: Session):
        """Initialize projection handler.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    @abstractmethod
    def get_event_types(self) -> List[str]:
        """Return list of event types this handler processes.

        Returns:
            List of event type names
        """
        pass

    @abstractmethod
    async def handle(self, event: DomainEvent) -> None:
        """Process an event and update the read model.

        Args:
            event: Domain event to process
        """
        pass

    async def replay(self, events: List[DomainEvent]) -> None:
        """Replay a sequence of events to rebuild projection.

        Args:
            events: List of events in chronological order
        """
        logger.info(f"Replaying {len(events)} events for {self.__class__.__name__}")

        for event in events:
            await self.handle(event)

        await self.session.commit()
        logger.info(f"Replay complete for {self.__class__.__name__}")


class OfferProjectionHandler(ProjectionHandler):
    """Projection handler for offer read model."""

    def get_event_types(self) -> List[str]:
        return [
            "OfferCreated",
            "OfferModified",
            "OfferApproved",
            "OfferSent",
            "OfferViewed",
            "OfferAccepted",
            "OfferRejected",
            "OfferExpired",
        ]

    async def handle(self, event: DomainEvent) -> None:
        """Process offer events."""
        event_type = event.event_type
        payload = event.payload

        if event_type == "OfferCreated":
            await self._handle_offer_created(event, payload)
        elif event_type == "OfferModified":
            await self._handle_offer_modified(event, payload)
        elif event_type == "OfferApproved":
            await self._handle_offer_approved(event, payload)
        elif event_type == "OfferSent":
            await self._handle_offer_sent(event, payload)
        elif event_type == "OfferViewed":
            await self._handle_offer_viewed(event, payload)
        elif event_type == "OfferAccepted":
            await self._handle_offer_accepted(event, payload)
        elif event_type in ["OfferRejected", "OfferExpired"]:
            await self._handle_offer_status_change(event, payload)

    async def _handle_offer_created(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferCreated event."""
        offer = OfferReadModel(
            id=event.aggregate_id,
            offer_number=payload["offer_number"],
            version=payload.get("version", 1),
            customer_id=UUID(payload["customer_id"]),
            customer_name=payload.get("customer_name", ""),
            customer_email=payload.get("customer_email", ""),
            project_id=UUID(payload["project_id"]),
            project_name=payload.get("project_name", ""),
            status=payload.get("status", "DRAFT"),
            total_value=Decimal(str(payload["total_value"])),
            currency=payload.get("currency", "EUR"),
            created_at=event.occurred_at,
            valid_until=datetime.fromisoformat(payload["valid_until"]),
            approval_required=str(payload.get("approval_required", False)).lower(),
            work_package_count=len(payload.get("work_packages", [])),
            total_hours=Decimal(str(payload.get("total_hours", 0))),
            work_packages=payload.get("work_packages"),
            metadata=event.metadata,
        )

        self.session.add(offer)

    async def _handle_offer_modified(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferModified event."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer:
            offer.version = payload.get("version", offer.version + 1)
            offer.total_value = Decimal(str(payload.get("total_value", offer.total_value)))
            offer.work_package_count = len(payload.get("work_packages", []))
            offer.work_packages = payload.get("work_packages", offer.work_packages)

    async def _handle_offer_approved(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferApproved event."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer:
            offer.approval_status = "APPROVED"
            offer.approved_by = event.actor_id
            offer.approved_at = event.occurred_at
            offer.status = "APPROVED"

    async def _handle_offer_sent(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferSent event."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer:
            offer.status = "SENT"
            offer.sent_at = event.occurred_at

    async def _handle_offer_viewed(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferViewed event."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer and not offer.viewed_at:
            offer.status = "VIEWED"
            offer.viewed_at = event.occurred_at

    async def _handle_offer_accepted(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle OfferAccepted event."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer:
            offer.status = "ACCEPTED"
            offer.accepted_at = event.occurred_at

    async def _handle_offer_status_change(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle status change events."""
        offer = self.session.query(OfferReadModel).filter_by(id=event.aggregate_id).first()

        if offer:
            offer.status = payload.get("status", event.event_type.replace("Offer", "").upper())


class ConversationProjectionHandler(ProjectionHandler):
    """Projection handler for conversation read model."""

    def get_event_types(self) -> List[str]:
        return [
            "ConversationStarted",
            "QuestionAsked",
            "AnswerReceived",
            "RequirementIdentified",
            "ConversationCompleted",
            "ConversationPaused",
            "ConversationAbandoned",
        ]

    async def handle(self, event: DomainEvent) -> None:
        """Process conversation events."""
        event_type = event.event_type
        payload = event.payload

        if event_type == "ConversationStarted":
            await self._handle_conversation_started(event, payload)
        elif event_type in ["QuestionAsked", "AnswerReceived"]:
            await self._handle_interaction(event, payload)
        elif event_type == "RequirementIdentified":
            await self._handle_requirement_identified(event, payload)
        elif event_type in ["ConversationCompleted", "ConversationPaused", "ConversationAbandoned"]:
            await self._handle_status_change(event, payload)

    async def _handle_conversation_started(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle ConversationStarted event."""
        conversation = ConversationReadModel(
            id=event.aggregate_id,
            session_id=payload["session_id"],
            customer_id=UUID(payload["customer_id"]) if payload.get("customer_id") else None,
            customer_name=payload.get("customer_name"),
            status="ACTIVE",
            language=payload.get("language", "en"),
            started_at=event.occurred_at,
            last_interaction_at=event.occurred_at,
            context=payload.get("context"),
        )

        self.session.add(conversation)

    async def _handle_interaction(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle interaction events."""
        conversation = self.session.query(ConversationReadModel).filter_by(
            id=event.aggregate_id
        ).first()

        if conversation:
            conversation.interaction_count += 1
            conversation.last_interaction_at = event.occurred_at
            conversation.latest_message = payload.get("content", "")[:500]

            if event.event_type == "QuestionAsked":
                conversation.question_count += 1

            # Update context
            if payload.get("context"):
                conversation.context = payload["context"]

    async def _handle_requirement_identified(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle RequirementIdentified event."""
        conversation = self.session.query(ConversationReadModel).filter_by(
            id=event.aggregate_id
        ).first()

        if conversation:
            conversation.requirements_gathered += 1
            conversation.completion_percentage = payload.get("completion_percentage", 0)

    async def _handle_status_change(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle conversation status changes."""
        conversation = self.session.query(ConversationReadModel).filter_by(
            id=event.aggregate_id
        ).first()

        if conversation:
            status_map = {
                "ConversationCompleted": "COMPLETED",
                "ConversationPaused": "PAUSED",
                "ConversationAbandoned": "ABANDONED",
            }
            conversation.status = status_map.get(event.event_type, conversation.status)

            if event.event_type == "ConversationCompleted":
                conversation.completed_at = event.occurred_at
                conversation.completion_percentage = 100


class CustomerProjectionHandler(ProjectionHandler):
    """Projection handler for customer read model."""

    def get_event_types(self) -> List[str]:
        return [
            "CustomerCreated",
            "ConsentGiven",
            "ConsentWithdrawn",
            "DeletionRequested",
            "OfferCreated",
            "OfferAccepted",
        ]

    async def handle(self, event: DomainEvent) -> None:
        """Process customer events."""
        event_type = event.event_type
        payload = event.payload

        if event_type == "CustomerCreated":
            await self._handle_customer_created(event, payload)
        elif event_type == "ConsentGiven":
            await self._handle_consent_given(event, payload)
        elif event_type == "ConsentWithdrawn":
            await self._handle_consent_withdrawn(event, payload)
        elif event_type == "DeletionRequested":
            await self._handle_deletion_requested(event, payload)
        elif event_type == "OfferCreated":
            await self._update_offer_stats(event, payload)
        elif event_type == "OfferAccepted":
            await self._update_accepted_offer_stats(event, payload)

    async def _handle_customer_created(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle CustomerCreated event."""
        customer = CustomerReadModel(
            id=event.aggregate_id,
            external_id=payload["external_id"],
            company_name=payload["company_name"],
            contact_person=payload["contact_person"],
            email=payload["email"],
            phone=payload.get("phone"),
            language_preference=payload.get("language_preference", "en"),
            created_at=event.occurred_at,
            updated_at=event.occurred_at,
        )

        self.session.add(customer)

    async def _handle_consent_given(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle ConsentGiven event."""
        customer = self.session.query(CustomerReadModel).filter_by(id=event.aggregate_id).first()

        if customer:
            customer.gdpr_consent_given_at = event.occurred_at
            customer.gdpr_consent_withdrawn_at = None

    async def _handle_consent_withdrawn(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle ConsentWithdrawn event."""
        customer = self.session.query(CustomerReadModel).filter_by(id=event.aggregate_id).first()

        if customer:
            customer.gdpr_consent_withdrawn_at = event.occurred_at

    async def _handle_deletion_requested(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Handle DeletionRequested event."""
        customer = self.session.query(CustomerReadModel).filter_by(id=event.aggregate_id).first()

        if customer:
            customer.deletion_requested_at = event.occurred_at

    async def _update_offer_stats(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Update offer statistics when offer is created."""
        customer_id = UUID(payload.get("customer_id"))
        customer = self.session.query(CustomerReadModel).filter_by(id=customer_id).first()

        if customer:
            customer.total_offers += 1

    async def _update_accepted_offer_stats(self, event: DomainEvent, payload: Dict[str, Any]) -> None:
        """Update statistics when offer is accepted."""
        customer_id = UUID(payload.get("customer_id"))
        customer = self.session.query(CustomerReadModel).filter_by(id=customer_id).first()

        if customer:
            customer.accepted_offers += 1
            customer.total_value += Decimal(str(payload.get("total_value", 0)))


class ProjectionRegistry:
    """Registry for managing projection handlers.

    This class coordinates projection handlers, subscribes them to events,
    and provides utilities for rebuilding projections.
    """

    def __init__(self, session: Session):
        """Initialize projection registry.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session
        self.handlers: List[ProjectionHandler] = []

    def register(self, handler: ProjectionHandler) -> None:
        """Register a projection handler.

        Args:
            handler: Projection handler to register
        """
        self.handlers.append(handler)
        logger.info(f"Registered projection handler: {handler.__class__.__name__}")

    def register_all(self) -> None:
        """Register all standard projection handlers."""
        self.register(OfferProjectionHandler(self.session))
        self.register(ConversationProjectionHandler(self.session))
        self.register(CustomerProjectionHandler(self.session))

    def get_handler_for_event(self, event_type: str) -> List[ProjectionHandler]:
        """Get all handlers that process a given event type.

        Args:
            event_type: Event type name

        Returns:
            List of matching projection handlers
        """
        return [
            handler
            for handler in self.handlers
            if event_type in handler.get_event_types()
        ]

    async def handle_event(self, event: DomainEvent) -> None:
        """Dispatch event to relevant projection handlers.

        Args:
            event: Domain event to process
        """
        handlers = self.get_handler_for_event(event.event_type)

        for handler in handlers:
            try:
                await handler.handle(event)
            except Exception as e:
                logger.error(
                    f"Projection handler {handler.__class__.__name__} "
                    f"failed for event {event.event_type}: {e}",
                    exc_info=True
                )

    async def rebuild_all(self, event_store: Any) -> None:
        """Rebuild all projections from event store.

        Args:
            event_store: EventStore instance
        """
        logger.info("Rebuilding all projections from event store")

        # Clear existing read models
        for table in [OfferReadModel, ConversationReadModel, CustomerReadModel]:
            self.session.query(table).delete()

        # Get all events ordered by time
        events = await event_store.get_events_by_type(
            event_type="%",  # All events
            limit=999999
        )

        # Replay events through all handlers
        for event in events:
            await self.handle_event(event)

        await self.session.commit()
        logger.info(f"Rebuilt {len(events)} events across all projections")
