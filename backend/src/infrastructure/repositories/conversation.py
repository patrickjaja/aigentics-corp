"""Conversation repository implementation."""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from ...models.conversation import (
    Conversation,
    ConversationContext,
    ConversationStatus,
    Interaction,
    InteractionType,
)
from ...models.value_objects import LanguageCode
from ..events.schema import DomainEvent
from .base import Repository


class ConversationRepository(Repository[Conversation]):
    """Repository for Conversation aggregate."""

    def _reconstruct_from_events(self, events: List[DomainEvent]) -> Conversation:
        """Reconstruct conversation from events."""
        conversation_data = {}
        interactions = []
        context_data = {
            "current_topic": "",
            "answered_questions": [],
            "pending_questions": [],
            "gathered_requirements": [],
            "confidence_scores": {},
        }

        for event in events:
            event_type = event.event_type
            payload = event.payload

            if event_type == "ConversationStarted":
                conversation_data = {
                    "id": event.aggregate_id,
                    "session_id": payload["session_id"],
                    "customer_id": UUID(payload["customer_id"]) if payload.get("customer_id") else None,
                    "project_id": UUID(payload["project_id"]) if payload.get("project_id") else None,
                    "language": LanguageCode(code=payload.get("language", "en")),
                    "started_at": event.occurred_at,
                    "last_interaction_at": event.occurred_at,
                    "status": ConversationStatus.ACTIVE,
                    "completion_percentage": 0,
                }
                if payload.get("context"):
                    context_data.update(payload["context"])

            elif event_type in ["QuestionAsked", "AnswerReceived", "UserMessageReceived", "AIMessageSent"]:
                interaction = Interaction(
                    id=uuid4(),
                    timestamp=event.occurred_at,
                    type=InteractionType(payload.get("type", "USER_MESSAGE")),
                    content=payload.get("content", ""),
                    language=LanguageCode(code=payload.get("language", conversation_data.get("language", "en"))),
                    metadata=payload.get("metadata", {}),
                )
                interactions.append(interaction)
                conversation_data["last_interaction_at"] = event.occurred_at

            elif event_type == "RequirementIdentified":
                requirement = payload.get("requirement", "")
                if requirement:
                    context_data["gathered_requirements"].append(requirement)
                conversation_data["completion_percentage"] = payload.get("completion_percentage", 0)

            elif event_type == "QuestionAnswered":
                question = payload.get("question", "")
                if question:
                    context_data["answered_questions"].append(question)
                    if question in context_data["pending_questions"]:
                        context_data["pending_questions"].remove(question)

            elif event_type == "TopicChanged":
                context_data["current_topic"] = payload.get("topic", "")

            elif event_type == "ConversationCompleted":
                conversation_data["status"] = ConversationStatus.COMPLETED
                conversation_data["completion_percentage"] = 100

            elif event_type == "ConversationPaused":
                conversation_data["status"] = ConversationStatus.PAUSED

            elif event_type == "ConversationAbandoned":
                conversation_data["status"] = ConversationStatus.ABANDONED

            elif event_type == "ConversationEscalated":
                conversation_data["status"] = ConversationStatus.ESCALATED

        # Create context object
        conversation_data["context"] = ConversationContext(**context_data)
        conversation_data["interactions"] = interactions

        return Conversation(**conversation_data)

    def _get_uncommitted_events(self, aggregate: Conversation) -> List[DomainEvent]:
        """Get uncommitted events from conversation."""
        return getattr(aggregate, "_uncommitted_events", [])

    def _mark_events_committed(self, aggregate: Conversation) -> None:
        """Mark conversation events as committed."""
        if hasattr(aggregate, "_uncommitted_events"):
            aggregate._uncommitted_events = []

    def _get_aggregate_id(self, aggregate: Conversation) -> UUID:
        """Get conversation ID."""
        return aggregate.id

    def _create_deletion_event(self, aggregate_id: UUID) -> DomainEvent:
        """Create conversation deletion event."""
        return DomainEvent(
            event_id=uuid4(),
            aggregate_id=aggregate_id,
            aggregate_type="Conversation",
            event_type="ConversationDeleted",
            event_version=1,
            occurred_at=datetime.utcnow(),
            correlation_id=uuid4(),
            causation_id=None,
            actor_id=None,
            metadata={},
            payload={"deleted_at": datetime.utcnow().isoformat()},
        )
