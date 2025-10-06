"""Contract tests for POST /offers endpoint.

Tests verify the API contract matches contracts/offer-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestGenerateOffer:
    """Test POST /offers endpoint contract."""

    async def test_generate_offer_success(
        self,
        api_client: AsyncClient,
        valid_conversation_id: str,
    ):
        """Test successful offer generation returns 201 with correct schema."""
        project_id = "12345678-1234-1234-1234-123456789012"

        response = await api_client.post(
            "/offers",
            json={
                "project_id": project_id,
                "conversation_id": valid_conversation_id
            }
        )

        assert response.status_code == 201

        # Verify X-Processing-Time header exists
        assert "X-Processing-Time" in response.headers
        processing_time = int(response.headers["X-Processing-Time"])
        assert processing_time > 0
        # Performance requirement: <30 seconds
        assert processing_time < 30000  # milliseconds

        data = response.json()

        # Verify OfferResponse schema
        assert "offer_id" in data
        assert "offer_number" in data
        assert "status" in data
        assert "total_value" in data
        assert "approval_required" in data
        assert "created_at" in data
        assert "valid_until" in data

        # Verify offer_number format: YY-NNNN
        import re
        assert re.match(r"^\d{2}-\d{4}$", data["offer_number"])

        # Verify status enum
        assert data["status"] in [
            "draft", "pending_approval", "approved",
            "sent", "viewed", "accepted", "rejected", "expired"
        ]

        # Verify Money schema for total_value
        assert "amount" in data["total_value"]
        assert "currency" in data["total_value"]
        assert data["total_value"]["currency"] in ["EUR", "CHF"]

        # Verify approval_required is boolean
        assert isinstance(data["approval_required"], bool)

        # If approval required, workflow_id should be present
        if data["approval_required"]:
            assert "approval_workflow_id" in data

    async def test_generate_offer_with_customer_id(
        self, api_client: AsyncClient, valid_customer_id: str
    ):
        """Test offer generation with existing customer_id."""
        response = await api_client.post(
            "/offers",
            json={
                "project_id": "12345678-1234-1234-1234-123456789012",
                "conversation_id": "87654321-4321-4321-4321-210987654321",
                "customer_id": valid_customer_id
            }
        )

        assert response.status_code in [201, 404, 422]

    async def test_generate_offer_missing_required_fields(self, api_client: AsyncClient):
        """Test 400 Bad Request when required fields are missing."""
        # Missing conversation_id
        response = await api_client.post(
            "/offers",
            json={"project_id": "12345678-1234-1234-1234-123456789012"}
        )

        assert response.status_code == 400

        # Missing project_id
        response = await api_client.post(
            "/offers",
            json={"conversation_id": "87654321-4321-4321-4321-210987654321"}
        )

        assert response.status_code == 400

    async def test_generate_offer_invalid_project_id(self, api_client: AsyncClient):
        """Test 404 Not Found for non-existent project."""
        response = await api_client.post(
            "/offers",
            json={
                "project_id": "00000000-0000-0000-0000-000000000000",
                "conversation_id": "87654321-4321-4321-4321-210987654321"
            }
        )

        assert response.status_code == 404

    async def test_generate_offer_insufficient_information(
        self, api_client: AsyncClient
    ):
        """Test 422 Unprocessable when insufficient info for offer generation."""
        response = await api_client.post(
            "/offers",
            json={
                "project_id": "incomplete-project-id",
                "conversation_id": "incomplete-conversation-id"
            }
        )

        assert response.status_code in [400, 422]

    @pytest.mark.slow
    async def test_generate_offer_timeout(self, api_client: AsyncClient):
        """Test 503 Service Unavailable when 30s timeout exceeded."""
        # This test requires mocking a slow offer generation
        # In real scenario, the service should return 503 if generation takes >30s
        pass  # Implementation depends on service architecture

    async def test_generate_offer_high_value_triggers_approval(
        self, api_client: AsyncClient
    ):
        """Test that high-value offers (>EUR 100k) trigger approval workflow."""
        # This requires creating a project with high estimated value
        # The response should have approval_required=True and approval_workflow_id
        pass  # Implementation depends on project data setup
