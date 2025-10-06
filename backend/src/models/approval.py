"""ApprovalWorkflow aggregate root model for high-value offer approvals."""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ApprovalStatus(Enum):
    """
    Approval workflow status.

    State transitions:
    PENDING → IN_REVIEW → (APPROVED | REJECTED | REVISION_REQUESTED)
    REVISION_REQUESTED → PENDING (after modifications)
    """
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class Comment(BaseModel):
    """
    Comment in approval workflow.

    Allows approvers and requesters to discuss the offer
    and document their reasoning.
    """
    id: UUID = Field(default_factory=uuid4)
    author_id: UUID
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: str

    class Config:
        frozen = True


class OfferModification(BaseModel):
    """
    Tracks modifications to an offer during approval process.

    Uses JSONPath for field identification to support nested
    structure changes (e.g., work package modifications).
    """
    field_path: str  # JSONPath to modified field (e.g., "$.work_packages[0].estimated_hours.likely")
    old_value: Any
    new_value: Any
    modified_by: UUID
    modified_at: datetime = Field(default_factory=datetime.utcnow)
    reason: str

    class Config:
        frozen = True


class ApprovalDecision(BaseModel):
    """
    Final decision for an approval workflow.

    Contains the outcome, reasoning, and any conditions
    attached to the approval.
    """
    outcome: ApprovalStatus
    reason: str
    conditions: List[str] = Field(default_factory=list)

    class Config:
        frozen = True

    def __init__(self, **data):
        """Validate that outcome is a terminal status."""
        super().__init__(**data)
        if self.outcome not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.REVISION_REQUESTED]:
            raise ValueError(f"Decision outcome must be terminal status, got: {self.outcome}")


class ApprovalWorkflow(BaseModel):
    """
    ApprovalWorkflow aggregate root.

    Manages the approval process for high-value offers (>EUR 100,000).
    Enforces business rules around approver authorization, tracks all
    modifications and comments, and maintains complete audit trail.

    Invariants:
    - Only one active workflow per offer
    - Approver cannot be the requester
    - Modifications trigger new offer version
    - Decision must be terminal status (APPROVED, REJECTED, or REVISION_REQUESTED)

    State transitions:
    PENDING → IN_REVIEW → (APPROVED | REJECTED | REVISION_REQUESTED)
    REVISION_REQUESTED → PENDING (after offer modifications)
    """

    id: UUID = Field(default_factory=uuid4)
    offer_id: UUID
    requested_by: UUID
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    approver_id: UUID
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision: Optional[ApprovalDecision] = None
    decided_at: Optional[datetime] = None
    comments: List[Comment] = Field(default_factory=list)
    modifications: List[OfferModification] = Field(default_factory=list)

    class Config:
        from_attributes = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        """Validate that approver is not the requester."""
        super().__init__(**data)
        if self.approver_id == self.requested_by:
            raise ValueError("Approver cannot be the same as requester")

    def start_review(self) -> None:
        """
        Transition workflow to IN_REVIEW status.

        Called when an approver begins reviewing the offer.

        Raises:
            ValueError: If workflow is not in PENDING status
        """
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot start review from status: {self.status}")
        self.status = ApprovalStatus.IN_REVIEW

    def add_comment(self, author_id: UUID, content: str) -> Comment:
        """
        Add a comment to the approval workflow.

        Args:
            author_id: UUID of the comment author
            content: Comment text

        Returns:
            The created Comment object

        Raises:
            ValueError: If workflow is already decided
        """
        if self.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            raise ValueError(f"Cannot add comments to {self.status} workflow")

        comment = Comment(author_id=author_id, content=content)
        self.comments.append(comment)
        return comment

    def add_modification(
        self,
        field_path: str,
        old_value: Any,
        new_value: Any,
        modified_by: UUID,
        reason: str
    ) -> OfferModification:
        """
        Record a modification to the offer during approval.

        Args:
            field_path: JSONPath to the modified field
            old_value: Previous value
            new_value: New value
            modified_by: UUID of user making modification
            reason: Explanation for the change

        Returns:
            The created OfferModification object

        Raises:
            ValueError: If workflow is already approved or rejected
        """
        if self.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]:
            raise ValueError(f"Cannot modify offer in {self.status} workflow")

        modification = OfferModification(
            field_path=field_path,
            old_value=old_value,
            new_value=new_value,
            modified_by=modified_by,
            reason=reason
        )
        self.modifications.append(modification)
        return modification

    def approve(
        self,
        reason: str,
        conditions: Optional[List[str]] = None
    ) -> None:
        """
        Approve the offer.

        Args:
            reason: Explanation for approval
            conditions: Optional list of conditions attached to approval

        Raises:
            ValueError: If workflow is not in IN_REVIEW status
        """
        if self.status != ApprovalStatus.IN_REVIEW:
            raise ValueError(f"Cannot approve from status: {self.status}")

        self.status = ApprovalStatus.APPROVED
        self.decision = ApprovalDecision(
            outcome=ApprovalStatus.APPROVED,
            reason=reason,
            conditions=conditions or []
        )
        self.decided_at = datetime.utcnow()

    def reject(self, reason: str) -> None:
        """
        Reject the offer.

        Args:
            reason: Explanation for rejection

        Raises:
            ValueError: If workflow is not in IN_REVIEW status
        """
        if self.status != ApprovalStatus.IN_REVIEW:
            raise ValueError(f"Cannot reject from status: {self.status}")

        self.status = ApprovalStatus.REJECTED
        self.decision = ApprovalDecision(
            outcome=ApprovalStatus.REJECTED,
            reason=reason,
            conditions=[]
        )
        self.decided_at = datetime.utcnow()

    def request_revision(self, reason: str, required_changes: List[str]) -> None:
        """
        Request revisions to the offer.

        Args:
            reason: Explanation for revision request
            required_changes: List of specific changes needed

        Raises:
            ValueError: If workflow is not in IN_REVIEW status
        """
        if self.status != ApprovalStatus.IN_REVIEW:
            raise ValueError(f"Cannot request revision from status: {self.status}")

        self.status = ApprovalStatus.REVISION_REQUESTED
        self.decision = ApprovalDecision(
            outcome=ApprovalStatus.REVISION_REQUESTED,
            reason=reason,
            conditions=required_changes
        )
        self.decided_at = datetime.utcnow()

    def reset_after_revision(self) -> None:
        """
        Reset workflow to PENDING after offer has been revised.

        Called when the requester has made requested changes and
        resubmits for approval.

        Raises:
            ValueError: If workflow is not in REVISION_REQUESTED status
        """
        if self.status != ApprovalStatus.REVISION_REQUESTED:
            raise ValueError(f"Cannot reset from status: {self.status}")

        self.status = ApprovalStatus.PENDING
        # Decision remains for audit trail but workflow is reopened
        self.decided_at = None

    def is_terminal(self) -> bool:
        """
        Check if workflow is in a terminal state.

        Returns:
            True if workflow is APPROVED or REJECTED (cannot transition further)
        """
        return self.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]

    def can_modify(self) -> bool:
        """
        Check if offer can be modified in current workflow state.

        Returns:
            True if modifications are allowed (not yet approved/rejected)
        """
        return self.status not in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED]
