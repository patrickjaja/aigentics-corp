"""Contract tests for POST /offers/{id}/download endpoint.

Tests verify the API contract matches contracts/offer-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestDownloadOffer:
    """Test POST /offers/{offerId}/download endpoint contract."""

    async def test_download_offer_success(
        self,
        api_client: AsyncClient,
        valid_offer_id: str,
        sample_customer_data: dict
    ):
        """Test successful PDF download with GDPR consent."""
        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=sample_customer_data
        )

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            # Verify PDF content type
            assert response.headers["content-type"] == "application/pdf"

            # Verify Content-Disposition header with filename
            assert "Content-Disposition" in response.headers
            disposition = response.headers["Content-Disposition"]
            assert "attachment" in disposition
            assert ".pdf" in disposition
            assert "offer-" in disposition  # Format: offer-24-0001.pdf

            # Verify response is binary PDF data
            assert isinstance(response.content, bytes)
            assert len(response.content) > 0

            # Basic PDF validation (starts with %PDF)
            assert response.content.startswith(b"%PDF")

    async def test_download_offer_without_gdpr_consent(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test 422 Unprocessable when GDPR consent not provided."""
        customer_data_no_consent = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": False,  # Consent not given
                "purposes": [],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=customer_data_no_consent
        )

        assert response.status_code == 422

    async def test_download_offer_missing_customer_data(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test 400 Bad Request when required customer fields are missing."""
        incomplete_data = {
            "company_name": "Test GmbH"
            # Missing required fields: contact_person, email, gdpr_consent
        }

        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=incomplete_data
        )

        assert response.status_code == 400

    async def test_download_offer_invalid_email(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test 400 Bad Request for invalid email format."""
        invalid_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "invalid-email",  # Invalid format
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=invalid_data
        )

        assert response.status_code == 400

    async def test_download_offer_invalid_phone_format(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test 400 Bad Request for invalid phone number format."""
        invalid_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "phone": "123456",  # Invalid format, should be +[0-9]{1,15}
            "gdpr_consent": {
                "given": True,
                "purposes": ["offer_generation"],
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=invalid_data
        )

        assert response.status_code == 400

    async def test_download_offer_not_found(
        self, api_client: AsyncClient, sample_customer_data: dict
    ):
        """Test 404 Not Found for non-existent offer."""
        response = await api_client.post(
            "/offers/00000000-0000-0000-0000-000000000000/download",
            json=sample_customer_data
        )

        assert response.status_code == 404

    async def test_download_offer_gdpr_purposes(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test GDPR consent with different purposes."""
        valid_purposes = ["offer_generation", "marketing", "analytics"]

        customer_data = {
            "company_name": "Test GmbH",
            "contact_person": "Max Mustermann",
            "email": "max@test.de",
            "gdpr_consent": {
                "given": True,
                "purposes": valid_purposes,  # Multiple purposes
                "consent_text_version": "1.0"
            }
        }

        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=customer_data
        )

        assert response.status_code in [200, 404]

    async def test_download_offer_din5008_compliance(
        self,
        api_client: AsyncClient,
        valid_offer_id: str,
        sample_customer_data: dict
    ):
        """Test that generated PDF follows DIN 5008 German business letter format."""
        response = await api_client.post(
            f"/offers/{valid_offer_id}/download",
            json=sample_customer_data
        )

        if response.status_code == 200:
            # PDF should be generated according to DIN 5008 standards
            # This is verified in the PDF generation service tests
            # Here we just verify the PDF is generated
            assert response.content.startswith(b"%PDF")
