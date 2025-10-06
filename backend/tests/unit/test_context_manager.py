"""
Unit tests for conversation context manager.

Tests context extraction, requirement gathering, completion scoring,
and conversation state management to ensure 100% coverage of business logic.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List

from src.services.conversation.context_manager import ContextManager


class TestContextManagerInitialization:
    """Test cases for ContextManager initialization."""

    def test_context_manager_creation(self):
        """Test that ContextManager initializes correctly."""
        manager = ContextManager()
        assert manager is not None
        assert manager.category_keywords is not None
        assert len(manager.category_keywords) > 0

    def test_required_categories_defined(self):
        """Test that required categories are properly defined."""
        manager = ContextManager()
        assert "project_type" in manager.REQUIRED_CATEGORIES
        assert "tech_stack" in manager.REQUIRED_CATEGORIES
        assert "team_size" in manager.REQUIRED_CATEGORIES
        assert "timeline" in manager.REQUIRED_CATEGORIES
        assert "budget" in manager.REQUIRED_CATEGORIES
        assert "complexity" in manager.REQUIRED_CATEGORIES

    def test_keyword_index_built(self):
        """Test that keyword index is properly built."""
        manager = ContextManager()
        keywords = manager._build_keyword_index()

        # Check that all required categories have keywords
        for category in manager.REQUIRED_CATEGORIES:
            assert category in keywords
            assert len(keywords[category]) > 0


class TestRequirementExtraction:
    """Test cases for requirement extraction from messages."""

    @pytest.mark.asyncio
    async def test_extract_project_type(self):
        """Test extracting project type from message."""
        manager = ContextManager()
        message = "I need a web application for my business"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        assert len(requirements) > 0
        # Should detect "web" keyword
        assert any("project_type" in req or "web" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_tech_stack(self):
        """Test extracting technology stack from message."""
        manager = ContextManager()
        message = "We want to use React for frontend and Python for backend"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should detect both react and python
        assert any("react" in req.lower() for req in requirements)
        assert any("python" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_multiple_technologies(self):
        """Test extracting multiple technologies."""
        manager = ContextManager()
        message = "Stack: React, Node.js, PostgreSQL, Docker, AWS"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should detect multiple technologies
        assert len(requirements) >= 4
        techs = ["react", "node", "postgres", "docker", "aws"]
        for tech in techs:
            assert any(tech in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_numbers_users(self):
        """Test extracting user count from message."""
        manager = ContextManager()
        message = "We expect about 10,000 concurrent users"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should extract user count
        assert any("10" in req and "users" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_numbers_budget(self):
        """Test extracting budget from message."""
        manager = ContextManager()
        message = "Our budget is €50,000 for this project"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should extract budget
        assert any("50" in req and "budget" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_numbers_timeline(self):
        """Test extracting timeline from message."""
        manager = ContextManager()
        message = "We need this completed in 3 months"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should extract timeline
        assert any("3" in req and "timeline" in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_features(self):
        """Test extracting features from message."""
        manager = ContextManager()
        message = "Need user authentication, payment processing, and email notifications"
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        # Should detect features
        features = ["authentication", "payment", "email"]
        for feature in features:
            assert any(feature in req.lower() for req in requirements)

    @pytest.mark.asyncio
    async def test_extract_requirements_no_duplicates(self):
        """Test that duplicate requirements are not extracted."""
        manager = ContextManager()
        message = "We need React frontend"
        context = {"gathered_requirements": ["technology: react"]}

        requirements = await manager.extract_requirements(message, context)

        # Should not include already gathered requirement
        react_count = sum(1 for req in requirements if "react" in req.lower())
        assert react_count == 0

    @pytest.mark.asyncio
    async def test_extract_requirements_empty_message(self):
        """Test extracting requirements from empty message."""
        manager = ContextManager()
        message = ""
        context = {"gathered_requirements": []}

        requirements = await manager.extract_requirements(message, context)

        assert isinstance(requirements, list)
        assert len(requirements) == 0


class TestNumberExtraction:
    """Test cases for number extraction (users, budget, timeline)."""

    def test_extract_users_simple(self):
        """Test extracting simple user count."""
        manager = ContextManager()
        message = "100 users"
        numbers = manager._extract_numbers(message)

        assert len(numbers) > 0
        assert any("100" in num and "users" in num for num in numbers)

    def test_extract_users_with_commas(self):
        """Test extracting user count with comma separators."""
        manager = ContextManager()
        message = "10,000 concurrent users"
        numbers = manager._extract_numbers(message)

        assert len(numbers) > 0
        assert any("10,000" in num or "10000" in num for num in numbers)

    def test_extract_budget_euro(self):
        """Test extracting budget in euros."""
        manager = ContextManager()
        message = "Budget is €25,000"
        numbers = manager._extract_numbers(message)

        assert len(numbers) > 0
        assert any("25" in num and "budget" in num.lower() for num in numbers)

    def test_extract_timeline_weeks(self):
        """Test extracting timeline in weeks."""
        manager = ContextManager()
        message = "Complete in 8 weeks"
        numbers = manager._extract_numbers(message)

        assert len(numbers) > 0
        assert any("8" in num and "timeline" in num.lower() for num in numbers)

    def test_extract_timeline_months(self):
        """Test extracting timeline in months."""
        manager = ContextManager()
        message = "Project duration: 6 months"
        numbers = manager._extract_numbers(message)

        assert len(numbers) > 0
        assert any("6" in num and "timeline" in num.lower() for num in numbers)


class TestContextUpdate:
    """Test cases for context updating."""

    @pytest.mark.asyncio
    async def test_update_context_basic(self):
        """Test basic context update."""
        manager = ContextManager()
        current_context = {}
        messages = [
            {"type": "user_message", "content": "I need a web app"},
        ]
        gathered_requirements = ["project_type: web"]

        updated_context = await manager.update_context(
            current_context,
            messages,
            gathered_requirements,
        )

        assert "categorized_requirements" in updated_context
        assert "confidence_scores" in updated_context
        assert "current_topic" in updated_context
        assert "last_updated" in updated_context

    @pytest.mark.asyncio
    async def test_update_context_categorization(self):
        """Test that requirements are properly categorized."""
        manager = ContextManager()
        current_context = {}
        messages = []
        gathered_requirements = [
            "project_type: web",
            "technology: react",
            "technology: python",
            "budget: €50000",
        ]

        updated_context = await manager.update_context(
            current_context,
            messages,
            gathered_requirements,
        )

        categorized = updated_context["categorized_requirements"]
        assert "project_type" in categorized
        assert "technology" in categorized
        assert "budget" in categorized
        assert len(categorized["technology"]) == 2

    @pytest.mark.asyncio
    async def test_update_context_confidence_scores(self):
        """Test confidence score calculation."""
        manager = ContextManager()
        current_context = {}
        messages = []
        gathered_requirements = [
            "project_type: web",
            "tech_stack: react",
        ]

        updated_context = await manager.update_context(
            current_context,
            messages,
            gathered_requirements,
        )

        scores = updated_context["confidence_scores"]
        # project_type should have confidence > 0
        assert scores.get("project_type", 0) > 0
        # tech_stack should have confidence > 0
        assert scores.get("tech_stack", 0) > 0

    @pytest.mark.asyncio
    async def test_update_context_current_topic(self):
        """Test current topic determination."""
        manager = ContextManager()
        current_context = {}
        messages = []
        gathered_requirements = ["project_type: web"]

        updated_context = await manager.update_context(
            current_context,
            messages,
            gathered_requirements,
        )

        # Should identify missing topics
        assert "current_topic" in updated_context
        assert updated_context["current_topic"] in manager.REQUIRED_CATEGORIES


class TestConfidenceScoring:
    """Test cases for confidence score calculation."""

    def test_calculate_confidence_empty(self):
        """Test confidence calculation with no requirements."""
        manager = ContextManager()
        categorized = {}
        scores = manager._calculate_confidence_scores(categorized)

        # All scores should be 0
        for category in manager.REQUIRED_CATEGORIES:
            assert scores[category] == 0.0

    def test_calculate_confidence_single_item(self):
        """Test confidence calculation with single item per category."""
        manager = ContextManager()
        categorized = {"project_type": ["web"]}
        scores = manager._calculate_confidence_scores(categorized)

        # project_type should have confidence of at least 0.5
        assert scores["project_type"] >= 0.5

    def test_calculate_confidence_multiple_items(self):
        """Test confidence calculation with multiple items."""
        manager = ContextManager()
        categorized = {"tech_stack": ["react", "python", "postgres"]}
        scores = manager._calculate_confidence_scores(categorized)

        # More items should increase confidence
        assert scores["tech_stack"] > 0.5

    def test_calculate_confidence_capped_at_one(self):
        """Test that confidence is capped at 1.0."""
        manager = ContextManager()
        # Many items should still cap at 1.0
        categorized = {"tech_stack": ["item" + str(i) for i in range(10)]}
        scores = manager._calculate_confidence_scores(categorized)

        assert scores["tech_stack"] <= 1.0


class TestTopicDetermination:
    """Test cases for current topic determination."""

    def test_determine_topic_low_confidence(self):
        """Test topic determination with low confidence areas."""
        manager = ContextManager()
        categorized = {"project_type": ["web"]}
        confidence_scores = {
            "project_type": 0.75,
            "tech_stack": 0.0,
            "team_size": 0.0,
            "timeline": 0.0,
            "budget": 0.0,
            "complexity": 0.0,
        }
        messages = []

        topic = manager._determine_current_topic(
            categorized,
            confidence_scores,
            messages,
        )

        # Should return a low-confidence category
        assert topic in manager.REQUIRED_CATEGORIES
        assert confidence_scores[topic] < manager.MIN_CONFIDENCE

    def test_determine_topic_all_confident(self):
        """Test topic determination when all categories confident."""
        manager = ContextManager()
        categorized = {cat: ["value"] for cat in manager.REQUIRED_CATEGORIES}
        confidence_scores = {cat: 0.8 for cat in manager.REQUIRED_CATEGORIES}
        messages = []

        topic = manager._determine_current_topic(
            categorized,
            confidence_scores,
            messages,
        )

        # Should focus on general or completion
        assert topic in ["general", "completion"]


class TestCompletionCalculation:
    """Test cases for completion score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_completion_empty(self):
        """Test completion calculation with no data."""
        manager = ContextManager()
        context = {"confidence_scores": {}}
        gathered_requirements = []

        completion = await manager.calculate_completion(
            context,
            gathered_requirements,
        )

        assert completion == 0.0

    @pytest.mark.asyncio
    async def test_calculate_completion_partial(self):
        """Test completion calculation with partial data."""
        manager = ContextManager()
        context = {
            "confidence_scores": {
                "project_type": 0.75,
                "tech_stack": 0.5,
                "team_size": 0.0,
                "timeline": 0.0,
                "budget": 0.0,
                "complexity": 0.0,
            }
        }
        gathered_requirements = ["project_type: web", "tech_stack: react"]

        completion = await manager.calculate_completion(
            context,
            gathered_requirements,
        )

        # Should be partial completion (around 20-30%)
        assert 0.0 < completion < 0.5

    @pytest.mark.asyncio
    async def test_calculate_completion_full(self):
        """Test completion calculation with full data."""
        manager = ContextManager()
        context = {
            "confidence_scores": {
                cat: 0.9 for cat in manager.REQUIRED_CATEGORIES
            }
        }
        gathered_requirements = [
            f"{cat}: value" for cat in manager.REQUIRED_CATEGORIES
        ] * 5  # Many requirements

        completion = await manager.calculate_completion(
            context,
            gathered_requirements,
        )

        # Should be high completion (>80%)
        assert completion > 0.8

    @pytest.mark.asyncio
    async def test_calculate_completion_capped_at_one(self):
        """Test that completion is capped at 1.0."""
        manager = ContextManager()
        context = {
            "confidence_scores": {
                cat: 1.0 for cat in manager.REQUIRED_CATEGORIES
            }
        }
        gathered_requirements = ["req"] * 100

        completion = await manager.calculate_completion(
            context,
            gathered_requirements,
        )

        assert completion <= 1.0


