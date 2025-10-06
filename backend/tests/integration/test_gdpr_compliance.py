"""
Integration Test: GDPR Compliance

Tests GDPR requirements for customer data handling, consent management,
and data deletion as required by FR-005, FR-013, FR-018, FR-021.

GDPR Requirements:
- Explicit consent before storing PII (FR-005)
- AES-256 encryption for all PII (FR-018)
- 10-year data retention for offers (FR-013)
- 4-year retention after deletion request (FR-021)
- Right to erasure implementation
- Data minimization and purpose limitation

Validation Scenarios:
- Cannot download offer without GDPR consent
- Consent tracked with timestamp and IP
- Customer can request data deletion
- PII encrypted at rest
- Audit logs exclude sensitive data
- Data export functionality
"""

import pytest
from uuid import uuid4
from datetime import datetime, timedelta


class TestGDPRCompliance:
    """Test GDPR compliance for data privacy."""

    @pytest.mark.asyncio
    async def test_cannot_download_offer_without_gdpr_consent(
        self, async_client, existing_offer
    ):
        """
        Test Case: Offer download blocked without GDPR consent

        Given: Valid offer exists
        When: Download requested without consent
        Then: Returns 422 with consent requirement error

        Compliance: FR-005 - Explicit consent required
        """
        # ARRANGE
        offer_id = existing_offer["id"]

        # Customer data WITHOUT consent
        customer_data_no_consent = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": False,
                "purposes": [],
                "consent_text_version": "1.0"
            }
        }

        # ACT: Attempt download without consent
        response = await async_client.post(
            f"/v1/offers/{offer_id}/download",
            json=customer_data_no_consent
        )

        # ASSERT: Blocked
        assert response.status_code == 422
        error = response.json()

        assert "consent" in error["message"].lower() or "gdpr" in error["message"].lower()

    @pytest.mark.asyncio
    async def test_valid_gdpr_consent_allows_download(
        self, async_client, existing_offer
    ):
        """
        Test Case: Valid GDPR consent enables offer download

        Given: Valid offer exists
        When: Download requested WITH proper consent
        Then: PDF generated successfully

        Compliance: FR-005 - Consent enables data processing
        """
        # ARRANGE
        offer_id = existing_offer["id"]

        customer_data_with_consent = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "phone": "+491234567890",
            "language_preference": "de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0",
                "ip_address": "192.168.1.1"
            }
        }

        # ACT: Download with consent
        response = await async_client.post(
            f"/v1/offers/{offer_id}/download",
            json=customer_data_with_consent
        )

        # ASSERT: Success
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_gdpr_consent_tracked_with_metadata(
        self, async_client, db_session
    ):
        """
        Test Case: Consent recorded with timestamp and IP

        Given: Customer provides consent
        When: Customer created
        Then: Consent metadata stored (timestamp, IP, version)

        Compliance: GDPR Article 7 - Proof of consent
        """
        # ARRANGE
        customer_data = {
            "company_name": "GDPR Test GmbH",
            "contact_person": "Anna Schmidt",
            "email": "anna@gdprtest.de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation", "analytics"],
                "consent_text_version": "1.0",
                "ip_address": "192.168.1.100"
            }
        }

        # ACT: Create customer
        response = await async_client.post(
            "/v1/customers",
            json=customer_data
        )

        # ASSERT: Customer created
        assert response.status_code == 201
        data = response.json()

        assert data["gdpr_consent_recorded"] is True
        customer_id = data["customer_id"]

        # Verify consent stored in database
        # (This would query the database directly)
        from src.models.customer import Customer

        customer = db_session.query(Customer).filter_by(id=customer_id).first()

        assert customer is not None
        assert customer.gdpr_consent is not None
        assert customer.gdpr_consent.given_at is not None
        assert customer.gdpr_consent.ip_address == "192.168.1.100"
        assert customer.gdpr_consent.consent_text_version == "1.0"
        assert "offer_generation" in customer.gdpr_consent.purposes

    @pytest.mark.asyncio
    async def test_customer_can_withdraw_consent(
        self, async_client, existing_customer
    ):
        """
        Test Case: Customer can withdraw GDPR consent

        Given: Customer with active consent
        When: Consent withdrawal requested
        Then: Consent marked as withdrawn with timestamp

        Compliance: GDPR Article 7(3) - Right to withdraw
        """
        # ARRANGE
        customer_id = existing_customer["id"]

        # ACT: Withdraw consent (implementation specific endpoint)
        response = await async_client.post(
            f"/v1/customers/{customer_id}/withdraw-consent",
            json={"purposes": ["marketing", "analytics"]}
        )

        # ASSERT: Consent withdrawn
        assert response.status_code == 200
        data = response.json()

        assert data["consent_withdrawn"] is True
        assert "withdrawn_at" in data

    @pytest.mark.asyncio
    async def test_customer_data_deletion_request(
        self, async_client, existing_customer
    ):
        """
        Test Case: Customer can request data deletion (Right to Erasure)

        Given: Customer with stored data
        When: Deletion requested
        Then: Deletion scheduled with 4-year legal retention

        Compliance: FR-021, GDPR Article 17
        """
        # ARRANGE
        customer_id = existing_customer["id"]

        # ACT: Request deletion
        response = await async_client.delete(
            f"/v1/customers/{customer_id}",
            json={"reason": "No longer using service"}
        )

        # ASSERT: Deletion scheduled
        assert response.status_code == 200
        data = response.json()

        assert data["deletion_scheduled"] is True
        assert "deletion_date" in data  # 4 years from now
        assert data["legal_retention_period"] == "4 years"

        # Verify customer marked for deletion
        customer_response = await async_client.get(f"/v1/customers/{customer_id}")

        # Customer data should be pseudonymized
        customer_data = customer_response.json()
        assert customer_data.get("deletion_requested_at") is not None

    @pytest.mark.asyncio
    async def test_pii_encryption_at_rest(
        self, async_client, db_session, crypto_service
    ):
        """
        Test Case: PII encrypted in database

        Given: Customer data stored
        When: Database inspected directly
        Then: Email, phone, name are encrypted

        Compliance: FR-018 - AES-256 encryption
        """
        # ARRANGE: Create customer
        customer_data = {
            "company_name": "Encryption Test GmbH",
            "contact_person": "Private Name",
            "email": "private@encryption.de",
            "phone": "+491234567890",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await async_client.post(
            "/v1/customers",
            json=customer_data
        )

        assert response.status_code == 201
        customer_id = response.json()["customer_id"]

        # ACT: Query database directly
        from src.models.customer import Customer

        customer = db_session.query(Customer).filter_by(id=customer_id).first()

        # ASSERT: PII fields are encrypted (not plaintext)
        # The email field should NOT contain the plaintext email
        assert customer.email != "private@encryption.de"
        assert len(customer.email) > len("private@encryption.de")  # Encrypted data is longer

        # Verify can decrypt
        decrypted_email = crypto_service.decrypt(customer.email)
        assert decrypted_email == "private@encryption.de"

    @pytest.mark.asyncio
    async def test_data_minimization_principle(
        self, async_client, db_session
    ):
        """
        Test Case: Only necessary data collected

        Given: Customer creation
        When: Optional fields omitted
        Then: System accepts minimal data

        Compliance: GDPR Article 5(1)(c) - Data minimization
        """
        # ARRANGE: Minimal customer data
        minimal_data = {
            "company_name": "Minimal GmbH",
            "contact_person": "Min User",
            "email": "min@minimal.de",
            # NO phone, NO language_preference
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        # ACT: Create customer with minimal data
        response = await async_client.post(
            "/v1/customers",
            json=minimal_data
        )

        # ASSERT: Accepted
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_purpose_limitation_enforcement(
        self, async_client, existing_customer
    ):
        """
        Test Case: Data used only for consented purposes

        Given: Customer consented only to "offer_generation"
        When: Attempt to use data for "marketing"
        Then: System blocks non-consented use

        Compliance: GDPR Article 5(1)(b) - Purpose limitation
        """
        # ARRANGE: Customer with limited consent
        customer_id = existing_customer["id"]
        # Assume customer only consented to "offer_generation"

        # ACT: Attempt to send marketing email (not consented)
        response = await async_client.post(
            "/v1/notifications/marketing",
            json={
                "customer_id": customer_id,
                "campaign": "new_features"
            }
        )

        # ASSERT: Blocked
        assert response.status_code in [403, 422]
        error = response.json()

        assert "consent" in error["message"].lower() or "purpose" in error["message"].lower()

    @pytest.mark.asyncio
    async def test_data_export_for_portability(
        self, async_client, existing_customer
    ):
        """
        Test Case: Customer can export their data

        Given: Customer with stored data
        When: Data export requested
        Then: Receives all personal data in structured format

        Compliance: GDPR Article 20 - Right to data portability
        """
        # ARRANGE
        customer_id = existing_customer["id"]

        # ACT: Request data export
        response = await async_client.get(
            f"/v1/customers/{customer_id}/export",
            headers={"Accept": "application/json"}
        )

        # ASSERT: Data exported
        assert response.status_code == 200
        data = response.json()

        # Verify complete data package
        assert "customer_data" in data
        assert "conversations" in data
        assert "offers" in data
        assert "consent_history" in data

        customer_data = data["customer_data"]
        assert customer_data["email"] == existing_customer["email"]

    @pytest.mark.asyncio
    async def test_audit_logs_exclude_pii(
        self, async_client, db_session, existing_customer
    ):
        """
        Test Case: Audit logs do not contain PII

        Given: Customer actions logged
        When: Audit logs reviewed
        Then: Logs contain pseudonymized identifiers, not PII

        Compliance: Data protection by design
        """
        # ARRANGE: Customer performs action
        customer_id = existing_customer["id"]

        # ACT: Perform logged action
        await async_client.get(f"/v1/customers/{customer_id}")

        # Query audit logs
        from src.infrastructure.events.schema import DomainEvent

        events = db_session.query(DomainEvent).filter_by(
            aggregate_id=customer_id
        ).all()

        # ASSERT: No PII in event payloads
        for event in events:
            payload_str = str(event.payload)

            # Should not contain actual email
            assert "actual-email@example.de" not in payload_str
            # Should use customer_id or pseudonym
            assert str(customer_id) in str(event.aggregate_id)

    @pytest.mark.asyncio
    async def test_data_retention_period_enforcement(
        self, async_client, db_session
    ):
        """
        Test Case: Data retention periods enforced

        Given: Customer data older than retention period
        When: Cleanup job runs
        Then: Data deleted according to policy

        Compliance: FR-013 (10 years offers), FR-021 (4 years customer data)
        """
        # ARRANGE: Create old customer (simulation)
        old_date = datetime.utcnow() - timedelta(days=365 * 5)  # 5 years ago

        from src.models.customer import Customer

        old_customer = Customer(
            company_name="Old Corp",
            contact_person="Old User",
            email="old@example.de",
            deletion_requested_at=old_date
        )

        db_session.add(old_customer)
        db_session.commit()

        # ACT: Run cleanup job
        response = await async_client.post(
            "/v1/admin/maintenance/cleanup-old-data",
            headers={"Authorization": "Bearer admin_token"}
        )

        # ASSERT: Old data cleaned
        assert response.status_code == 200
        data = response.json()

        assert data["customers_deleted"] > 0

    @pytest.mark.asyncio
    async def test_consent_version_tracking(
        self, async_client
    ):
        """
        Test Case: Consent text versioning

        Given: Multiple versions of consent text
        When: Customer consents
        Then: Exact version recorded

        Compliance: GDPR proof of consent requirements
        """
        # ARRANGE: Customer with specific consent version
        customer_data = {
            "company_name": "Version Test GmbH",
            "contact_person": "Ver User",
            "email": "ver@test.de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "2.1"  # Specific version
            }
        }

        # ACT: Create customer
        response = await async_client.post(
            "/v1/customers",
            json=customer_data
        )

        # ASSERT: Version recorded
        assert response.status_code == 201
        customer_id = response.json()["customer_id"]

        # Verify version stored
        customer_response = await async_client.get(f"/v1/customers/{customer_id}")
        customer_data_response = customer_response.json()

        # Should have consent version tracked
        assert "gdpr_consent" in customer_data_response
        assert customer_data_response["gdpr_consent"]["consent_text_version"] == "2.1"

    @pytest.mark.asyncio
    async def test_cross_border_data_transfer_restrictions(
        self, async_client, existing_customer
    ):
        """
        Test Case: EU data residency maintained

        Given: Customer data stored
        When: Data location checked
        Then: Confirms EU-based storage

        Compliance: GDPR Article 44 - International transfers
        """
        # ARRANGE
        customer_id = existing_customer["id"]

        # ACT: Check data location (metadata endpoint)
        response = await async_client.get(
            f"/v1/customers/{customer_id}/metadata",
            headers={"Authorization": "Bearer admin_token"}
        )

        # ASSERT: EU residency confirmed
        assert response.status_code == 200
        metadata = response.json()

        assert "storage_region" in metadata
        # Hetzner is EU-based (Germany/Finland)
        assert metadata["storage_region"] in ["EU", "DE", "FI"]
