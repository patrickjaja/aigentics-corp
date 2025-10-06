"""Customer aggregate root and related entities."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .value_objects import EmailAddress, LanguageCode, PhoneNumber


class ConsentPurpose(str, Enum):
    """Purposes for which GDPR consent can be given."""

    OFFER_GENERATION = "offer_generation"
    MARKETING = "marketing"
    ANALYTICS = "analytics"


class GDPRConsent(BaseModel):
    """GDPR consent tracking with purposes and withdrawal capability."""

    given_at: datetime = Field(
        ...,
        description="Timestamp when consent was given"
    )
    ip_address: str = Field(
        ...,
        description="IP address from which consent was given"
    )
    consent_text_version: str = Field(
        ...,
        description="Version identifier of the consent text shown to user"
    )
    purposes: List[ConsentPurpose] = Field(
        ...,
        description="List of purposes for which consent was given"
    )
    withdrawn_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when consent was withdrawn, if applicable"
    )

    class Config:
        """Pydantic configuration."""
        frozen = True


class Customer(BaseModel):
    """
    Customer aggregate root.

    Manages customer information, GDPR consent, and data privacy operations.
    Supports pseudonymization through external_id for GDPR compliance.

    Invariants:
    - Email must be valid format
    - GDPR consent required before storing PII
    - Deletion request triggers 4-year legal retention

    State Transitions:
    - Prospect → Lead → Customer → Deleted
    """

    id: UUID = Field(
        default_factory=uuid4,
        description="Internal customer identifier"
    )
    external_id: str = Field(
        ...,
        description="External identifier for GDPR pseudonymization"
    )
    company_name: str = Field(
        ...,
        description="Name of the customer's company"
    )
    contact_person: str = Field(
        ...,
        description="Name of the primary contact person"
    )
    email: EmailAddress = Field(
        ...,
        description="Contact email address (validated)"
    )
    phone: Optional[PhoneNumber] = Field(
        default=None,
        description="Optional phone number (validated)"
    )
    language_preference: LanguageCode = Field(
        ...,
        description="Preferred language for communication (ISO 639-1)"
    )
    gdpr_consent: GDPRConsent = Field(
        ...,
        description="GDPR consent information"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when customer was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last update"
    )
    deletion_requested_at: Optional[datetime] = Field(
        default=None,
        description="Timestamp when deletion was requested (triggers 4-year retention)"
    )

    def request_deletion(self) -> None:
        """
        Request customer data deletion.

        Triggers 4-year legal retention period before actual deletion.
        """
        if self.deletion_requested_at is None:
            object.__setattr__(self, 'deletion_requested_at', datetime.utcnow())
            object.__setattr__(self, 'updated_at', datetime.utcnow())

    def withdraw_consent(self) -> None:
        """
        Withdraw GDPR consent.

        Creates new GDPRConsent object with withdrawn_at set.
        """
        if self.gdpr_consent.withdrawn_at is None:
            new_consent = GDPRConsent(
                given_at=self.gdpr_consent.given_at,
                ip_address=self.gdpr_consent.ip_address,
                consent_text_version=self.gdpr_consent.consent_text_version,
                purposes=self.gdpr_consent.purposes,
                withdrawn_at=datetime.utcnow()
            )
            object.__setattr__(self, 'gdpr_consent', new_consent)
            object.__setattr__(self, 'updated_at', datetime.utcnow())

    def has_active_consent(self) -> bool:
        """Check if customer has active (non-withdrawn) GDPR consent."""
        return self.gdpr_consent.withdrawn_at is None

    def has_consent_for_purpose(self, purpose: ConsentPurpose) -> bool:
        """Check if customer has active consent for a specific purpose."""
        return self.has_active_consent() and purpose in self.gdpr_consent.purposes

    class Config:
        """Pydantic configuration."""
        frozen = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "external_id": "CUST-2025-001",
                "company_name": "Acme Corporation",
                "contact_person": "John Doe",
                "email": {"value": "john.doe@acme.com"},
                "phone": {
                    "country_code": "+49",
                    "number": "1234567890"
                },
                "language_preference": {"code": "de"},
                "gdpr_consent": {
                    "given_at": "2025-09-30T10:00:00Z",
                    "ip_address": "192.168.1.1",
                    "consent_text_version": "v1.0",
                    "purposes": ["offer_generation", "marketing"],
                    "withdrawn_at": None
                },
                "created_at": "2025-09-30T10:00:00Z",
                "updated_at": "2025-09-30T10:00:00Z",
                "deletion_requested_at": None
            }
        }