class TestMissingInformation:
    """Test cases for missing information detection."""

    def test_get_missing_information_all_missing(self):
        """Test getting missing information when nothing provided."""
        manager = ContextManager()
        context = {"confidence_scores": {cat: 0.0 for cat in manager.REQUIRED_CATEGORIES}}

        missing = manager.get_missing_information(context)

        # All categories should be missing
        assert len(missing) == len(manager.REQUIRED_CATEGORIES)
        for cat in manager.REQUIRED_CATEGORIES:
            assert cat in missing

    def test_get_missing_information_partial(self):
        """Test getting missing information with some provided."""
        manager = ContextManager()
        context = {
            "confidence_scores": {
                "project_type": 0.75,
                "tech_stack": 0.8,
                "team_size": 0.0,
                "timeline": 0.0,
                "budget": 0.0,
                "complexity": 0.0,
            }
        }

        missing = manager.get_missing_information(context)

        # Should be missing 4 categories
        assert len(missing) == 4
        assert "team_size" in missing
        assert "timeline" in missing
        assert "budget" in missing
        assert "complexity" in missing
        assert "project_type" not in missing
        assert "tech_stack" not in missing

    def test_get_missing_information_none_missing(self):
        """Test getting missing information when all provided."""
        manager = ContextManager()
        context = {
            "confidence_scores": {
                cat: 0.9 for cat in manager.REQUIRED_CATEGORIES
            }
        }

        missing = manager.get_missing_information(context)

        # Nothing should be missing
        assert len(missing) == 0


