"""Customer repository implementation."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ...models.customer import Customer, GDPRConsent, ConsentPurpose
from ...models.value_objects import EmailAddress, LanguageCode, PhoneNumber
from ..events.schema import DomainEvent
from .base import Repository


class CustomerRepository(Repository[Customer]):
    """Repository for Customer aggregate."""

    def _reconstruct_from_events(self, events: List[DomainEvent]) -> Customer:
        """Reconstruct customer from events."""
        customer_data = {}
        gdpr_consent_data = None

        for event in events:
            event_type = event.event_type
            payload = event.payload

            if event_type == "CustomerCreated":
                customer_data = {
                    "id": event.aggregate_id,
                    "external_id": payload["external_id"],
                    "company_name": payload["company_name"],
                    "contact_person": payload["contact_person"],
                    "email": EmailAddress(value=payload["email"]),
                    "phone": PhoneNumber(full_number=payload["phone"]) if payload.get("phone") else None,
                    "language_preference": LanguageCode(code=payload.get("language_preference", "en")),
                    "created_at": event.occurred_at,
                    "updated_at": event.occurred_at,
                    "deletion_requested_at": None,
                }

            elif event_type == "ConsentGiven":
                gdpr_consent_data = {
                    "given_at": event.occurred_at,
                    "ip_address": payload["ip_address"],
                    "consent_text_version": payload["consent_text_version"],
                    "purposes": [ConsentPurpose(p) for p in payload["purposes"]],
                    "withdrawn_at": None,
                }

            elif event_type == "ConsentWithdrawn":
                if gdpr_consent_data:
                    gdpr_consent_data["withdrawn_at"] = event.occurred_at

            elif event_type == "CustomerUpdated":
                if "company_name" in payload:
                    customer_data["company_name"] = payload["company_name"]
                if "contact_person" in payload:
                    customer_data["contact_person"] = payload["contact_person"]
                if "email" in payload:
                    customer_data["email"] = EmailAddress(value=payload["email"])
                if "phone" in payload:
                    customer_data["phone"] = PhoneNumber(full_number=payload["phone"]) if payload["phone"] else None
                customer_data["updated_at"] = event.occurred_at

            elif event_type == "DeletionRequested":
                customer_data["deletion_requested_at"] = event.occurred_at

        # Create GDPR consent object
        if gdpr_consent_data:
            customer_data["gdpr_consent"] = GDPRConsent(**gdpr_consent_data)

        return Customer(**customer_data)

    def _get_uncommitted_events(self, aggregate: Customer) -> List[DomainEvent]:
        """Get uncommitted events from customer."""
        # In a real implementation, the aggregate would track uncommitted events
        # For now, return empty list (events should be created by the aggregate)
        return getattr(aggregate, "_uncommitted_events", [])

    def _mark_events_committed(self, aggregate: Customer) -> None:
        """Mark customer events as committed."""
        if hasattr(aggregate, "_uncommitted_events"):
            aggregate._uncommitted_events = []

    def _get_aggregate_id(self, aggregate: Customer) -> UUID:
        """Get customer ID."""
        return aggregate.id

    def _create_deletion_event(self, aggregate_id: UUID) -> DomainEvent:
        """Create customer deletion event."""
        return DomainEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_type="Customer",
            event_type="CustomerDeleted",
            event_version=1,
            occurred_at=datetime.utcnow(),
            correlation_id=uuid4(),
            causation_id=None,
            actor_id=None,
            metadata={},
            payload={"deleted_at": datetime.utcnow().isoformat()},
        )
