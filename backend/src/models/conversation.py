"""Conversation aggregate root model for AI-powered requirement gathering.

This module implements the Conversation bounded context with support for
multi-language interactions, context management, and conversation state tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .value_objects import LanguageCode


class ConversationStatus(Enum):
    """Conversation lifecycle states.

    State transitions:
        ACTIVE → PAUSED → ACTIVE
          ↓        ↓        ↓
        COMPLETED  ABANDONED  ESCALATED
    """

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class InteractionType(Enum):
    """Types of interactions within a conversation."""

    USER_MESSAGE = "user_message"
    AI_MESSAGE = "ai_message"
    AI_QUESTION = "ai_question"


class Interaction(BaseModel):
    """Single interaction within a conversation.

    Represents a message exchange between the AI and the user,
    tracking content, language, and metadata for analysis.
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    type: InteractionType
    content: str
    language: LanguageCode
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class ConversationContext(BaseModel):
    """Maintains conversation state and gathered information.

    Tracks the current topic, answered/pending questions, requirements,
    and confidence scores for requirement understanding.
    """

    current_topic: str = ""
    answered_questions: List[str] = Field(default_factory=list)
    pending_questions: List[str] = Field(default_factory=list)
    gathered_requirements: List[str] = Field(default_factory=list)
    confidence_scores: Dict[str, float] = Field(default_factory=dict)

    def add_answered_question(self, question: str) -> None:
        """Mark a question as answered and remove from pending."""
        if question in self.pending_questions:
            self.pending_questions.remove(question)
        if question not in self.answered_questions:
            self.answered_questions.append(question)

    def add_pending_question(self, question: str) -> None:
        """Add a new question to the pending list."""
        if question not in self.pending_questions and question not in self.answered_questions:
            self.pending_questions.append(question)

    def add_requirement(self, requirement: str, confidence: float = 0.0) -> None:
        """Add a gathered requirement with confidence score."""
        if requirement not in self.gathered_requirements:
            self.gathered_requirements.append(requirement)
            self.confidence_scores[requirement] = confidence

    def update_confidence(self, requirement: str, confidence: float) -> None:
        """Update confidence score for a requirement."""
        if requirement in self.gathered_requirements:
            self.confidence_scores[requirement] = confidence


class Conversation(BaseModel):
    """Conversation aggregate root.

    Manages the lifecycle of an AI-powered conversation for requirement
    gathering, supporting anonymous sessions, multi-language interactions,
    and context preservation.

    Invariants:
        - Maximum 5 questions per interaction round
        - Context must be maintained across interactions
        - Escalation triggered after 5 clarification rounds
        - Completion percentage must be between 0-100
    """

    id: UUID = Field(default_factory=uuid4)
    session_id: str
    customer_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    language: LanguageCode
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction_at: datetime = Field(default_factory=datetime.utcnow)
    status: ConversationStatus = ConversationStatus.ACTIVE
    interactions: List[Interaction] = Field(default_factory=list)
    context: ConversationContext = Field(default_factory=ConversationContext)
    completion_percentage: int = Field(default=0, ge=0, le=100)

    class Config:
        """Pydantic configuration."""
        use_enum_values = True

    def add_interaction(
        self,
        interaction_type: InteractionType,
        content: str,
        language: Optional[LanguageCode] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Interaction:
        """Add a new interaction to the conversation.

        Args:
            interaction_type: Type of interaction (user/AI message/question)
            content: Interaction content
            language: Language code (defaults to conversation language)
            metadata: Additional metadata (intents, entities, etc.)

        Returns:
            The created interaction
        """
        interaction = Interaction(
            type=interaction_type,
            content=content,
            language=language or self.language,
            metadata=metadata or {}
        )
        self.interactions.append(interaction)
        self.last_interaction_at = interaction.timestamp
        return interaction

    def pause(self) -> None:
        """Pause an active conversation."""
        if self.status == ConversationStatus.ACTIVE:
            self.status = ConversationStatus.PAUSED

    def resume(self) -> None:
        """Resume a paused conversation."""
        if self.status == ConversationStatus.PAUSED:
            self.status = ConversationStatus.ACTIVE
            self.last_interaction_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark conversation as completed."""
        self.status = ConversationStatus.COMPLETED
        self.completion_percentage = 100
        self.last_interaction_at = datetime.utcnow()

    def abandon(self) -> None:
        """Mark conversation as abandoned."""
        self.status = ConversationStatus.ABANDONED
        self.last_interaction_at = datetime.utcnow()

    def escalate(self) -> None:
        """Escalate conversation to human operator.

        Triggered after maximum clarification rounds or on explicit request.
        """
        self.status = ConversationStatus.ESCALATED
        self.last_interaction_at = datetime.utcnow()

    def get_clarification_rounds(self) -> int:
        """Count number of AI question rounds.

        Each round consists of up to 5 consecutive AI questions.
        Rounds are separated by user messages.

        Returns:
            Number of clarification rounds completed
        """
        rounds = 0
        consecutive_questions = 0

        for interaction in self.interactions:
            if interaction.type == InteractionType.AI_QUESTION.value:
                consecutive_questions += 1
                if consecutive_questions == 5:
                    rounds += 1
                    consecutive_questions = 0
            elif interaction.type == InteractionType.USER_MESSAGE.value:
                # User responded, count as completing a round if there were questions
                if consecutive_questions > 0:
                    rounds += 1
                    consecutive_questions = 0

        return rounds

    def should_escalate(self) -> bool:
        """Check if conversation should be escalated.

        Escalation triggered after 5 clarification rounds.

        Returns:
            True if escalation threshold reached
        """
        return self.get_clarification_rounds() >= 5

    def update_completion_percentage(self, percentage: int) -> None:
        """Update conversation completion percentage.

        Args:
            percentage: Completion percentage (0-100)

        Raises:
            ValueError: If percentage out of range
        """
        if not 0 <= percentage <= 100:
            raise ValueError(f"Completion percentage must be 0-100, got {percentage}")
        self.completion_percentage = percentage

    def get_interaction_count_by_type(self, interaction_type: InteractionType) -> int:
        """Count interactions of a specific type.

        Args:
            interaction_type: Type to count

        Returns:
            Number of interactions of that type
        """
        return sum(1 for i in self.interactions if i.type == interaction_type.value)

    def get_recent_interactions(self, limit: int = 10) -> List[Interaction]:
        """Get most recent interactions.

        Args:
            limit: Maximum number of interactions to return

        Returns:
            List of recent interactions (newest first)
        """
        return list(reversed(self.interactions[-limit:]))

    def link_customer(self, customer_id: UUID) -> None:
        """Link conversation to a customer after authentication.

        Args:
            customer_id: UUID of the customer
        """
        self.customer_id = customer_id

    def link_project(self, project_id: UUID) -> None:
        """Link conversation to a project.

        Args:
            project_id: UUID of the project
        """
        self.project_id = project_id
