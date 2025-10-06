"""
Offer API Endpoints (T046-T048)

OpenAPI-compliant endpoints for offer generation and management.
Implements contract spec from specs/001-build-an-ai/contracts/offer-api.yaml
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Header, Depends, status, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from ..models.offer import OfferStatus
from ..services.offer.main import OfferService, get_offer_service
from ..infrastructure.middleware.auth import verify_api_key
from ..infrastructure.middleware.rate_limit import check_rate_limit


router = APIRouter(
    prefix="/offers",
    tags=["offers"],
    dependencies=[Depends(verify_api_key)]
)


# Request/Response Models
class Money(BaseModel):
    """Money value object."""
    amount: str = Field(..., pattern=r"^[0-9]+\.[0-9]{2}$")
    currency: str = Field(default="EUR", pattern="^(EUR|CHF)$")
    formatted: Optional[str] = None

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: str) -> str:
        try:
            Decimal(v)
        except Exception:
            raise ValueError("Invalid amount format")
        return v


class EstimatedHours(BaseModel):
    """Estimated hours with PERT calculation."""
    optimistic: Optional[float] = None
    likely: Optional[float] = None
    pessimistic: Optional[float] = None
    expected: float = Field(..., description="Calculated using PERT formula")
    confidence: float = Field(..., ge=0.0, le=1.0)


class Deliverable(BaseModel):
    """Work package deliverable."""
    name: str
    description: str
    acceptance_criteria: Optional[List[str]] = None


class WorkPackage(BaseModel):
    """Work package with deliverables and pricing."""
    id: str
    name: str
    description: str
    deliverables: List[Deliverable]
    estimated_hours: EstimatedHours
    hourly_rate: Money
    total_cost: Money
    dependencies: Optional[List[str]] = None


class ProjectSummary(BaseModel):
    """Project summary information."""
    name: Optional[str] = None
    category: Optional[str] = Field(
        None,
        pattern="^(software_development|consulting|infrastructure|mixed)$"
    )
    requirements_count: Optional[int] = None
    timeline: Optional[str] = None
    budget_range: Optional[str] = None


class GenerateOfferRequest(BaseModel):
    """Request model for offer generation (T046)."""
    project_id: str = Field(..., description="Project UUID")
    conversation_id: str = Field(..., description="Conversation UUID")
    customer_id: Optional[str] = Field(None, description="Customer UUID if exists")

    @field_validator('project_id', 'conversation_id', 'customer_id')
    @classmethod
    def validate_uuid(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        try:
            UUID(v)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {v}")
        return v


class OfferResponse(BaseModel):
    """Response model for offer creation (T046)."""
    offer_id: str
    offer_number: str = Field(..., pattern=r"^[0-9]{2}-[0-9]{4}$")
    status: str = Field(
        ...,
        pattern="^(draft|pending_approval|approved|sent|viewed|accepted|rejected|expired)$"
    )
    total_value: Money
    approval_required: bool
    approval_workflow_id: Optional[str] = None
    created_at: datetime
    valid_until: str  # ISO date


class OfferDetails(BaseModel):
    """Detailed offer information (T047)."""
    offer_id: str
    offer_number: str
    status: str
    total_value: Money
    approval_required: bool
    approval_workflow_id: Optional[str] = None
    created_at: datetime
    valid_until: str
    version: int = Field(..., ge=1)
    work_packages: List[WorkPackage]
    terms_and_conditions: Optional[str] = None
    project_details: Optional[ProjectSummary] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# API Endpoints

@router.post(
    "",
    response_model=OfferResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Offer generated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Project or conversation not found"},
        422: {"model": ErrorResponse, "description": "Insufficient information for offer generation"},
        503: {"model": ErrorResponse, "description": "Service timeout (30s exceeded)"}
    }
)
async def generate_offer(
    request: GenerateOfferRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: OfferService = Depends(get_offer_service)
) -> OfferResponse:
    """
    T046: Generate a new offer

    Creates an offer from project requirements gathered during conversation.
    Automatically triggers approval workflow if total value > EUR 100,000.

    Processing timeout: 30 seconds
    """
    import time
    start_time = time.time()

    try:
        project_id = UUID(request.project_id)
        conversation_id = UUID(request.conversation_id)
        customer_id = UUID(request.customer_id) if request.customer_id else None

        # TODO: Validate that conversation has sufficient information
        # This would check completion_percentage >= 80

        # Generate offer (with 30s timeout)
        offer = await service.create_offer(
            project_id=project_id,
            conversation_id=conversation_id,
            customer_id=customer_id or UUID('00000000-0000-0000-0000-000000000000')  # Placeholder
        )

        processing_time = int((time.time() - start_time) * 1000)  # milliseconds

        if processing_time > 30000:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=ErrorResponse(
                    error_code="SERVICE_TIMEOUT",
                    message="Offer generation exceeded 30 second timeout",
                    details={"processing_time_ms": processing_time}
                ).model_dump()
            )

        return OfferResponse(
            offer_id=str(offer.id),
            offer_number=offer.offer_number,
            status=offer.status.value,
            total_value=Money(
                amount=f"{offer.total_value.amount:.2f}",
                currency=offer.total_value.currency,
                formatted=f"{offer.total_value.amount:,.2f} €".replace(",", ".")
            ),
            approval_required=offer.approval_required,
            approval_workflow_id=str(offer.approval_workflow_id) if offer.approval_workflow_id else None,
            created_at=offer.created_at,
            valid_until=offer.valid_until.isoformat()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_REQUEST",
                message=str(e)
            ).model_dump()
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error_code="INSUFFICIENT_INFORMATION",
                message="Cannot generate offer with current information",
                details={"error": str(e)}
            ).model_dump()
        )


@router.get(
    "/{offerId}",
    response_model=OfferDetails,
    responses={
        200: {"description": "Offer details"},
        404: {"model": ErrorResponse, "description": "Offer not found"}
    }
)
async def get_offer(
    offerId: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: OfferService = Depends(get_offer_service)
) -> OfferDetails:
    """
    T047: Get offer details

    Retrieves complete offer information including:
    - Work packages with deliverables
    - Pricing breakdown
    - Terms and conditions
    - Version history
    """
    try:
        offer_id = UUID(offerId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid offer ID format"
            ).model_dump()
        )

    offer = await service.get_offer(offer_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="OFFER_NOT_FOUND",
                message=f"Offer {offerId} not found"
            ).model_dump()
        )

    # Convert work packages
    work_packages = [
        WorkPackage(
            id=str(wp.id),
            name=wp.name,
            description=wp.description,
            deliverables=[
                Deliverable(
                    name=d.name,
                    description=d.description,
                    acceptance_criteria=d.acceptance_criteria
                )
                for d in wp.deliverables
            ],
            estimated_hours=EstimatedHours(
                optimistic=wp.estimated_hours.optimistic,
                likely=wp.estimated_hours.likely,
                pessimistic=wp.estimated_hours.pessimistic,
                expected=wp.estimated_hours.expected,
                confidence=wp.estimated_hours.confidence
            ),
            hourly_rate=Money(
                amount=f"{wp.hourly_rate.amount:.2f}",
                currency=wp.hourly_rate.currency,
                formatted=f"{wp.hourly_rate.amount:,.2f} €".replace(",", ".")
            ),
            total_cost=Money(
                amount=f"{wp.total_cost.amount:.2f}",
                currency=wp.total_cost.currency,
                formatted=f"{wp.total_cost.amount:,.2f} €".replace(",", ".")
            ),
            dependencies=[str(dep) for dep in wp.dependencies] if wp.dependencies else None
        )
        for wp in offer.work_packages
    ]

    return OfferDetails(
        offer_id=str(offer.id),
        offer_number=offer.offer_number,
        status=offer.status.value,
        total_value=Money(
            amount=f"{offer.total_value.amount:.2f}",
            currency=offer.total_value.currency,
            formatted=f"{offer.total_value.amount:,.2f} €".replace(",", ".")
        ),
        approval_required=offer.approval_required,
        approval_workflow_id=str(offer.approval_workflow_id) if offer.approval_workflow_id else None,
        created_at=offer.created_at,
        valid_until=offer.valid_until.isoformat(),
        version=offer.version,
        work_packages=work_packages,
        terms_and_conditions=offer.terms_and_conditions,
        project_details=None  # TODO: Fetch from project service
    )


@router.post(
    "/{offerId}/download",
    responses={
        200: {
            "description": "PDF document",
            "content": {"application/pdf": {}}
        },
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Offer not found"},
        422: {"model": ErrorResponse, "description": "GDPR consent not provided"}
    }
)
async def download_offer(
    offerId: str,
    customer_data: Dict[str, Any],
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: OfferService = Depends(get_offer_service)
) -> Response:
    """
    T048: Download offer as PDF

    Generates PDF with customer information included.
    Requires GDPR consent to be provided in customer_data.

    Returns PDF with Content-Disposition header for download.
    """
    try:
        offer_id = UUID(offerId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid offer ID format"
            ).model_dump()
        )

    # Validate GDPR consent
    gdpr_consent = customer_data.get("gdpr_consent", {})
    if not gdpr_consent.get("given"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=ErrorResponse(
                error_code="GDPR_CONSENT_REQUIRED",
                message="GDPR consent must be provided to download offer",
                details={"required_field": "gdpr_consent.given"}
            ).model_dump()
        )

    # Check if offer exists
    offer = await service.get_offer(offer_id)
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="OFFER_NOT_FOUND",
                message=f"Offer {offerId} not found"
            ).model_dump()
        )

    # Generate PDF
    try:
        language = customer_data.get("language_preference", "de")
        pdf_bytes = await service.generate_pdf(offer_id, language)

        filename = f"offer-{offer.offer_number}.pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="PDF_GENERATION_FAILED",
                message="Failed to generate PDF",
                details={"error": str(e)}
            ).model_dump()
        )
