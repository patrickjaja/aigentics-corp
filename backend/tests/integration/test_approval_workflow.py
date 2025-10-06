"""
Integration Test: High-Value Approval Workflow

Tests the approval workflow for offers exceeding EUR 100,000 as required
by FR-010 and the approval domain model.

Business Rules:
- Offers > EUR 100,000 require manager approval
- Approval workflow tracks all decisions
- Managers can approve, reject, or request revisions
- Offer modifications create new versions
- Customer notified of final decision

Validation Scenarios:
- High-value offer triggers automatic approval workflow
- Manager can review and approve/reject
- Modifications during approval create new version
- Approval history maintained for audit
- Notifications sent to appropriate parties
"""

import pytest
from uuid import uuid4
from decimal import Decimal


class TestApprovalWorkflow:
    """Test high-value offer approval workflow integration."""

    @pytest.mark.asyncio
    async def test_high_value_offer_triggers_approval_workflow(
        self, async_client, high_value_project
    ):
        """
        Test Case: Offer >EUR 100k automatically creates approval workflow

        Given: Project estimated at >EUR 100,000
        When: Offer is generated
        Then: Approval workflow automatically created

        Business Rule: FR-010 - High-value offers need approval
        """
        # ARRANGE: High-value project (>EUR 100k)
        project_id = high_value_project["id"]
        conversation_id = high_value_project["conversation_id"]

        # ACT: Generate offer
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        # ASSERT: Offer created with approval required
        assert response.status_code == 201
        data = response.json()

        assert data["approval_required"] is True
        assert "approval_workflow_id" in data
        assert data["status"] == "pending_approval"

        workflow_id = data["approval_workflow_id"]

        # Verify total value exceeds threshold
        total_value = float(data["total_value"]["amount"])
        assert total_value > 100000.00

        # Verify workflow created
        workflow_response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers={"Authorization": "Bearer admin_token"}
        )

        assert workflow_response.status_code == 200
        workflow_data = workflow_response.json()

        assert workflow_data["workflow_id"] == workflow_id
        assert workflow_data["status"] == "pending"

    @pytest.mark.asyncio
    async def test_low_value_offer_skips_approval(
        self, async_client, sample_conversation
    ):
        """
        Test Case: Offer <EUR 100k does not require approval

        Given: Project estimated at <EUR 100,000
        When: Offer is generated
        Then: No approval workflow created, status is "draft"

        Business Rule: Only high-value offers need approval
        """
        # ARRANGE: Regular project (<EUR 100k)
        project_id = sample_conversation["project_id"]
        conversation_id = sample_conversation["id"]

        # ACT: Generate offer
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        # ASSERT: No approval required
        assert response.status_code == 201
        data = response.json()

        assert data["approval_required"] is False
        assert "approval_workflow_id" not in data or data["approval_workflow_id"] is None
        assert data["status"] == "draft"

        # Verify total value under threshold
        total_value = float(data["total_value"]["amount"])
        assert total_value <= 100000.00

    @pytest.mark.asyncio
    async def test_manager_can_view_pending_approvals(
        self, async_client, manager_token, pending_approval_offers
    ):
        """
        Test Case: Sales manager sees list of pending approvals

        Given: Multiple offers pending approval
        When: Manager requests pending approvals list
        Then: Receives all offers awaiting decision

        API: GET /admin/approvals/pending
        """
        # ARRANGE: Manager authentication
        headers = {"Authorization": f"Bearer {manager_token}"}

        # ACT: Get pending approvals
        response = await async_client.get(
            "/v1/admin/approvals/pending",
            headers=headers
        )

        # ASSERT: List returned
        assert response.status_code == 200
        data = response.json()

        assert "total" in data
        assert "items" in data
        assert data["total"] >= len(pending_approval_offers)

        # Verify each item has required fields
        for item in data["items"]:
            assert "workflow_id" in item
            assert "offer_id" in item
            assert "offer_value" in item
            assert "requested_at" in item
            assert "status" in item
            assert item["status"] == "pending"

    @pytest.mark.asyncio
    async def test_manager_starts_review_locks_workflow(
        self, async_client, manager_token, pending_approval
    ):
        """
        Test Case: Starting review locks workflow to prevent concurrent edits

        Given: Pending approval workflow
        When: Manager starts review
        Then: Workflow locked to this manager

        Business Rule: Prevent concurrent approval attempts
        """
        # ARRANGE
        workflow_id = pending_approval["workflow_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        # ACT: Start review
        response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/review",
            headers=headers
        )

        # ASSERT: Review started and locked
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "in_review"
        assert "locked_by" in data
        assert "locked_until" in data

        # Verify cannot be locked by another manager
        other_manager_headers = {"Authorization": "Bearer other_manager_token"}

        conflict_response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/review",
            headers=other_manager_headers
        )

        assert conflict_response.status_code == 409  # Conflict

    @pytest.mark.asyncio
    async def test_manager_approves_offer(
        self, async_client, manager_token, in_review_approval
    ):
        """
        Test Case: Manager approves high-value offer

        Given: Approval workflow in review
        When: Manager submits approval decision
        Then: Offer status changes to "approved" and customer notified

        Business Rule: Approved offers can be sent to customers
        """
        # ARRANGE
        workflow_id = in_review_approval["workflow_id"]
        offer_id = in_review_approval["offer_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        decision = {
            "outcome": "approved",
            "reason": "Project scope is clear and pricing is appropriate",
            "notify_customer": True
        }

        # ACT: Approve offer
        response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/decide",
            json=decision,
            headers=headers
        )

        # ASSERT: Decision recorded
        assert response.status_code == 200
        data = response.json()

        assert data["outcome"] == "approved"
        assert data["offer_status"] == "approved"
        assert data["customer_notified"] is True

        # Verify offer status updated
        offer_response = await async_client.get(f"/v1/offers/{offer_id}")
        offer_data = offer_response.json()

        assert offer_data["status"] == "approved"

    @pytest.mark.asyncio
    async def test_manager_rejects_offer(
        self, async_client, manager_token, in_review_approval
    ):
        """
        Test Case: Manager rejects offer with reason

        Given: Approval workflow in review
        When: Manager rejects offer
        Then: Offer status changes to "rejected" with reason recorded

        Business Rule: Rejected offers cannot be sent
        """
        # ARRANGE
        workflow_id = in_review_approval["workflow_id"]
        offer_id = in_review_approval["offer_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        decision = {
            "outcome": "rejected",
            "reason": "Budget estimate significantly exceeds customer's stated budget",
            "notify_customer": False
        }

        # ACT: Reject offer
        response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/decide",
            json=decision,
            headers=headers
        )

        # ASSERT: Rejection recorded
        assert response.status_code == 200
        data = response.json()

        assert data["outcome"] == "rejected"
        assert data["offer_status"] == "rejected"

        # Verify workflow history includes rejection reason
        workflow_response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers=headers
        )

        workflow_data = workflow_response.json()
        assert workflow_data["status"] == "rejected"
        assert any("reject" in event["event_type"].lower() for event in workflow_data["history"])

    @pytest.mark.asyncio
    async def test_manager_requests_revision(
        self, async_client, manager_token, in_review_approval
    ):
        """
        Test Case: Manager requests revisions to offer

        Given: Approval workflow in review
        When: Manager requests revisions
        Then: Workflow status is "revision_requested" with conditions

        Business Rule: Revisions trigger re-review after changes
        """
        # ARRANGE
        workflow_id = in_review_approval["workflow_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        decision = {
            "outcome": "revision_requested",
            "reason": "Hourly rate for junior developers too high",
            "conditions": [
                "Reduce junior developer rate from EUR 80 to EUR 65",
                "Add more detail to testing deliverables"
            ],
            "notify_customer": False
        }

        # ACT: Request revision
        response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/decide",
            json=decision,
            headers=headers
        )

        # ASSERT: Revision request recorded
        assert response.status_code == 200
        data = response.json()

        assert data["outcome"] == "revision_requested"

        # Verify workflow includes conditions
        workflow_response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers=headers
        )

        workflow_data = workflow_response.json()
        assert workflow_data["status"] == "revision_requested"

        # Check conditions are stored
        latest_comment = workflow_data["comments"][-1]
        assert "junior developer" in latest_comment["content"].lower()

    @pytest.mark.asyncio
    async def test_manager_modifies_offer_during_approval(
        self, async_client, manager_token, in_review_approval
    ):
        """
        Test Case: Manager can modify offer directly during approval

        Given: Approval workflow in review
        When: Manager applies modifications
        Then: New offer version created with changes

        Business Rule: Modifications create audit trail (FR-017)
        """
        # ARRANGE
        workflow_id = in_review_approval["workflow_id"]
        offer_id = in_review_approval["offer_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        # Get current offer version
        offer_response = await async_client.get(f"/v1/offers/{offer_id}")
        current_version = offer_response.json()["version"]

        modifications = {
            "modifications": [
                {
                    "path": "$.work_packages[0].hourly_rate.amount",
                    "value": "65.00",
                    "reason": "Adjusted junior developer rate to market standard"
                },
                {
                    "path": "$.work_packages[1].estimated_hours.likely",
                    "value": "120",
                    "reason": "Increased testing hours based on complexity"
                }
            ],
            "reason": "Price adjustment for competitive positioning"
        }

        # ACT: Apply modifications
        response = await async_client.patch(
            f"/v1/admin/approvals/{workflow_id}/modify-offer",
            json=modifications,
            headers=headers
        )

        # ASSERT: Modifications applied
        assert response.status_code == 200
        data = response.json()

        assert data["new_version"] == current_version + 1
        assert data["modifications_applied"] == 2

        # Verify new version created
        new_offer_response = await async_client.get(f"/v1/offers/{offer_id}")
        new_offer_data = new_offer_response.json()

        assert new_offer_data["version"] == current_version + 1

        # Verify modifications recorded in workflow
        workflow_response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers=headers
        )

        workflow_data = workflow_response.json()
        assert len(workflow_data["modifications"]) >= 2

    @pytest.mark.asyncio
    async def test_approval_workflow_audit_trail(
        self, async_client, manager_token, completed_approval
    ):
        """
        Test Case: Complete approval history maintained

        Given: Completed approval workflow
        When: Workflow history retrieved
        Then: All events recorded chronologically

        Compliance: Event sourcing for audit (Constitution IV)
        """
        # ARRANGE
        workflow_id = completed_approval["workflow_id"]
        headers = {"Authorization": f"Bearer {manager_token}"}

        # ACT: Get workflow details
        response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers=headers
        )

        # ASSERT: Complete history
        assert response.status_code == 200
        data = response.json()

        assert "history" in data
        history = data["history"]

        # Verify chronological order
        timestamps = [event["timestamp"] for event in history]
        assert timestamps == sorted(timestamps)

        # Verify key events present
        event_types = [event["event_type"] for event in history]

        expected_events = ["WorkflowInitiated", "ReviewStarted"]
        for expected in expected_events:
            assert any(expected in event_type for event_type in event_types)

    @pytest.mark.asyncio
    async def test_approval_notification_to_sales_team(
        self, async_client, notification_service, high_value_project
    ):
        """
        Test Case: Notifications sent when high-value offer created

        Given: High-value offer generated
        When: Approval workflow triggered
        Then: Sales manager notified

        Business Rule: Immediate notification for >EUR 100k opportunities
        """
        # ARRANGE
        project_id = high_value_project["id"]
        conversation_id = high_value_project["conversation_id"]

        # ACT: Generate high-value offer
        response = await async_client.post(
            "/v1/offers",
            json={
                "project_id": project_id,
                "conversation_id": conversation_id
            }
        )

        assert response.status_code == 201
        workflow_id = response.json()["approval_workflow_id"]

        # ASSERT: Notification sent
        # (This would check notification service or email queue)
        # For integration test, verify workflow indicates notification
        workflow_response = await async_client.get(
            f"/v1/admin/approvals/{workflow_id}",
            headers={"Authorization": "Bearer admin_token"}
        )

        workflow_data = workflow_response.json()

        # Check for notification event in history
        history = workflow_data["history"]
        assert any(
            "notif" in event["event_type"].lower() or "notif" in event["details"].lower()
            for event in history
        )

    @pytest.mark.asyncio
    async def test_concurrent_approval_prevention(
        self, async_client, manager_token, other_manager_token, pending_approval
    ):
        """
        Test Case: System prevents concurrent approval decisions

        Given: Approval workflow in review by one manager
        When: Another manager attempts to decide
        Then: Second manager blocked with 409 Conflict

        Business Rule: One manager per approval to avoid conflicts
        """
        # ARRANGE: First manager starts review
        workflow_id = pending_approval["workflow_id"]
        headers1 = {"Authorization": f"Bearer {manager_token}"}

        await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/review",
            headers=headers1
        )

        # ACT: Second manager tries to decide
        headers2 = {"Authorization": f"Bearer {other_manager_token}"}

        decision = {
            "outcome": "approved",
            "reason": "Looks good"
        }

        response = await async_client.post(
            f"/v1/admin/approvals/{workflow_id}/decide",
            json=decision,
            headers=headers2
        )

        # ASSERT: Blocked
        assert response.status_code in [409, 403]  # Conflict or Forbidden
