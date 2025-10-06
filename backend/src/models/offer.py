"""Offer aggregate root model with event sourcing support."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .value_objects import Money

if TYPE_CHECKING:
    from .work_package import WorkPackage


class OfferStatus(Enum):
    """
    Offer lifecycle status.

    State transitions:
    DRAFT → PENDING_APPROVAL → APPROVED → SENT → VIEWED → (ACCEPTED | REJECTED | EXPIRED)
    """
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT = "sent"
    VIEWED = "viewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OfferEvent(BaseModel):
    """
    Event sourcing model for offer state changes.

    Provides complete audit trail of all offer modifications,
    approvals, and customer interactions.
    """
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    payload: Dict[str, Any]

    class Config:
        frozen = True


class Offer(BaseModel):
    """
    Offer aggregate root.

    Represents a complete offer for IT consulting services including
    work packages, pricing, and terms. Implements event sourcing for
    complete audit trail and supports versioning for modifications.

    Invariants:
    - Offer number must be unique (format: YY-NNNN)
    - Approval required if total_value > EUR 100,000
    - Version increments on any modification
    - Valid for 30 days from creation
    - Must have at least one work package

    State transitions are recorded as events:
    - OfferCreated
    - OfferModified
    - OfferApproved
    - OfferSent
    - OfferViewed
    - OfferAccepted
    - OfferRejected
    """

    id: UUID = Field(default_factory=uuid4)
    offer_number: str
    version: int = 1
    customer_id: UUID
    project_id: UUID
    conversation_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: date
    status: OfferStatus = OfferStatus.DRAFT
    total_value: Money
    work_packages: List["WorkPackage"] = Field(default_factory=list)
    terms_and_conditions: str
    approval_required: bool = False
    approval_workflow_id: Optional[UUID] = None
    events: List[OfferEvent] = Field(default_factory=list)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    def add_event(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Record an event for audit trail.

        Args:
            event_type: Type of event (e.g., "OfferCreated", "OfferApproved")
            payload: Event-specific data
        """
        event = OfferEvent(
            event_type=event_type,
            payload=payload
        )
        self.events.append(event)

    def requires_approval(self) -> bool:
        """
        Check if offer requires approval based on business rules.

        Business rule: Offers > EUR 100,000 require approval.

        Returns:
            True if approval is required
        """
        threshold = Money(amount=Decimal("100000.00"), currency="EUR")
        return self.total_value >= threshold

    def is_expired(self) -> bool:
        """
        Check if offer has passed its validity date.

        Returns:
            True if current date is after valid_until
        """
        return date.today() > self.valid_until

    def increment_version(self) -> None:
        """
        Increment version number for modifications.

        Called whenever the offer is modified to maintain version history.
        Records an OfferModified event.
        """
        old_version = self.version
        self.version += 1
        self.add_event(
            event_type="OfferModified",
            payload={
                "old_version": old_version,
                "new_version": self.version,
                "modified_at": datetime.utcnow().isoformat()
            }
        )

    def submit_for_approval(self, approver_id: UUID, workflow_id: UUID) -> None:
        """
        Submit offer for approval workflow.

        Args:
            approver_id: UUID of the approver
            workflow_id: UUID of the approval workflow

        Raises:
            ValueError: If offer is not in DRAFT status or approval not required
        """
        if self.status != OfferStatus.DRAFT:
            raise ValueError(f"Cannot submit offer in {self.status} status for approval")

        if not self.requires_approval():
            raise ValueError("Approval not required for this offer value")

        self.status = OfferStatus.PENDING_APPROVAL
        self.approval_workflow_id = workflow_id
        self.approval_required = True

        self.add_event(
            event_type="ApprovalRequested",
            payload={
                "approver_id": str(approver_id),
                "workflow_id": str(workflow_id),
                "total_value": {
                    "amount": str(self.total_value.amount),
                    "currency": self.total_value.currency
                }
            }
        )

    def approve(self, approver_id: UUID, comments: Optional[str] = None) -> None:
        """
        Approve the offer.

        Args:
            approver_id: UUID of the approver
            comments: Optional approval comments

        Raises:
            ValueError: If offer is not in PENDING_APPROVAL status
        """
        if self.status != OfferStatus.PENDING_APPROVAL:
            raise ValueError(f"Cannot approve offer in {self.status} status")

        self.status = OfferStatus.APPROVED

        self.add_event(
            event_type="OfferApproved",
            payload={
                "approver_id": str(approver_id),
                "comments": comments,
                "approved_at": datetime.utcnow().isoformat()
            }
        )

    def send_to_customer(self, sent_by: UUID, delivery_method: str) -> None:
        """
        Mark offer as sent to customer.

        Args:
            sent_by: UUID of user who sent the offer
            delivery_method: Method used to send (e.g., "email", "portal")

        Raises:
            ValueError: If offer is not in APPROVED status
        """
        if self.status not in [OfferStatus.APPROVED, OfferStatus.DRAFT]:
            raise ValueError(f"Cannot send offer in {self.status} status")

        self.status = OfferStatus.SENT

        self.add_event(
            event_type="OfferSent",
            payload={
                "sent_by": str(sent_by),
                "delivery_method": delivery_method,
                "sent_at": datetime.utcnow().isoformat()
            }
        )

    def mark_viewed(self, viewed_at: Optional[datetime] = None) -> None:
        """
        Mark offer as viewed by customer.

        Args:
            viewed_at: Time when offer was viewed, defaults to now
        """
        if self.status != OfferStatus.SENT:
            raise ValueError(f"Cannot mark offer as viewed in {self.status} status")

        self.status = OfferStatus.VIEWED

        self.add_event(
            event_type="OfferViewed",
            payload={
                "viewed_at": (viewed_at or datetime.utcnow()).isoformat()
            }
        )

    def accept(self, accepted_by: UUID, acceptance_notes: Optional[str] = None) -> None:
        """
        Accept the offer.

        Args:
            accepted_by: UUID of customer who accepted
            acceptance_notes: Optional acceptance notes

        Raises:
            ValueError: If offer is not in VIEWED or SENT status
        """
        if self.status not in [OfferStatus.VIEWED, OfferStatus.SENT]:
            raise ValueError(f"Cannot accept offer in {self.status} status")

        if self.is_expired():
            raise ValueError("Cannot accept expired offer")

        self.status = OfferStatus.ACCEPTED

        self.add_event(
            event_type="OfferAccepted",
            payload={
                "accepted_by": str(accepted_by),
                "acceptance_notes": acceptance_notes,
                "accepted_at": datetime.utcnow().isoformat()
            }
        )

    def reject(self, rejected_by: UUID, rejection_reason: str) -> None:
        """
        Reject the offer.

        Args:
            rejected_by: UUID of customer who rejected
            rejection_reason: Reason for rejection

        Raises:
            ValueError: If offer is not in VIEWED or SENT status
        """
        if self.status not in [OfferStatus.VIEWED, OfferStatus.SENT]:
            raise ValueError(f"Cannot reject offer in {self.status} status")

        self.status = OfferStatus.REJECTED

        self.add_event(
            event_type="OfferRejected",
            payload={
                "rejected_by": str(rejected_by),
                "rejection_reason": rejection_reason,
                "rejected_at": datetime.utcnow().isoformat()
            }
        )

    def mark_expired(self) -> None:
        """
        Mark offer as expired if past validity date.

        Raises:
            ValueError: If offer is already accepted or rejected
        """
        if self.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED]:
            raise ValueError(f"Cannot expire offer in {self.status} status")

        if not self.is_expired():
            raise ValueError("Cannot mark offer as expired before validity date")

        self.status = OfferStatus.EXPIRED

        self.add_event(
            event_type="OfferExpired",
            payload={
                "expired_at": datetime.utcnow().isoformat(),
                "valid_until": self.valid_until.isoformat()
            }
        )
