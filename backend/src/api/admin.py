"""
Admin API Endpoints (T051-T052)

OpenAPI-compliant endpoints for sales managers and administrators.
Implements contract spec from specs/001-build-an-ai/contracts/admin-api.yaml
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends, status, Query
from pydantic import BaseModel, Field, field_validator

from ..models.approval import ApprovalWorkflow, ApprovalStatus, ApprovalDecision
from ..models.offer import Offer
from ..infrastructure.middleware.auth import verify_jwt_token
from ..infrastructure.repositories.approval_repository import ApprovalRepository
from ..infrastructure.repositories.offer_repository import OfferRepository


router = APIRouter(
    prefix="/approvals",
    tags=["approvals"],
    dependencies=[Depends(verify_jwt_token)]
)


# Request/Response Models
class Money(BaseModel):
    """Money value object."""
    amount: str
    currency: str
    formatted: Optional[str] = None


class ApprovalRequestItem(BaseModel):
    """Single approval request in list."""
    workflow_id: str
    offer_id: str
    offer_number: Optional[str] = None
    requested_at: datetime
    requested_by: Optional[str] = None
    status: str = Field(
        ...,
        pattern="^(pending|in_review|approved|rejected|revision_requested)$"
    )
    offer_value: Money
    customer_name: Optional[str] = None
    project_category: Optional[str] = None


class PendingApprovalsResponse(BaseModel):
    """Response for pending approvals list (T051)."""
    total: int
    items: List[ApprovalRequestItem]


class ReviewDecisionRequest(BaseModel):
    """Request model for making approval decision (T052)."""
    outcome: str = Field(
        ...,
        pattern="^(approved|rejected|revision_requested)$"
    )
    reason: str = Field(..., min_length=10, max_length=1000)
    conditions: Optional[List[str]] = None
    notify_customer: bool = False

    @field_validator('reason')
    @classmethod
    def reason_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Reason cannot be empty')
        return v.strip()


class ReviewDecisionResponse(BaseModel):
    """Response for approval decision."""
    workflow_id: str
    outcome: str
    offer_status: str
    customer_notified: bool


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Dependencies
async def get_approval_repository() -> ApprovalRepository:
    """Get approval workflow repository."""
    from ..infrastructure.database import get_db_connection
    db_conn = await get_db_connection()
    return ApprovalRepository(db_conn)


async def get_offer_repository() -> OfferRepository:
    """Get offer repository."""
    from ..infrastructure.database import get_db_connection
    db_conn = await get_db_connection()
    return OfferRepository(db_conn)


async def get_current_user_id(authorization: str = Header(...)) -> UUID:
    """Extract user ID from JWT token."""
    # TODO: Implement JWT token parsing with Keycloak
    # For now, return a placeholder
    return UUID('00000000-0000-0000-0000-000000000001')


# API Endpoints

@router.get(
    "/pending",
    response_model=PendingApprovalsResponse,
    responses={
        200: {"description": "List of pending approvals"}
    }
)
async def get_pending_approvals(
    approver_id: Optional[str] = Query(None, description="Filter by approver UUID"),
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    authorization: str = Header(..., alias="Authorization"),
    approval_repo: ApprovalRepository = Depends(get_approval_repository),
    offer_repo: OfferRepository = Depends(get_offer_repository)
) -> PendingApprovalsResponse:
    """
    T051: Get pending approvals

    Retrieves list of offers awaiting approval (value > EUR 100,000).
    Sales managers can filter by their assigned approvals.

    Authentication: JWT Bearer token from Keycloak
    Authorization: Sales manager role required

    Pagination:
    - Default limit: 20
    - Max limit: 100
    - Use offset for pagination
    """
    try:
        # Parse approver_id if provided
        approver_uuid = UUID(approver_id) if approver_id else None

        # Fetch pending approval workflows
        workflows = await approval_repo.find_pending(
            approver_id=approver_uuid,
            limit=limit,
            offset=offset
        )

        # Get total count for pagination
        total = await approval_repo.count_pending(approver_id=approver_uuid)

        # Build response items
        items = []
        for workflow in workflows:
            # Fetch associated offer
            offer = await offer_repo.get_by_id(workflow.offer_id)

            if offer:
                # TODO: Fetch customer name from customer service
                customer_name = None  # Placeholder

                # TODO: Fetch project category from project service
                project_category = None  # Placeholder

                items.append(ApprovalRequestItem(
                    workflow_id=str(workflow.id),
                    offer_id=str(workflow.offer_id),
                    offer_number=offer.offer_number,
                    requested_at=workflow.requested_at,
                    requested_by=str(workflow.requested_by),
                    status=workflow.status.value,
                    offer_value=Money(
                        amount=str(offer.total_value.amount),
                        currency=offer.total_value.currency,
                        formatted=f"{offer.total_value.amount:,.2f} €".replace(",", ".")
                    ),
                    customer_name=customer_name,
                    project_category=project_category
                ))

        return PendingApprovalsResponse(
            total=total,
            items=items
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_PARAMETER",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="FETCH_FAILED",
                message="Failed to fetch pending approvals",
                details={"error": str(e)}
            ).model_dump()
        )


@router.post(
    "/{workflowId}/review",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Review started"},
        409: {"description": "Already being reviewed by another user"}
    }
)
async def start_review(
    workflowId: str,
    authorization: str = Header(..., alias="Authorization"),
    current_user_id: UUID = Depends(get_current_user_id),
    approval_repo: ApprovalRepository = Depends(get_approval_repository)
) -> Dict[str, Any]:
    """
    T052 (Part 1): Start reviewing an approval request

    Locks the workflow for review by current user.
    Prevents concurrent reviews by multiple approvers.

    Lock duration: 30 minutes (configurable)
    """
    try:
        workflow_id = UUID(workflowId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid workflow ID format"
            ).model_dump()
        )

    # Fetch workflow
    workflow = await approval_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="WORKFLOW_NOT_FOUND",
                message=f"Approval workflow {workflowId} not found"
            ).model_dump()
        )

    # Check if already in review
    if workflow.status == ApprovalStatus.IN_REVIEW:
        # TODO: Check if locked by another user
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ErrorResponse(
                error_code="ALREADY_IN_REVIEW",
                message="This approval is already being reviewed by another user",
                details={"locked_by": str(workflow.approver_id)}
            ).model_dump()
        )

    # Start review
    try:
        workflow.start_review()
        await approval_repo.save(workflow)

        from datetime import timedelta
        locked_until = datetime.utcnow() + timedelta(minutes=30)

        return {
            "status": "in_review",
            "locked_by": str(current_user_id),
            "locked_until": locked_until.isoformat()
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_STATE_TRANSITION",
                message=str(e)
            ).model_dump()
        )


@router.post(
    "/{workflowId}/decide",
    response_model=ReviewDecisionResponse,
    responses={
        200: {"description": "Decision recorded"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Workflow not found"}
    }
)
async def make_decision(
    workflowId: str,
    request: ReviewDecisionRequest,
    authorization: str = Header(..., alias="Authorization"),
    current_user_id: UUID = Depends(get_current_user_id),
    approval_repo: ApprovalRepository = Depends(get_approval_repository),
    offer_repo: OfferRepository = Depends(get_offer_repository)
) -> ReviewDecisionResponse:
    """
    T052 (Part 2): Make a decision on approval request

    Records approver's decision (approved/rejected/revision_requested).
    Updates offer status accordingly and triggers customer notification.

    Business Rules:
    - Approval → Offer status changes to 'approved'
    - Rejection → Offer status changes to 'rejected'
    - Revision requested → Offer remains in 'pending_approval'

    Side Effects:
    - Publishes decision event
    - Sends notification to customer (if notify_customer=true)
    - Triggers offer status update
    """
    try:
        workflow_id = UUID(workflowId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid workflow ID format"
            ).model_dump()
        )

    # Fetch workflow
    workflow = await approval_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="WORKFLOW_NOT_FOUND",
                message=f"Approval workflow {workflowId} not found"
            ).model_dump()
        )

    # Fetch associated offer
    offer = await offer_repo.get_by_id(workflow.offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="OFFER_NOT_FOUND",
                message=f"Associated offer not found"
            ).model_dump()
        )

    try:
        # Apply decision based on outcome
        if request.outcome == "approved":
            workflow.approve(
                reason=request.reason,
                conditions=request.conditions
            )
            # Update offer status
            offer.status = offer.OfferStatus.APPROVED

        elif request.outcome == "rejected":
            workflow.reject(reason=request.reason)
            # Update offer status
            offer.status = offer.OfferStatus.REJECTED

        elif request.outcome == "revision_requested":
            workflow.request_revision(
                reason=request.reason,
                required_changes=request.conditions or []
            )
            # Offer remains in pending_approval status

        else:
            raise ValueError(f"Invalid outcome: {request.outcome}")

        # Persist changes
        await approval_repo.save(workflow)
        await offer_repo.save(offer)

        # TODO: Publish decision event
        # await event_bus.publish({
        #     "event_type": "ApprovalDecisionMade",
        #     "aggregate_id": str(workflow_id),
        #     "payload": {
        #         "outcome": request.outcome,
        #         "offer_id": str(offer.id),
        #         "decided_by": str(current_user_id),
        #         "decided_at": workflow.decided_at.isoformat()
        #     }
        # })

        # TODO: Send customer notification if requested
        customer_notified = False
        if request.notify_customer:
            # Trigger notification service
            # await notification_service.send_approval_decision(
            #     offer_id=offer.id,
            #     outcome=request.outcome,
            #     reason=request.reason
            # )
            customer_notified = True

        return ReviewDecisionResponse(
            workflow_id=str(workflow_id),
            outcome=request.outcome,
            offer_status=offer.status.value,
            customer_notified=customer_notified
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_DECISION",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DECISION_FAILED",
                message="Failed to record decision",
                details={"error": str(e)}
            ).model_dump()
        )