class TestClarificationDecision:
    """Test cases for clarification question decision logic."""

    def test_should_ask_clarification_low_completion(self):
        """Test that clarification should be asked with low completion."""
        manager = ContextManager()
        context = {"completion_percentage": 50.0}  # 50% completion
        round_count = 2

        should_ask = manager.should_ask_clarification(context, round_count)

        # Should ask more questions
        assert should_ask is True

    def test_should_ask_clarification_high_completion(self):
        """Test that clarification should not be asked with high completion."""
        manager = ContextManager()
        context = {"completion_percentage": 85.0}  # 85% completion
        round_count = 2

        should_ask = manager.should_ask_clarification(context, round_count)

        # Should not ask more questions
        assert should_ask is False

    def test_should_ask_clarification_max_rounds(self):
        """Test that clarification stops after max rounds."""
        manager = ContextManager()
        context = {"completion_percentage": 50.0}  # Low completion
        round_count = 5  # Max rounds reached

        should_ask = manager.should_ask_clarification(context, round_count)

        # Should not ask more questions (max rounds)
        assert should_ask is False

    def test_should_ask_clarification_zero_rounds(self):
        """Test clarification decision at start."""
        manager = ContextManager()
        context = {"completion_percentage": 20.0}
        round_count = 0

        should_ask = manager.should_ask_clarification(context, round_count)

        # Should ask questions
        assert should_ask is True


