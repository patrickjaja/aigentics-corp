"""Approval workflow repository implementation."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ...models.approval import (
    ApprovalWorkflow,
    ApprovalStatus,
    ApprovalDecision,
    Comment,
    OfferModification,
)
from ..events.schema import DomainEvent
from .base import Repository


class ApprovalWorkflowRepository(Repository[ApprovalWorkflow]):
    """Repository for ApprovalWorkflow aggregate."""

    def _reconstruct_from_events(self, events: List[DomainEvent]) -> ApprovalWorkflow:
        """Reconstruct approval workflow from events."""
        workflow_data = {}
        comments = []
        modifications = []

        for event in events:
            event_type = event.event_type
            payload = event.payload

            if event_type == "WorkflowInitiated":
                workflow_data = {
                    "id": event.aggregate_id,
                    "offer_id": UUID(payload["offer_id"]),
                    "requested_by": UUID(payload["requested_by"]),
                    "requested_at": event.occurred_at,
                    "approver_id": UUID(payload["approver_id"]),
                    "status": ApprovalStatus.PENDING,
                    "decision": None,
                    "decided_at": None,
                }

            elif event_type == "ReviewStarted":
                workflow_data["status"] = ApprovalStatus.IN_REVIEW

            elif event_type == "CommentAdded":
                comment = Comment(
                    id=uuid4(),
                    author_id=event.actor_id or UUID(payload["author_id"]),
                    timestamp=event.occurred_at,
                    content=payload["content"],
                )
                comments.append(comment)

            elif event_type == "ModificationMade":
                modification = OfferModification(
                    field_path=payload["field_path"],
                    old_value=payload["old_value"],
                    new_value=payload["new_value"],
                    modified_by=event.actor_id or UUID(payload["modified_by"]),
                    modified_at=event.occurred_at,
                    reason=payload.get("reason", ""),
                )
                modifications.append(modification)

            elif event_type == "RevisionRequested":
                workflow_data["status"] = ApprovalStatus.REVISION_REQUESTED

            elif event_type == "DecisionMade":
                outcome = ApprovalStatus(payload["outcome"])
                workflow_data["decision"] = ApprovalDecision(
                    outcome=outcome,
                    reason=payload.get("reason", ""),
                    conditions=payload.get("conditions", []),
                )
                workflow_data["decided_at"] = event.occurred_at
                workflow_data["status"] = outcome

        workflow_data["comments"] = comments
        workflow_data["modifications"] = modifications

        return ApprovalWorkflow(**workflow_data)

    def _get_uncommitted_events(self, aggregate: ApprovalWorkflow) -> List[DomainEvent]:
        """Get uncommitted events from approval workflow."""
        return getattr(aggregate, "_uncommitted_events", [])

    def _mark_events_committed(self, aggregate: ApprovalWorkflow) -> None:
        """Mark approval workflow events as committed."""
        if hasattr(aggregate, "_uncommitted_events"):
            aggregate._uncommitted_events = []

    def _get_aggregate_id(self, aggregate: ApprovalWorkflow) -> UUID:
        """Get approval workflow ID."""
        return aggregate.id

    def _create_deletion_event(self, aggregate_id: UUID) -> DomainEvent:
        """Create approval workflow deletion event."""
        return DomainEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_type="ApprovalWorkflow",
            event_type="WorkflowDeleted",
            event_version=1,
            occurred_at=datetime.utcnow(),
            correlation_id=uuid4(),
            causation_id=None,
            actor_id=None,
            metadata={},
            payload={"deleted_at": datetime.utcnow().isoformat()},
        )
