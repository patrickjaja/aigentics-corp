"""
Conversation Context Manager

Manages conversation context, extracts requirements, and calculates completion scores.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import re
from collections import defaultdict


class ContextManager:
    """Manages conversation context and requirement extraction."""

    # Key information categories needed for project estimation
    REQUIRED_CATEGORIES = {
        "project_type": ["web", "mobile", "desktop", "api", "infrastructure"],
        "tech_stack": ["frontend", "backend", "database", "cloud"],
        "team_size": ["solo", "small", "medium", "large"],
        "timeline": ["urgent", "normal", "flexible"],
        "budget": ["low", "medium", "high", "enterprise"],
        "complexity": ["simple", "moderate", "complex", "enterprise"],
    }

    # Minimum confidence thresholds
    MIN_CONFIDENCE = 0.6
    COMPLETION_THRESHOLD = 0.8

    def __init__(self):
        self.category_keywords = self._build_keyword_index()

    def _build_keyword_index(self) -> Dict[str, List[str]]:
        """Build keyword index for category detection."""
        return {
            "project_type": [
                "website", "web app", "mobile app", "api", "backend",
                "frontend", "dashboard", "ecommerce", "platform"
            ],
            "tech_stack": [
                "react", "vue", "angular", "node", "python", "java",
                "postgres", "mysql", "mongodb", "aws", "azure", "docker"
            ],
            "team_size": [
                "alone", "solo", "team", "developers", "engineers"
            ],
            "timeline": [
                "urgent", "asap", "months", "weeks", "deadline", "flexible"
            ],
            "budget": [
                "€", "eur", "thousand", "budget", "cost", "price"
            ],
            "complexity": [
                "simple", "basic", "complex", "advanced", "enterprise",
                "integration", "microservice"
            ],
        }

    async def extract_requirements(
        self,
        message: str,
        current_context: Dict[str, Any]
    ) -> List[str]:
        """
        Extract structured requirements from user message.

        Args:
            message: User message text
            current_context: Current conversation context

        Returns:
            List of extracted requirements
        """
        requirements = []
        message_lower = message.lower()

        # Extract project type mentions
        for category, keywords in self.category_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    requirement = f"{category}: {keyword}"
                    if requirement not in current_context.get("gathered_requirements", []):
                        requirements.append(requirement)

        # Extract specific details using patterns
        requirements.extend(self._extract_numbers(message))
        requirements.extend(self._extract_technologies(message))
        requirements.extend(self._extract_features(message))

        return requirements

    def _extract_numbers(self, message: str) -> List[str]:
        """Extract numerical requirements (users, budget, timeline)."""
        requirements = []

        # User count patterns
        user_patterns = [
            r"(\d+[\d,]*)\s*(?:concurrent\s+)?users?",
            r"(\d+[\d,]*)\s*people",
        ]
        for pattern in user_patterns:
            match = re.search(pattern, message.lower())
            if match:
                requirements.append(f"scale: {match.group(1)} users")

        # Budget patterns
        budget_patterns = [
            r"€\s*(\d+[\d,]*)",
            r"(\d+[\d,]*)\s*(?:eur|euro)",
        ]
        for pattern in budget_patterns:
            match = re.search(pattern, message.lower())
            if match:
                requirements.append(f"budget: €{match.group(1)}")

        # Timeline patterns
        timeline_patterns = [
            r"(\d+)\s*(?:weeks?|months?)",
            r"by\s+(\w+\s+\d+)",
        ]
        for pattern in timeline_patterns:
            match = re.search(pattern, message.lower())
            if match:
                requirements.append(f"timeline: {match.group(1)}")

        return requirements

    def _extract_technologies(self, message: str) -> List[str]:
        """Extract mentioned technologies."""
        tech_keywords = [
            "react", "vue", "angular", "next", "nuxt",
            "node", "python", "java", "go", "rust",
            "postgres", "mysql", "mongodb", "redis",
            "aws", "azure", "gcp", "docker", "kubernetes"
        ]

        requirements = []
        message_lower = message.lower()

        for tech in tech_keywords:
            if tech in message_lower:
                requirements.append(f"technology: {tech}")

        return requirements

    def _extract_features(self, message: str) -> List[str]:
        """Extract feature mentions."""
        feature_keywords = [
            "authentication", "auth", "login", "user management",
            "payment", "checkout", "subscription",
            "search", "filtering", "sorting",
            "notification", "email", "sms",
            "admin panel", "dashboard", "reporting",
            "api", "integration", "webhook"
        ]

        requirements = []
        message_lower = message.lower()

        for feature in feature_keywords:
            if feature in message_lower:
                requirements.append(f"feature: {feature}")

        return requirements

    async def update_context(
        self,
        current_context: Dict[str, Any],
        messages: List[Dict[str, Any]],
        gathered_requirements: List[str]
    ) -> Dict[str, Any]:
        """
        Update conversation context with new information.

        Args:
            current_context: Current context state
            messages: All conversation messages
            gathered_requirements: All gathered requirements

        Returns:
            Updated context dictionary
        """
        # Categorize requirements
        categorized = self._categorize_requirements(gathered_requirements)

        # Calculate confidence scores for each category
        confidence_scores = self._calculate_confidence_scores(categorized)

        # Determine current topic based on recent messages and gaps
        current_topic = self._determine_current_topic(
            categorized,
            confidence_scores,
            messages
        )

        # Build answered questions list
        answered_questions = self._identify_answered_questions(
            messages,
            categorized
        )

        # Update context
        updated_context = {
            **current_context,
            "categorized_requirements": categorized,
            "confidence_scores": confidence_scores,
            "current_topic": current_topic,
            "answered_questions": answered_questions,
            "last_updated": datetime.utcnow().isoformat()
        }

        return updated_context

    def _categorize_requirements(
        self,
        requirements: List[str]
    ) -> Dict[str, List[str]]:
        """Categorize requirements into structured buckets."""
        categorized = defaultdict(list)

        for req in requirements:
            if ":" in req:
                category, value = req.split(":", 1)
                categorized[category.strip()].append(value.strip())
            else:
                categorized["general"].append(req)

        return dict(categorized)

    def _calculate_confidence_scores(
        self,
        categorized_requirements: Dict[str, List[str]]
    ) -> Dict[str, float]:
        """Calculate confidence score for each required category."""
        scores = {}

        for category in self.REQUIRED_CATEGORIES:
            if category in categorized_requirements:
                # Higher confidence if multiple items in category
                item_count = len(categorized_requirements[category])
                scores[category] = min(1.0, 0.5 + (item_count * 0.25))
            else:
                scores[category] = 0.0

        return scores

    def _determine_current_topic(
        self,
        categorized_requirements: Dict[str, List[str]],
        confidence_scores: Dict[str, float],
        messages: List[Dict[str, Any]]
    ) -> str:
        """Determine which topic should be focused on next."""
        # Find categories with low confidence
        low_confidence_categories = [
            cat for cat, score in confidence_scores.items()
            if score < self.MIN_CONFIDENCE
        ]

        if low_confidence_categories:
            # Return first low-confidence category
            return low_confidence_categories[0]

        # If all categories confident, check for general details
        if not categorized_requirements.get("general"):
            return "general"

        return "completion"

    def _identify_answered_questions(
        self,
        messages: List[Dict[str, Any]],
        categorized_requirements: Dict[str, List[str]]
    ) -> List[str]:
        """Identify which questions have been answered."""
        answered = []

        # Simple heuristic: questions followed by user messages are "answered"
        for i, msg in enumerate(messages):
            if msg.get("type") == "ai_question":
                # Check if next message is user response
                if i + 1 < len(messages) and messages[i + 1].get("type") == "user_message":
                    answered.append(msg.get("content", ""))

        return answered

    async def calculate_completion(
        self,
        context: Dict[str, Any],
        gathered_requirements: List[str]
    ) -> float:
        """
        Calculate conversation completion score (0.0 to 1.0).

        Args:
            context: Current conversation context
            gathered_requirements: All gathered requirements

        Returns:
            Completion score between 0.0 and 1.0
        """
        confidence_scores = context.get("confidence_scores", {})

        if not confidence_scores:
            return 0.0

        # Calculate average confidence across required categories
        total_score = sum(
            confidence_scores.get(cat, 0.0)
            for cat in self.REQUIRED_CATEGORIES
        )

        avg_score = total_score / len(self.REQUIRED_CATEGORIES)

        # Bonus for having many detailed requirements
        requirement_bonus = min(0.2, len(gathered_requirements) * 0.01)

        final_score = min(1.0, avg_score + requirement_bonus)

        return final_score

    def get_missing_information(
        self,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get list of missing information categories.

        Args:
            context: Current conversation context

        Returns:
            List of missing category names
        """
        confidence_scores = context.get("confidence_scores", {})

        missing = [
            category
            for category in self.REQUIRED_CATEGORIES
            if confidence_scores.get(category, 0.0) < self.MIN_CONFIDENCE
        ]

        return missing

    def should_ask_clarification(
        self,
        context: Dict[str, Any],
        round_count: int
    ) -> bool:
        """
        Determine if clarification questions should be asked.

        Args:
            context: Current conversation context
            round_count: Number of question rounds so far

        Returns:
            True if should ask questions, False otherwise
        """
        # Don't ask more than 5 rounds
        if round_count >= 5:
            return False

        # Ask if completion is below threshold
        completion = context.get("completion_percentage", 0) / 100.0
        return completion < self.COMPLETION_THRESHOLD
