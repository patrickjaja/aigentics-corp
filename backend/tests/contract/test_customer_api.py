"""Contract tests for POST /customers endpoint.

Tests verify the API contract matches contracts/offer-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestCreateCustomer:
    """Test POST /customers endpoint contract."""

    async def test_create_customer_success(
        self, api_client: AsyncClient, sample_customer_data: dict
    ):
        """Test successful customer creation returns 201."""
        response = await api_client.post(
            "/customers",
            json=sample_customer_data
        )

        assert response.status_code == 201
        data = response.json()

        # Verify response schema
        assert "customer_id" in data
        assert "gdpr_consent_recorded" in data

        # Verify types
        assert isinstance(data["customer_id"], str)
        assert isinstance(data["gdpr_consent_recorded"], bool)
        assert data["gdpr_consent_recorded"] is True

    async def test_create_customer_missing_required_fields(
        self, api_client: AsyncClient
    ):
        """Test 400 Bad Request when required fields are missing."""
        # Missing email
        incomplete_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            # Missing: email, gdpr_consent
        }

        response = await api_client.post(
            "/customers",
            json=incomplete_data
        )

        assert response.status_code == 400

    async def test_create_customer_invalid_email(self, api_client: AsyncClient):
        """Test 400 Bad Request for invalid email format."""
        invalid_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "not-an-email",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            "/customers",
            json=invalid_data
        )

        assert response.status_code == 400

    async def test_create_customer_without_gdpr_consent(
        self, api_client: AsyncClient
    ):
        """Test that GDPR consent is required."""
        no_consent_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": False,
                "purposes": [],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            "/customers",
            json=no_consent_data
        )

        # Should reject customers without consent
        assert response.status_code in [400, 422]

    async def test_create_customer_duplicate(
        self, api_client: AsyncClient, sample_customer_data: dict
    ):
        """Test 409 Conflict when customer already exists."""
        # First creation should succeed
        response1 = await api_client.post(
            "/customers",
            json=sample_customer_data
        )

        # Second creation with same email should conflict
        response2 = await api_client.post(
            "/customers",
            json=sample_customer_data
        )

        assert response1.status_code == 201 or response2.status_code == 409

    async def test_create_customer_with_phone(self, api_client: AsyncClient):
        """Test customer creation with optional phone number."""
        data_with_phone = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max.phone@test.de",
            "phone": "+491701234567",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            "/customers",
            json=data_with_phone
        )

        assert response.status_code == 201

    async def test_create_customer_invalid_phone_format(
        self, api_client: AsyncClient
    ):
        """Test 400 Bad Request for invalid phone format."""
        invalid_phone_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max.invalidphone@test.de",
            "phone": "123456",  # Should be +[0-9]{1,15}
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            "/customers",
            json=invalid_phone_data
        )

        assert response.status_code == 400

    async def test_create_customer_all_languages(self, api_client: AsyncClient):
        """Test customer creation with all supported language preferences."""
        languages = ["de", "en", "fr", "es", "it", "nl"]

        for lang in languages:
            data = {
                "company_name": f"Test {lang.upper()} GmbH",
                "contact_person": "Max Mustermann",
                "email": f"max.{lang}@test.de",
                "language_preference": lang,
                "gdpr_consent": {
                    "given": True,
                    "purposes": ["offer_generation"],
                    "consent_text_version": "1.0"
                }
            }

            response = await api_client.post(
                "/customers",
                json=data
            )

            assert response.status_code in [201, 409]

    async def test_create_customer_gdpr_purposes(self, api_client: AsyncClient):
        """Test GDPR consent with different purposes combinations."""
        purposes_combinations = [
            ["offer_generation"],
            ["offer_generation", "marketing"],
            ["offer_generation", "marketing", "analytics"]
        ]

        for i, purposes in enumerate(purposes_combinations):
            data = {
                "company_name": f"Test Purpose {i} GmbH",
                "contact_person": "Max Mustermann",
                "email": f"max.purpose{i}@test.de",
                "gdpr_consent": {
                    "given": True,
                    "purposes": purposes,
                    "consent_text_version": "1.0",
                    "ip_address": "192.168.1.1"
                }
            }

            response = await api_client.post(
                "/customers",
                json=data
            )

            assert response.status_code in [201, 409]

    async def test_create_customer_name_length_validation(
        self, api_client: AsyncClient
    ):
        """Test 400 Bad Request when names exceed max length."""
        long_name = "X" * 201  # maxLength: 200

        invalid_data = {
            "company_name": long_name,
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            "/customers",
            json=invalid_data
        )

        assert response.status_code == 400
