"""Contract tests for POST /conversations endpoint.

These tests verify the API contract matches the OpenAPI specification
in contracts/conversation-api.yaml
"""

import pytest
from httpx import AsyncClient


@pytest.mark.contract
class TestStartConversation:
    """Test POST /conversations endpoint contract."""

    async def test_start_conversation_success(
        self, api_client: AsyncClient, valid_language: str
    ):
        """Test successful conversation creation returns 201 with correct schema."""
        response = await api_client.post(
            "/conversations",
            json={"language": valid_language}
        )

        assert response.status_code == 201
        data = response.json()

        # Verify required fields per OpenAPI schema
        assert "conversation_id" in data
        assert "status" in data
        assert "initial_questions" in data
        assert "language" in data

        # Verify field types and constraints
        assert isinstance(data["conversation_id"], str)
        assert data["status"] in ["active", "paused", "completed", "abandoned", "escalated"]
        assert isinstance(data["initial_questions"], list)
        assert len(data["initial_questions"]) <= 5  # maxItems: 5
        assert data["language"] == valid_language

        # Verify Question schema for each initial question
        for question in data["initial_questions"]:
            assert "id" in question
            assert "text" in question
            assert "type" in question
            assert question["type"] in [
                "text", "single_choice", "multiple_choice", "number", "date"
            ]
            if question["type"] in ["single_choice", "multiple_choice"]:
                assert "options" in question

    async def test_start_conversation_with_session_id(self, api_client: AsyncClient):
        """Test conversation creation with optional session_id."""
        response = await api_client.post(
            "/conversations",
            json={"language": "en", "session_id": "test-session-123"}
        )

        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data

    async def test_start_conversation_invalid_language(self, api_client: AsyncClient):
        """Test 400 Bad Request for invalid language code."""
        response = await api_client.post(
            "/conversations",
            json={"language": "invalid"}
        )

        assert response.status_code == 400
        error = response.json()
        assert "error_code" in error
        assert "message" in error

    async def test_start_conversation_missing_language(self, api_client: AsyncClient):
        """Test 400 Bad Request when required language field is missing."""
        response = await api_client.post(
            "/conversations",
            json={}
        )

        assert response.status_code == 400

    async def test_start_conversation_all_supported_languages(self, api_client: AsyncClient):
        """Test conversation creation with all EU languages per contract."""
        supported_languages = [
            "de", "en", "fr", "es", "it", "nl", "pl", "pt",
            "cs", "da", "el", "hu", "ro", "sv", "bg", "hr",
            "et", "fi", "ga", "lt", "lv", "mt", "sk", "sl"
        ]

        for lang in supported_languages:
            response = await api_client.post(
                "/conversations",
                json={"language": lang}
            )
            # Should succeed for all supported languages
            assert response.status_code == 201

    @pytest.mark.slow
    async def test_rate_limiting(self, api_client: AsyncClient):
        """Test 429 Rate Limited response when exceeding 100 req/min."""
        # Make 101 requests to exceed rate limit
        for i in range(101):
            response = await api_client.post(
                "/conversations",
                json={"language": "en"}
            )

            if i < 100:
                # First 100 should succeed
                assert response.status_code == 201
            else:
                # 101st should be rate limited
                assert response.status_code == 429
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
                assert "X-RateLimit-Reset" in response.headers

    async def test_api_key_authentication(self):
        """Test that requests without API key are rejected."""
        async with AsyncClient(base_url="http://localhost:8000/v1") as client:
            response = await client.post(
                "/conversations",
                json={"language": "en"}
            )
            # Should require authentication
            assert response.status_code in [401, 403]
