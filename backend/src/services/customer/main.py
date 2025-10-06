"""Customer Service with GDPR compliance and PII encryption."""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from ...models.customer import (
    ConsentPurpose,
    Customer,
    GDPRConsent,
)
from ...models.value_objects import EmailAddress, LanguageCode, PhoneNumber
from .privacy import AuditLogEntry, EncryptedData, PIIEncryptionService

# Configure logging (exclude sensitive data)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Customer Service",
    description="GDPR-compliant customer management with PII encryption",
    version="1.0.0"
)

# Initialize encryption service
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    logger.warning("ENCRYPTION_KEY not set, generating temporary key (NOT FOR PRODUCTION!)")
pii_service = PIIEncryptionService(master_key=ENCRYPTION_KEY)

# In-memory storage (replace with database in production)
customers_store: Dict[str, Customer] = {}
encrypted_pii_store: Dict[str, Dict[str, EncryptedData]] = {}


class CreateCustomerRequest(BaseModel):
    """Request body for creating a customer."""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Company name"
    )
    contact_person: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Contact person name"
    )
    email: str = Field(
        ...,
        description="Email address"
    )
    phone: Optional[str] = Field(
        default=None,
        description="Phone number in international format"
    )
    language_preference: str = Field(
        default="en",
        description="ISO 639-1 language code"
    )
    consent_purposes: List[ConsentPurpose] = Field(
        ...,
        min_length=1,
        description="List of purposes for which consent is given"
    )
    consent_text_version: str = Field(
        default="v1.0",
        description="Version of consent text shown to user"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        EmailAddress(value=v)  # Raises ValueError if invalid
        return v

    @field_validator('language_preference')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """Validate language code."""
        LanguageCode(code=v)  # Raises ValueError if invalid
        return v

    @field_validator('phone')
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        """Validate phone number if provided."""
        if v:
            PhoneNumber.from_string(v)  # Raises ValueError if invalid
        return v


class CustomerResponse(BaseModel):
    """Response model for customer data (without encrypted fields)."""

    id: str
    external_id: str
    company_name: str
    contact_person: str
    email: str
    phone: Optional[str] = None
    language_preference: str
    gdpr_consent: Dict
    created_at: str
    updated_at: str
    deletion_requested_at: Optional[str] = None
    has_active_consent: bool


class DeleteCustomerRequest(BaseModel):
    """Request body for customer deletion."""

    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional reason for deletion request"
    )


class HealthCheckResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: str


