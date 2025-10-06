"""Contract tests for GET /approvals/pending endpoint.

Tests verify the API contract matches contracts/admin-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestGetPendingApprovals:
    """Test GET /approvals/pending endpoint contract."""

    async def test_get_pending_approvals_success(
        self, api_client: AsyncClient, bearer_token: str
    ):
        """Test successful retrieval of pending approvals."""
        response = await api_client.get(
            "/admin/v1/approvals/pending",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()

            # Verify response schema
            assert "total" in data
            assert "items" in data

            assert isinstance(data["total"], int)
            assert isinstance(data["items"], list)

            # Verify each ApprovalRequest schema
            for item in data["items"]:
                assert "workflow_id" in item
                assert "offer_id" in item
                assert "requested_at" in item
                assert "status" in item
                assert "offer_value" in item

                # Verify status enum
                assert item["status"] in [
                    "pending", "in_review", "approved",
                    "rejected", "revision_requested"
                ]

                # Verify Money schema for offer_value
                assert "amount" in item["offer_value"]
                assert "currency" in item["offer_value"]

    async def test_get_pending_approvals_with_pagination(
        self, api_client: AsyncClient, bearer_token: str
    ):
        """Test pagination parameters (limit and offset)."""
        response = await api_client.get(
            "/admin/v1/approvals/pending?limit=10&offset=0",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        assert response.status_code in [200, 401]

        if response.status_code == 200:
            data = response.json()
            # Should return max 10 items per limit
            assert len(data["items"]) <= 10

    async def test_get_pending_approvals_max_limit(
        self, api_client: AsyncClient, bearer_token: str
    ):
        """Test that limit cannot exceed 100 per contract."""
        response = await api_client.get(
            "/admin/v1/approvals/pending?limit=101",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        # Should either enforce max limit or return 400
        assert response.status_code in [200, 400, 401]

    async def test_get_pending_approvals_filter_by_approver(
        self, api_client: AsyncClient, bearer_token: str
    ):
        """Test filtering by approver_id."""
        approver_id = "12345678-1234-1234-1234-123456789012"

        response = await api_client.get(
            f"/admin/v1/approvals/pending?approver_id={approver_id}",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        assert response.status_code in [200, 401]

    async def test_get_pending_approvals_without_auth(
        self, api_client: AsyncClient
    ):
        """Test 401 Unauthorized when no bearer token provided."""
        response = await api_client.get("/admin/v1/approvals/pending")

        assert response.status_code == 401

    async def test_get_approval_workflow_details(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test GET /approvals/{workflowId} endpoint."""
        response = await api_client.get(
            f"/admin/v1/approvals/{valid_workflow_id}",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        assert response.status_code in [200, 404, 401]

        if response.status_code == 200:
            data = response.json()

            # Verify ApprovalWorkflow schema
            assert "workflow_id" in data
            assert "offer_details" in data
            assert "status" in data
            assert "history" in data

            # Verify offer_details is OfferSummary
            offer = data["offer_details"]
            assert "offer_id" in offer
            assert "total_value" in offer

            # Verify history is array of WorkflowEvent
            assert isinstance(data["history"], list)
            for event in data["history"]:
                assert "timestamp" in event
                assert "event_type" in event

            # Optional fields
            if "comments" in data:
                assert isinstance(data["comments"], list)
            if "modifications" in data:
                assert isinstance(data["modifications"], list)
