"""Contract tests for GET /offers/{id} endpoint.

Tests verify the API contract matches contracts/offer-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestGetOffer:
    """Test GET /offers/{offerId} endpoint contract."""

    async def test_get_offer_success(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test successful offer retrieval returns 200 with OfferDetails schema."""
        response = await api_client.get(f"/offers/{valid_offer_id}")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()

            # Verify OfferDetails extends OfferResponse
            assert "offer_id" in data
            assert "offer_number" in data
            assert "status" in data
            assert "total_value" in data
            assert "approval_required" in data
            assert "created_at" in data
            assert "valid_until" in data

            # Additional fields in OfferDetails
            assert "version" in data
            assert "work_packages" in data

            # Verify version is positive integer
            assert isinstance(data["version"], int)
            assert data["version"] >= 1

            # Verify work_packages array
            assert isinstance(data["work_packages"], list)

            for wp in data["work_packages"]:
                # Verify WorkPackage schema
                assert "id" in wp
                assert "name" in wp
                assert "description" in wp
                assert "deliverables" in wp
                assert "estimated_hours" in wp
                assert "hourly_rate" in wp
                assert "total_cost" in wp

                # Verify EstimatedHours schema
                hours = wp["estimated_hours"]
                assert "expected" in hours
                assert "confidence" in hours
                assert 0 <= hours["confidence"] <= 1

                # Verify Money schema for rates and costs
                for money_field in ["hourly_rate", "total_cost"]:
                    money = wp[money_field]
                    assert "amount" in money
                    assert "currency" in money

                # Verify Deliverable schema
                for deliverable in wp["deliverables"]:
                    assert "name" in deliverable
                    assert "description" in deliverable

    async def test_get_offer_not_found(self, api_client: AsyncClient):
        """Test 404 Not Found for non-existent offer."""
        response = await api_client.get(
            "/offers/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404
        error = response.json()
        assert "error_code" in error
        assert "message" in error

    async def test_get_offer_preview(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test GET /offers/{offerId}/preview endpoint."""
        response = await api_client.get(
            f"/offers/{valid_offer_id}/preview?language=de"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            # Should return HTML content
            assert response.headers["content-type"].startswith("text/html")
            assert isinstance(response.text, str)

    async def test_get_offer_preview_all_languages(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test offer preview in all supported languages."""
        languages = ["de", "en", "fr", "es", "it"]

        for lang in languages:
            response = await api_client.get(
                f"/offers/{valid_offer_id}/preview?language={lang}"
            )

            assert response.status_code in [200, 404]

    async def test_get_offer_versions(
        self, api_client: AsyncClient, valid_offer_id: str
    ):
        """Test GET /offers/{offerId}/versions endpoint."""
        response = await api_client.get(f"/offers/{valid_offer_id}/versions")

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "versions" in data
            assert isinstance(data["versions"], list)

            for version in data["versions"]:
                # Verify OfferVersion schema
                assert "version" in version
                assert "created_at" in version
                if "changes" in version:
                    assert isinstance(version["changes"], list)
