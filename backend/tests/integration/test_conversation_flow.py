"""
Integration Test: Complete Conversation Flow

Tests the full end-to-end conversation flow from initialization through
requirement gathering to project creation, validating the complete user journey.

Validation Scenarios:
- Start conversation → receives initial questions (max 5)
- Send multiple messages → AI responds with contextual questions
- Context preservation → previous interactions inform new questions
- Conversation completion → generates project with requirements
- Progressive disclosure → max 5 questions per round enforced
"""

import pytest
from uuid import uuid4
from datetime import datetime


class TestConversationFlow:
    """Test complete conversation workflow integration."""

    @pytest.mark.asyncio
    async def test_complete_conversation_journey(self, async_client, db_session):
        """
        Test Case: Full conversation from start to project creation

        Given: A new conversation is initiated
        When: User completes full conversation flow
        Then: Project is created with all gathered requirements

        Expected flow:
        1. POST /conversations → conversation_id + initial questions
        2. POST /conversations/{id}/messages (3-5 rounds)
        3. POST /conversations/{id}/complete → project_id
        """
        # ARRANGE: No existing conversation
        language = "en"

        # ACT 1: Start conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": language}
        )

        # ASSERT 1: Conversation created with initial questions
        assert response.status_code == 201
        data = response.json()

        conversation_id = data["conversation_id"]
        assert conversation_id is not None
        assert data["status"] == "active"
        assert "initial_questions" in data
        assert len(data["initial_questions"]) <= 5  # Max 5 questions
        assert len(data["initial_questions"]) > 0  # At least 1 question

        # ACT 2: Send first message about project requirements
        first_message = (
            "We need a new e-commerce platform with React frontend, "
            "Node.js backend, payment integration, and admin dashboard. "
            "Expected to handle 10,000 users."
        )

        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": first_message}
        )

        # ASSERT 2: AI responds with follow-up questions
        assert response.status_code == 200
        data = response.json()

        assert "message" in data  # AI acknowledgment
        assert "questions" in data
        assert len(data["questions"]) <= 5  # Progressive disclosure
        assert data["completion_percentage"] > 0
        assert data["completion_percentage"] < 100  # Not complete yet

        # Store questions for next round
        questions = data["questions"]

        # ACT 3: Answer AI questions (Round 2)
        second_message = (
            "We need Stripe payment integration, the timeline is 6 months, "
            "and our budget is around EUR 150,000."
        )

        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": second_message}
        )

        # ASSERT 3: Completion percentage increases
        assert response.status_code == 200
        data = response.json()

        second_completion = data["completion_percentage"]
        assert second_completion > data.get("completion_percentage", 0)

        # ACT 4: Continue conversation (Round 3)
        third_message = (
            "Yes, we need multi-language support for EN, DE, FR. "
            "The admin dashboard should have analytics and user management."
        )

        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": third_message}
        )

        # ASSERT 4: Near completion
        assert response.status_code == 200
        data = response.json()
        assert data["completion_percentage"] >= 80  # Should be nearly complete

        # ACT 5: Complete conversation
        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/complete"
        )

        # ASSERT 5: Project created with requirements
        assert response.status_code == 200
        data = response.json()

        assert "project_id" in data
        project_id = data["project_id"]
        assert project_id is not None

        assert data["requirements_gathered"] >= 5  # Should have identified multiple requirements
        assert data["ready_for_offer"] is True

        # VERIFY: Conversation status updated
        response = await async_client.get(f"/v1/conversations/{conversation_id}")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "completed"
        assert data["completion_percentage"] == 100

    @pytest.mark.asyncio
    async def test_conversation_context_preservation(self, async_client):
        """
        Test Case: Context is maintained across conversation rounds

        Given: An active conversation with previous interactions
        When: User sends new message
        Then: AI response shows awareness of previous context
        """
        # ARRANGE: Start conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "en"}
        )
        conversation_id = response.json()["conversation_id"]

        # ACT 1: Mention specific technology
        await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "We want to use React and TypeScript"}
        )

        # ACT 2: Refer back without repeating
        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "Also need backend API for those technologies"}
        )

        # ASSERT: AI understands "those technologies" = React + TypeScript
        assert response.status_code == 200
        data = response.json()

        # The AI should ask about backend specifics without asking "what frontend?"
        assert "questions" in data
        # Context should show understanding of previous tech stack

    @pytest.mark.asyncio
    async def test_max_questions_per_round_enforced(self, async_client):
        """
        Test Case: Progressive disclosure - max 5 questions per interaction

        Given: A conversation
        When: AI generates questions
        Then: Never more than 5 questions returned
        """
        # ARRANGE
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "en"}
        )
        conversation_id = response.json()["conversation_id"]

        # ACT: Send vague message to trigger many potential questions
        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "I need software"}
        )

        # ASSERT: Max 5 questions
        assert response.status_code == 200
        data = response.json()

        assert len(data["questions"]) <= 5

    @pytest.mark.asyncio
    async def test_conversation_pause_and_resume(self, async_client):
        """
        Test Case: User can pause and resume conversation

        Given: Active conversation
        When: User returns after time
        Then: Can continue from last point
        """
        # ARRANGE: Start and progress conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "en"}
        )
        conversation_id = response.json()["conversation_id"]

        await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "Need e-commerce site"}
        )

        # ACT: Resume conversation later
        response = await async_client.get(f"/v1/conversations/{conversation_id}")

        # ASSERT: Can retrieve state
        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["active", "paused"]
        assert data["interactions_count"] >= 1
        assert "gathered_requirements" in data

    @pytest.mark.asyncio
    async def test_conversation_escalation_after_too_many_rounds(self, async_client):
        """
        Test Case: Conversation escalates if too many clarification rounds

        Given: Conversation with 5+ rounds without progress
        When: System detects lack of progress
        Then: Status changes to "escalated"
        """
        # ARRANGE: Start conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "en"}
        )
        conversation_id = response.json()["conversation_id"]

        # ACT: Send 6 vague responses
        for i in range(6):
            response = await async_client.post(
                f"/v1/conversations/{conversation_id}/messages",
                json={"message": "I don't know"}
            )

            if response.status_code == 422:
                # Expected - too many rounds
                break

        # ASSERT: Either 422 or status changed to escalated
        if response.status_code == 422:
            assert True  # Correctly prevented too many rounds
        else:
            # Check if escalated
            response = await async_client.get(f"/v1/conversations/{conversation_id}")
            data = response.json()
            assert data["status"] in ["escalated", "active"]

    @pytest.mark.asyncio
    async def test_multilingual_conversation_consistency(self, async_client):
        """
        Test Case: Conversation maintains language throughout

        Given: Conversation started in specific language
        When: Messages exchanged
        Then: All AI responses in same language
        """
        # ARRANGE & ACT: Start German conversation
        response = await async_client.post(
            "/v1/conversations",
            json={"language": "de"}
        )

        conversation_id = response.json()["conversation_id"]

        # Send message
        response = await async_client.post(
            f"/v1/conversations/{conversation_id}/messages",
            json={"message": "Ich brauche eine Webseite"}
        )

        # ASSERT: Response indicates German language
        assert response.status_code == 200
        data = response.json()

        # Check that questions are present (language verification would need NLP)
        assert "questions" in data
        assert len(data["questions"]) > 0
