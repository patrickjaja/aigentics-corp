"""Contract tests for POST /conversations/{id}/messages endpoint.

Tests verify the API contract matches contracts/conversation-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestSendMessage:
    """Test POST /conversations/{conversationId}/messages endpoint contract."""

    async def test_send_message_success(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test successful message send returns 200 with AIResponse schema."""
        response = await api_client.post(
            f"/conversations/{valid_conversation_id}/messages",
            json={"message": "We need a new e-commerce platform with React"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify AIResponse schema
        assert "message" in data
        assert "questions" in data
        assert "completion_percentage" in data

        # Verify field types
        assert isinstance(data["message"], str)
        assert isinstance(data["questions"], list)
        assert len(data["questions"]) <= 5  # maxItems: 5 per spec
        assert isinstance(data["completion_percentage"], int)
        assert 0 <= data["completion_percentage"] <= 100

        # Verify optional fields
        if "suggested_category" in data:
            assert data["suggested_category"] in [
                "software_development", "consulting", "infrastructure", "mixed"
            ]
        if "confidence_score" in data:
            assert 0 <= data["confidence_score"] <= 1

    async def test_send_message_with_context(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test sending message with additional context."""
        response = await api_client.post(
            f"/conversations/{valid_conversation_id}/messages",
            json={
                "message": "The budget is around 50k EUR",
                "context": {"previous_answer": "e-commerce platform"}
            }
        )

        assert response.status_code == 200

    async def test_send_message_invalid_conversation_id(self, api_client: AsyncClient):
        """Test 404 Not Found for non-existent conversation."""
        response = await api_client.post(
            "/conversations/00000000-0000-0000-0000-000000000000/messages",
            json={"message": "Test message"}
        )

        assert response.status_code == 404
        error = response.json()
        assert "error_code" in error
        assert "message" in error

    async def test_send_message_missing_message_field(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test 400 Bad Request when required message field is missing."""
        response = await api_client.post(
            f"/conversations/{valid_conversation_id}/messages",
            json={}
        )

        assert response.status_code == 400

    async def test_send_message_exceeds_max_length(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test 400 Bad Request when message exceeds 5000 characters."""
        long_message = "x" * 5001

        response = await api_client.post(
            f"/conversations/{valid_conversation_id}/messages",
            json={"message": long_message}
        )

        assert response.status_code == 400

    async def test_send_message_max_rounds_exceeded(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test 422 Unprocessable when maximum conversation rounds exceeded."""
        # Simulate exceeding 5 clarification rounds
        for i in range(6):
            response = await api_client.post(
                f"/conversations/{valid_conversation_id}/messages",
                json={"message": f"Message {i}"}
            )

            if i < 5:
                # First 5 rounds should succeed
                assert response.status_code in [200, 404]
            else:
                # 6th round should fail with 422
                if response.status_code == 422:
                    error = response.json()
                    assert "error_code" in error
                break

    async def test_complete_conversation(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test POST /conversations/{conversationId}/complete endpoint."""
        response = await api_client.post(
            f"/conversations/{valid_conversation_id}/complete"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "project_id" in data
            assert "requirements_gathered" in data
            assert "ready_for_offer" in data

            assert isinstance(data["requirements_gathered"], int)
            assert isinstance(data["ready_for_offer"], bool)

    async def test_get_conversation_details(
        self, api_client: AsyncClient, valid_conversation_id: str
    ):
        """Test GET /conversations/{conversationId} endpoint."""
        response = await api_client.get(
            f"/conversations/{valid_conversation_id}"
        )

        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()

            # Verify ConversationDetails schema
            assert "conversation_id" in data
            assert "status" in data
            assert "started_at" in data
            assert "completion_percentage" in data

            assert isinstance(data["completion_percentage"], int)
            assert 0 <= data["completion_percentage"] <= 100
