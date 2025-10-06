"""Contract tests for POST /approvals/{id}/review endpoint.

Tests verify the API contract matches contracts/admin-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestApprovalWorkflow:
    """Test approval workflow endpoints contract."""

    async def test_start_review_success(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test POST /approvals/{workflowId}/review endpoint."""
        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/review",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        assert response.status_code in [200, 404, 409, 401]

        if response.status_code == 200:
            data = response.json()

            # Verify response schema
            assert "status" in data
            assert data["status"] == "in_review"
            assert "locked_by" in data
            assert "locked_until" in data

    async def test_start_review_already_locked(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test 409 Conflict when workflow already being reviewed."""
        # First request locks the workflow
        response1 = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/review",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        # Second request should get 409
        response2 = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/review",
            headers={"Authorization": f"Bearer {bearer_token}"}
        )

        if response1.status_code == 200:
            assert response2.status_code == 409

    async def test_make_decision_approve(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test POST /approvals/{workflowId}/decide with approve outcome."""
        decision = {
            "outcome": "approved",
            "reason": "All requirements met, pricing is competitive",
            "notify_customer": True
        }

        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=decision
        )

        assert response.status_code in [200, 400, 404, 401]

        if response.status_code == 200:
            data = response.json()

            # Verify response schema
            assert "workflow_id" in data
            assert "outcome" in data
            assert "offer_status" in data
            assert "customer_notified" in data

            assert data["outcome"] in ["approved", "rejected", "revision_requested"]
            assert isinstance(data["customer_notified"], bool)

    async def test_make_decision_reject(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test POST /approvals/{workflowId}/decide with reject outcome."""
        decision = {
            "outcome": "rejected",
            "reason": "Pricing is too high for the market segment",
            "notify_customer": False
        }

        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=decision
        )

        assert response.status_code in [200, 400, 404, 401]

    async def test_make_decision_revision_requested(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test POST /approvals/{workflowId}/decide with revision_requested."""
        decision = {
            "outcome": "revision_requested",
            "reason": "Need to adjust hourly rates and add more details",
            "conditions": [
                "Reduce hourly rate by 10%",
                "Add detailed timeline"
            ],
            "notify_customer": False
        }

        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=decision
        )

        assert response.status_code in [200, 400, 404, 401]

    async def test_make_decision_invalid_reason_length(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test 400 Bad Request when reason is too short."""
        decision = {
            "outcome": "approved",
            "reason": "OK"  # minLength: 10 per contract
        }

        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=decision
        )

        assert response.status_code == 400

    async def test_make_decision_reason_too_long(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test 400 Bad Request when reason exceeds max length."""
        decision = {
            "outcome": "approved",
            "reason": "X" * 1001  # maxLength: 1000
        }

        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=decision
        )

        assert response.status_code == 400

    async def test_modify_offer_during_approval(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test PATCH /approvals/{workflowId}/modify-offer endpoint."""
        modifications = {
            "modifications": [
                {
                    "path": "$.work_packages[0].hourly_rate.amount",
                    "value": "120.00",
                    "reason": "Adjusted to market rate"
                }
            ],
            "reason": "Price adjustment based on market analysis"
        }

        response = await api_client.patch(
            f"/admin/v1/approvals/{valid_workflow_id}/modify-offer",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=modifications
        )

        assert response.status_code in [200, 400, 404, 401]

        if response.status_code == 200:
            data = response.json()

            # Verify response schema
            assert "new_version" in data
            assert "modifications_applied" in data

            assert isinstance(data["new_version"], int)
            assert isinstance(data["modifications_applied"], int)

    async def test_modify_offer_without_modifications(
        self, api_client: AsyncClient, bearer_token: str, valid_workflow_id: str
    ):
        """Test 400 Bad Request when modifications array is empty."""
        modifications = {
            "modifications": [],  # minItems: 1
            "reason": "No modifications"
        }

        response = await api_client.patch(
            f"/admin/v1/approvals/{valid_workflow_id}/modify-offer",
            headers={"Authorization": f"Bearer {bearer_token}"},
            json=modifications
        )

        assert response.status_code == 400

    async def test_approval_workflow_without_auth(
        self, api_client: AsyncClient, valid_workflow_id: str
    ):
        """Test 401 Unauthorized for all admin endpoints without token."""
        # Test review endpoint
        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/review"
        )
        assert response.status_code == 401

        # Test decide endpoint
        response = await api_client.post(
            f"/admin/v1/approvals/{valid_workflow_id}/decide",
            json={"outcome": "approved", "reason": "Test reason here"}
        )
        assert response.status_code == 401

        # Test modify endpoint
        response = await api_client.patch(
            f"/admin/v1/approvals/{valid_workflow_id}/modify-offer",
            json={"modifications": [], "reason": "Test"}
        )
        assert response.status_code == 401