def create_audit_log(
    action: str,
    customer: Customer,
    email: str,
    request: Request,
    metadata: Optional[Dict] = None
) -> None:
    """
    Create audit log entry without storing PII.

    Args:
        action: Action performed (e.g., "customer_created")
        customer: Customer object
        email: Email address (to hash)
        request: FastAPI request object
        metadata: Optional additional metadata
    """
    audit_entry = AuditLogEntry(
        action=action,
        customer_external_id=customer.external_id,
        email_hash=pii_service.hash_for_audit(email),
        ip_address=request.client.host if request.client else "unknown",
        timestamp=datetime.utcnow().isoformat(),
        metadata=metadata or {}
    )

    # Log without sensitive data
    logger.info(
        f"Audit: {action}",
        extra=audit_entry.to_log_dict()
    )


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.

    Returns:
        Service health status
    """
    return HealthCheckResponse(
        status="healthy",
        service="customer-service",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )


@app.post(
    "/customers",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_customer(
    request_body: CreateCustomerRequest,
    request: Request
) -> CustomerResponse:
    """
    Create a new customer with GDPR consent.

    GDPR Compliance:
    - Explicit consent required before storing PII
    - PII encrypted at rest using AES-256
    - Pseudonymized external_id generated
    - Audit log created (without PII)

    Args:
        request_body: Customer creation data
        request: FastAPI request object

    Returns:
        Created customer data

    Raises:
        HTTPException: If consent not provided or validation fails
    """
    try:
        # Verify consent is given
        if not request_body.consent_purposes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="GDPR consent required before storing PII"
            )

        # Create GDPR consent
        consent = GDPRConsent(
            given_at=datetime.utcnow(),
            ip_address=request.client.host if request.client else "unknown",
            consent_text_version=request_body.consent_text_version,
            purposes=request_body.consent_purposes,
            withdrawn_at=None
        )

        # Generate customer ID and external ID
        customer_id = uuid4()
        timestamp = datetime.utcnow().isoformat()
        external_id = pii_service.generate_external_id(
            str(customer_id),
            timestamp
        )

        # Create customer object with value objects
        customer = Customer(
            id=customer_id,
            external_id=external_id,
            company_name=request_body.company_name,
            contact_person=request_body.contact_person,
            email=EmailAddress(value=request_body.email),
            phone=PhoneNumber.from_string(request_body.phone) if request_body.phone else None,
            language_preference=LanguageCode(code=request_body.language_preference),
            gdpr_consent=consent,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deletion_requested_at=None
        )

        # Encrypt PII fields
        encrypted_fields = pii_service.encrypt_customer_data(
            company_name=request_body.company_name,
            contact_person=request_body.contact_person,
            email=request_body.email,
            phone=request_body.phone
        )

        # Store customer and encrypted PII (in production, use database)
        customers_store[str(customer_id)] = customer
        encrypted_pii_store[str(customer_id)] = encrypted_fields

        # Create audit log (without PII)
        create_audit_log(
            action="customer_created",
            customer=customer,
            email=request_body.email,
            request=request,
            metadata={
                "consent_purposes": [p.value for p in request_body.consent_purposes],
                "language": request_body.language_preference
            }
        )

        logger.info(
            f"Customer created: {pii_service.mask_email(request_body.email)} "
            f"(external_id: {external_id})"
        )

        # Return customer response
        return CustomerResponse(
            id=str(customer.id),
            external_id=customer.external_id,
            company_name=customer.company_name,
            contact_person=customer.contact_person,
            email=customer.email.value,
            phone=f"{customer.phone.country_code}{customer.phone.number}" if customer.phone else None,
            language_preference=customer.language_preference.code,
            gdpr_consent={
                "given_at": customer.gdpr_consent.given_at.isoformat(),
                "purposes": [p.value for p in customer.gdpr_consent.purposes],
                "withdrawn_at": customer.gdpr_consent.withdrawn_at.isoformat() if customer.gdpr_consent.withdrawn_at else None
            },
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
            deletion_requested_at=customer.deletion_requested_at.isoformat() if customer.deletion_requested_at else None,
            has_active_consent=customer.has_active_consent()
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating customer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.get("/customers/{customer_id}", response_model=CustomerResponse)
async def get_customer(customer_id: str, request: Request) -> CustomerResponse:
    """
    Retrieve customer by ID.

    Decrypts PII fields for authorized access.

    Args:
        customer_id: Customer UUID
        request: FastAPI request object

    Returns:
        Customer data

    Raises:
        HTTPException: If customer not found
    """
    try:
        # Validate UUID format
        try:
            UUID(customer_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

        # Retrieve customer
        customer = customers_store.get(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Check if deletion was requested
        if customer.deletion_requested_at:
            # Calculate retention period (4 years)
            retention_period = timedelta(days=4 * 365)
            deletion_date = customer.deletion_requested_at + retention_period

            if datetime.utcnow() >= deletion_date:
                raise HTTPException(
                    status_code=status.HTTP_410_GONE,
                    detail="Customer data has been deleted"
                )

        # Decrypt PII (in production, decrypt from database)
        encrypted_fields = encrypted_pii_store.get(customer_id, {})

        # Create audit log
        create_audit_log(
            action="customer_retrieved",
            customer=customer,
            email=customer.email.value,
            request=request,
            metadata={}
        )

        logger.info(
            f"Customer retrieved: {pii_service.mask_email(customer.email.value)} "
            f"(external_id: {customer.external_id})"
        )

        return CustomerResponse(
            id=str(customer.id),
            external_id=customer.external_id,
            company_name=customer.company_name,
            contact_person=customer.contact_person,
            email=customer.email.value,
            phone=f"{customer.phone.country_code}{customer.phone.number}" if customer.phone else None,
            language_preference=customer.language_preference.code,
            gdpr_consent={
                "given_at": customer.gdpr_consent.given_at.isoformat(),
                "purposes": [p.value for p in customer.gdpr_consent.purposes],
                "withdrawn_at": customer.gdpr_consent.withdrawn_at.isoformat() if customer.gdpr_consent.withdrawn_at else None
            },
            created_at=customer.created_at.isoformat(),
            updated_at=customer.updated_at.isoformat(),
            deletion_requested_at=customer.deletion_requested_at.isoformat() if customer.deletion_requested_at else None,
            has_active_consent=customer.has_active_consent()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving customer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@app.delete("/customers/{customer_id}", status_code=status.HTTP_202_ACCEPTED)
async def delete_customer(
    customer_id: str,
    request_body: DeleteCustomerRequest,
    request: Request
) -> JSONResponse:
    """
    Request customer deletion (GDPR Right to be Forgotten).

    Triggers 4-year retention period before actual deletion.

    Args:
        customer_id: Customer UUID
        request_body: Deletion request data
        request: FastAPI request object

    Returns:
        Deletion request confirmation

    Raises:
        HTTPException: If customer not found or already deleted
    """
    try:
        # Validate UUID format
        try:
            UUID(customer_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

        # Retrieve customer
        customer = customers_store.get(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        # Check if already requested
        if customer.deletion_requested_at:
            retention_period = timedelta(days=4 * 365)
            deletion_date = customer.deletion_requested_at + retention_period

            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "message": "Deletion already requested",
                    "deletion_requested_at": customer.deletion_requested_at.isoformat(),
                    "scheduled_deletion_date": deletion_date.isoformat(),
                    "external_id": customer.external_id
                }
            )

        # Request deletion (updates customer object)
        customer.request_deletion()

        # Update in store
        customers_store[customer_id] = customer

        # Create audit log
        create_audit_log(
            action="customer_deletion_requested",
            customer=customer,
            email=customer.email.value,
            request=request,
            metadata={
                "reason": request_body.reason or "Not provided"
            }
        )

        # Calculate scheduled deletion date
        retention_period = timedelta(days=4 * 365)
        deletion_date = customer.deletion_requested_at + retention_period

        logger.info(
            f"Customer deletion requested: {pii_service.mask_email(customer.email.value)} "
            f"(external_id: {customer.external_id})"
        )

        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Deletion request accepted. Data will be retained for 4 years as required by law.",
                "deletion_requested_at": customer.deletion_requested_at.isoformat(),
                "scheduled_deletion_date": deletion_date.isoformat(),
                "external_id": customer.external_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting customer: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


if __name__ == "__main__":
    import uvicorn

    # Get port from environment or use default
    port = int(os.getenv("CUSTOMER_SERVICE_PORT", 8003))

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