class TestAnsweredQuestions:
    """Test cases for answered questions identification."""

    def test_identify_answered_questions_simple(self):
        """Test identifying answered questions."""
        manager = ContextManager()
        messages = [
            {"type": "ai_question", "content": "What type of project?"},
            {"type": "user_message", "content": "A web application"},
        ]
        categorized = {}

        answered = manager._identify_answered_questions(messages, categorized)

        assert len(answered) == 1
        assert "What type of project?" in answered

    def test_identify_answered_questions_multiple(self):
        """Test identifying multiple answered questions."""
        manager = ContextManager()
        messages = [
            {"type": "ai_question", "content": "Question 1?"},
            {"type": "user_message", "content": "Answer 1"},
            {"type": "ai_question", "content": "Question 2?"},
            {"type": "user_message", "content": "Answer 2"},
        ]
        categorized = {}

        answered = manager._identify_answered_questions(messages, categorized)

        assert len(answered) == 2
        assert "Question 1?" in answered
        assert "Question 2?" in answered

    def test_identify_answered_questions_unanswered(self):
        """Test that unanswered questions are not included."""
        manager = ContextManager()
        messages = [
            {"type": "ai_question", "content": "Unanswered question?"},
            # No user response
        ]
        categorized = {}

        answered = manager._identify_answered_questions(messages, categorized)

        assert len(answered) == 0


class TestRequirementCategorization:
    """Test cases for requirement categorization."""

    def test_categorize_requirements_simple(self):
        """Test categorizing simple requirements."""
        manager = ContextManager()
        requirements = [
            "project_type: web",
            "technology: react",
            "budget: €50000",
        ]

        categorized = manager._categorize_requirements(requirements)

        assert "project_type" in categorized
        assert "technology" in categorized
        assert "budget" in categorized
        assert categorized["project_type"] == ["web"]
        assert categorized["technology"] == ["react"]

    def test_categorize_requirements_multiple_in_category(self):
        """Test categorizing multiple requirements in same category."""
        manager = ContextManager()
        requirements = [
            "technology: react",
            "technology: python",
            "technology: postgres",
        ]

        categorized = manager._categorize_requirements(requirements)

        assert "technology" in categorized
        assert len(categorized["technology"]) == 3
        assert "react" in categorized["technology"]
        assert "python" in categorized["technology"]
        assert "postgres" in categorized["technology"]

    def test_categorize_requirements_without_category(self):
        """Test categorizing requirements without explicit category."""
        manager = ContextManager()
        requirements = [
            "Some general requirement",
            "Another detail",
        ]

        categorized = manager._categorize_requirements(requirements)

        assert "general" in categorized
        assert len(categorized["general"]) == 2
