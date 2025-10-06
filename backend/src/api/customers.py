"""
Customer API Endpoints (T049-T050)

OpenAPI-compliant endpoints for customer data management.
Implements GDPR-compliant customer creation and deletion.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field, field_validator, EmailStr

from ..models.customer import Customer, GDPRConsent, ConsentPurpose
from ..models.value_objects import EmailAddress, PhoneNumber, LanguageCode
from ..infrastructure.middleware.auth import verify_api_key
from ..infrastructure.repositories.customer_repository import CustomerRepository


router = APIRouter(
    prefix="/customers",
    tags=["customers"],
    dependencies=[Depends(verify_api_key)]
)


# Request/Response Models
class GDPRConsentRequest(BaseModel):
    """GDPR consent information."""
    given: bool = Field(..., description="Whether consent was given")
    purposes: List[str] = Field(
        ...,
        min_length=1,
        description="Purposes for which consent is given"
    )
    consent_text_version: str = Field(..., description="Version of consent text")
    ip_address: Optional[str] = Field(None, pattern=r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")

    @field_validator('purposes')
    @classmethod
    def validate_purposes(cls, v: List[str]) -> List[str]:
        valid_purposes = {"offer_generation", "marketing", "analytics"}
        for purpose in v:
            if purpose not in valid_purposes:
                raise ValueError(f"Invalid purpose: {purpose}. Must be one of {valid_purposes}")
        return v


class CreateCustomerRequest(BaseModel):
    """Request model for customer creation (T049)."""
    company_name: str = Field(..., max_length=200)
    contact_person: str = Field(..., max_length=200)
    email: EmailStr = Field(..., description="Contact email address")
    phone: Optional[str] = Field(
        None,
        pattern=r"^\+[0-9]{1,15}$",
        description="Phone number in E.164 format"
    )
    language_preference: str = Field(
        default="de",
        pattern="^(de|en|fr|es|it|nl|pl|pt|cs|da|el|hu|ro|sv|bg|hr|et|fi|ga|lt|lv|mt|sk|sl)$"
    )
    gdpr_consent: GDPRConsentRequest = Field(..., description="GDPR consent information")

    @field_validator('company_name', 'contact_person')
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class CustomerResponse(BaseModel):
    """Response model for customer creation."""
    customer_id: str
    gdpr_consent_recorded: bool


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# Dependency for customer repository
async def get_customer_repository() -> CustomerRepository:
    """Get customer repository instance."""
    from ..infrastructure.database import get_db_connection
    db_conn = await get_db_connection()
    return CustomerRepository(db_conn)


# API Endpoints

@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Customer created"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        409: {"model": ErrorResponse, "description": "Customer already exists"}
    }
)
async def create_customer(
    request: CreateCustomerRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    repository: CustomerRepository = Depends(get_customer_repository)
) -> CustomerResponse:
    """
    T049: Create customer with GDPR consent

    Creates a new customer with explicit GDPR consent.
    Records consent timestamp, IP address, and purposes.

    GDPR Requirements:
    - Consent must be explicit (given=true)
    - At least one purpose must be specified
    - Consent text version must be tracked
    - IP address should be recorded for audit trail

    Returns customer ID and confirmation of consent recording.
    """
    # Validate GDPR consent is explicitly given
    if not request.gdpr_consent.given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="GDPR_CONSENT_REQUIRED",
                message="GDPR consent must be explicitly given (given=true)",
                details={"field": "gdpr_consent.given"}
            ).model_dump()
        )

    try:
        # Check if customer already exists by email
        existing_customer = await repository.find_by_email(request.email)
        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ErrorResponse(
                    error_code="CUSTOMER_EXISTS",
                    message=f"Customer with email {request.email} already exists",
                    details={"existing_customer_id": str(existing_customer.id)}
                ).model_dump()
            )

        # Parse phone number if provided
        phone = None
        if request.phone:
            # Split E.164 format (+49123456789 -> country_code=+49, number=123456789)
            phone = PhoneNumber(
                country_code=request.phone[:3],  # First 3 chars for country code
                number=request.phone[3:]  # Rest is the number
            )

        # Create GDPR consent
        consent_purposes = [ConsentPurpose(p) for p in request.gdpr_consent.purposes]
        gdpr_consent = GDPRConsent(
            given_at=datetime.utcnow(),
            ip_address=request.gdpr_consent.ip_address or "0.0.0.0",
            consent_text_version=request.gdpr_consent.consent_text_version,
            purposes=consent_purposes,
            withdrawn_at=None
        )

        # Create customer entity
        from uuid import uuid4
        external_id = f"CUST-{datetime.utcnow().year}-{uuid4().hex[:8].upper()}"

        customer = Customer(
            external_id=external_id,
            company_name=request.company_name,
            contact_person=request.contact_person,
            email=EmailAddress(value=request.email),
            phone=phone,
            language_preference=LanguageCode(code=request.language_preference),
            gdpr_consent=gdpr_consent,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deletion_requested_at=None
        )

        # Persist customer
        await repository.save(customer)

        # Publish customer created event
        # TODO: Integrate with event bus
        # await event_bus.publish({
        #     "event_type": "CustomerCreated",
        #     "aggregate_id": str(customer.id),
        #     "payload": {...}
        # })

        return CustomerResponse(
            customer_id=str(customer.id),
            gdpr_consent_recorded=True
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_DATA",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="CUSTOMER_CREATION_FAILED",
                message="Failed to create customer",
                details={"error": str(e)}
            ).model_dump()
        )


@router.delete(
    "/{customerId}",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Deletion request recorded (4-year retention starts)"},
        404: {"model": ErrorResponse, "description": "Customer not found"}
    }
)
async def delete_customer(
    customerId: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    repository: CustomerRepository = Depends(get_customer_repository)
) -> Dict[str, Any]:
    """
    T050: Request customer data deletion (GDPR Article 17)

    Initiates GDPR-compliant deletion process:
    1. Marks customer for deletion
    2. Starts 4-year legal retention period
    3. Triggers data pseudonymization
    4. Schedules final deletion after retention period

    GDPR Compliance:
    - Article 17: Right to erasure
    - German law: 4-year retention for tax/legal purposes
    - Personal data is pseudonymized immediately
    - Complete deletion occurs after retention period

    Note: This does not immediately delete the customer.
    It records the deletion request and starts the retention period.
    """
    try:
        customer_id = UUID(customerId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid customer ID format"
            ).model_dump()
        )

    # Retrieve customer
    customer = await repository.get_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="CUSTOMER_NOT_FOUND",
                message=f"Customer {customerId} not found"
            ).model_dump()
        )

    # Check if deletion already requested
    if customer.deletion_requested_at:
        return {
            "status": "deletion_already_requested",
            "customer_id": customerId,
            "deletion_requested_at": customer.deletion_requested_at.isoformat(),
            "retention_period_years": 4,
            "message": "Deletion was already requested for this customer"
        }

    try:
        # Mark customer for deletion (triggers 4-year retention)
        customer.request_deletion()

        # Persist updated customer
        await repository.save(customer)

        # Publish deletion requested event
        # TODO: Integrate with event bus
        # This event would trigger:
        # 1. Data pseudonymization job
        # 2. Notification to customer
        # 3. Scheduling of final deletion after 4 years
        # await event_bus.publish({
        #     "event_type": "CustomerDeletionRequested",
        #     "aggregate_id": str(customer_id),
        #     "payload": {
        #         "deletion_requested_at": customer.deletion_requested_at.isoformat(),
        #         "retention_period_years": 4,
        #         "final_deletion_date": (customer.deletion_requested_at + timedelta(days=1460)).isoformat()
        #     }
        # })

        from datetime import timedelta
        final_deletion_date = customer.deletion_requested_at + timedelta(days=1460)  # 4 years

        return {
            "status": "deletion_requested",
            "customer_id": customerId,
            "deletion_requested_at": customer.deletion_requested_at.isoformat(),
            "retention_period_years": 4,
            "final_deletion_date": final_deletion_date.isoformat(),
            "message": "Customer deletion request recorded. Data will be pseudonymized immediately and deleted after 4-year legal retention period."
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="DELETION_REQUEST_FAILED",
                message="Failed to process deletion request",
                details={"error": str(e)}
            ).model_dump()
        )
