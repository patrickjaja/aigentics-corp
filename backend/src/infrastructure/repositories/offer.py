"""Offer repository implementation."""

from datetime import datetime
from decimal import Decimal
from typing import List
from uuid import UUID, uuid4

from ...models.offer import Offer, OfferStatus, Money
from ...models.work_package import WorkPackage, Deliverable, EstimatedHours
from ..events.schema import DomainEvent
from .base import Repository


class OfferRepository(Repository[Offer]):
    """Repository for Offer aggregate."""

    def _reconstruct_from_events(self, events: List[DomainEvent]) -> Offer:
        """Reconstruct offer from events."""
        offer_data = {}
        work_packages = []
        offer_events = []

        for event in events:
            event_type = event.event_type
            payload = event.payload
            offer_events.append(event)

            if event_type == "OfferCreated":
                offer_data = {
                    "id": event.aggregate_id,
                    "offer_number": payload["offer_number"],
                    "version": payload.get("version", 1),
                    "customer_id": UUID(payload["customer_id"]),
                    "project_id": UUID(payload["project_id"]),
                    "conversation_id": UUID(payload["conversation_id"]),
                    "created_at": event.occurred_at,
                    "valid_until": datetime.fromisoformat(payload["valid_until"]),
                    "status": OfferStatus(payload.get("status", "DRAFT")),
                    "total_value": Money(
                        amount=Decimal(str(payload["total_value"])),
                        currency=payload.get("currency", "EUR")
                    ),
                    "terms_and_conditions": payload.get("terms_and_conditions", ""),
                    "approval_required": payload.get("approval_required", False),
                    "approval_workflow_id": UUID(payload["approval_workflow_id"]) if payload.get("approval_workflow_id") else None,
                }

                # Parse work packages
                for wp_data in payload.get("work_packages", []):
                    work_package = self._parse_work_package(wp_data, event.aggregate_id)
                    work_packages.append(work_package)

            elif event_type == "OfferModified":
                offer_data["version"] = payload.get("version", offer_data.get("version", 1) + 1)
                if "total_value" in payload:
                    offer_data["total_value"] = Money(
                        amount=Decimal(str(payload["total_value"])),
                        currency=payload.get("currency", "EUR")
                    )
                if "work_packages" in payload:
                    work_packages = []
                    for wp_data in payload["work_packages"]:
                        work_package = self._parse_work_package(wp_data, event.aggregate_id)
                        work_packages.append(work_package)

            elif event_type == "OfferApproved":
                offer_data["status"] = OfferStatus.APPROVED
                offer_data["approval_workflow_id"] = UUID(payload["approval_workflow_id"]) if payload.get("approval_workflow_id") else None

            elif event_type == "OfferSent":
                offer_data["status"] = OfferStatus.SENT

            elif event_type == "OfferViewed":
                offer_data["status"] = OfferStatus.VIEWED

            elif event_type == "OfferAccepted":
                offer_data["status"] = OfferStatus.ACCEPTED

            elif event_type == "OfferRejected":
                offer_data["status"] = OfferStatus.REJECTED

            elif event_type == "OfferExpired":
                offer_data["status"] = OfferStatus.EXPIRED

            elif event_type == "ApprovalRequested":
                offer_data["status"] = OfferStatus.PENDING_APPROVAL
                offer_data["approval_workflow_id"] = UUID(payload["approval_workflow_id"])

        offer_data["work_packages"] = work_packages
        offer_data["events"] = offer_events

        return Offer(**offer_data)

    def _parse_work_package(self, wp_data: dict, offer_id: UUID) -> WorkPackage:
        """Parse work package from event payload."""
        deliverables = [
            Deliverable(
                name=d.get("name", ""),
                description=d.get("description", ""),
                acceptance_criteria=d.get("acceptance_criteria", [])
            )
            for d in wp_data.get("deliverables", [])
        ]

        estimated_hours_data = wp_data.get("estimated_hours", {})
        estimated_hours = EstimatedHours(
            optimistic=Decimal(str(estimated_hours_data.get("optimistic", 0))),
            likely=Decimal(str(estimated_hours_data.get("likely", 0))),
            pessimistic=Decimal(str(estimated_hours_data.get("pessimistic", 0))),
            confidence=float(estimated_hours_data.get("confidence", 0.5)),
        )

        hourly_rate = Money(
            amount=Decimal(str(wp_data.get("hourly_rate", {}).get("amount", 0))),
            currency=wp_data.get("hourly_rate", {}).get("currency", "EUR")
        )

        total_cost = Money(
            amount=Decimal(str(wp_data.get("total_cost", {}).get("amount", 0))),
            currency=wp_data.get("total_cost", {}).get("currency", "EUR")
        )

        return WorkPackage(
            id=UUID(wp_data["id"]) if wp_data.get("id") else uuid4(),
            offer_id=offer_id,
            name=wp_data.get("name", ""),
            description=wp_data.get("description", ""),
            deliverables=deliverables,
            estimated_hours=estimated_hours,
            hourly_rate=hourly_rate,
            total_cost=total_cost,
            dependencies=[UUID(dep) for dep in wp_data.get("dependencies", [])],
            order=wp_data.get("order", 0),
        )

    def _get_uncommitted_events(self, aggregate: Offer) -> List[DomainEvent]:
        """Get uncommitted events from offer."""
        return getattr(aggregate, "_uncommitted_events", [])

    def _mark_events_committed(self, aggregate: Offer) -> None:
        """Mark offer events as committed."""
        if hasattr(aggregate, "_uncommitted_events"):
            aggregate._uncommitted_events = []

    def _get_aggregate_id(self, aggregate: Offer) -> UUID:
        """Get offer ID."""
        return aggregate.id

    def _create_deletion_event(self, aggregate_id: UUID) -> DomainEvent:
        """Create offer deletion event."""
        return DomainEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_type="Offer",
            event_type="OfferDeleted",
            event_version=1,
            occurred_at=datetime.utcnow(),
            correlation_id=uuid4(),
            causation_id=None,
            actor_id=None,
            metadata={},
            payload={"deleted_at": datetime.utcnow().isoformat()},
        )
