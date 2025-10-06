"""
Conversation Service - LangGraph Orchestration

Manages AI-powered conversations for gathering project requirements
using LangGraph state machines with PostgreSQL persistence.
"""

from typing import Any, Dict, List, Optional, TypedDict
from uuid import UUID, uuid4
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
import asyncio

from ...models.conversation import (
    Conversation,
    ConversationStatus,
    Interaction,
    InteractionType,
    ConversationContext,
)
from ...models.customer import Customer, LanguageCode
from ...infrastructure.database import get_db_connection
from .context_manager import ContextManager
from .ai_questions import AIQuestionGenerator


app = FastAPI(title="Conversation Service", version="1.0.0")


# Pydantic models for API
class CreateConversationRequest(BaseModel):
    language: str = "en"
    session_id: Optional[str] = None


class ConversationMessageRequest(BaseModel):
    message: str
    metadata: Optional[Dict[str, Any]] = None


class ConversationResponse(BaseModel):
    conversation_id: str
    status: str
    interactions: List[Dict[str, Any]]
    completion_percentage: int
    next_questions: Optional[List[str]] = None


# LangGraph State Definition
class ConversationState(TypedDict):
    conversation_id: str
    messages: List[Dict[str, Any]]
    context: Dict[str, Any]
    gathered_requirements: List[str]
    pending_questions: List[str]
    current_topic: str
    completion_percentage: int
    round_count: int
    needs_escalation: bool


class ConversationService:
    """Service for managing conversations with LangGraph orchestration."""

    def __init__(self, db_connection_string: str):
        self.db_connection = db_connection_string
        self.context_manager = ContextManager()
        self.question_generator = AIQuestionGenerator()
        self.checkpointer = PostgresSaver.from_conn_string(db_connection_string)
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for conversation management."""
        workflow = StateGraph(ConversationState)

        # Define nodes
        workflow.add_node("process_message", self._process_user_message)
        workflow.add_node("update_context", self._update_context)
        workflow.add_node("generate_questions", self._generate_ai_questions)
        workflow.add_node("check_completion", self._check_conversation_completion)
        workflow.add_node("escalate", self._escalate_conversation)

        # Define edges
        workflow.set_entry_point("process_message")
        workflow.add_edge("process_message", "update_context")
        workflow.add_edge("update_context", "generate_questions")
        workflow.add_edge("generate_questions", "check_completion")

        # Conditional edges
        workflow.add_conditional_edges(
            "check_completion",
            self._should_escalate,
            {
                "escalate": "escalate",
                "continue": END,
                "complete": END,
            }
        )
        workflow.add_edge("escalate", END)

        return workflow.compile(checkpointer=self.checkpointer)

    async def _process_user_message(self, state: ConversationState) -> ConversationState:
        """Process incoming user message and extract intents."""
        last_message = state["messages"][-1] if state["messages"] else {}

        # Extract requirements from user message using NLP
        requirements = await self.context_manager.extract_requirements(
            last_message.get("content", ""),
            state["context"]
        )

        state["gathered_requirements"].extend(requirements)
        state["round_count"] = state.get("round_count", 0) + 1

        return state

    async def _update_context(self, state: ConversationState) -> ConversationState:
        """Update conversation context with new information."""
        updated_context = await self.context_manager.update_context(
            state["context"],
            state["messages"],
            state["gathered_requirements"]
        )

        state["context"] = updated_context
        state["current_topic"] = updated_context.get("current_topic", "general")

        return state

    async def _generate_ai_questions(self, state: ConversationState) -> ConversationState:
        """Generate AI questions based on current context (max 5 per round)."""
        questions = await self.question_generator.generate_questions(
            context=state["context"],
            gathered_requirements=state["gathered_requirements"],
            max_questions=5
        )

        state["pending_questions"] = questions

        # Add AI questions as interaction messages
        for question in questions:
            state["messages"].append({
                "type": "ai_question",
                "content": question,
                "timestamp": datetime.utcnow().isoformat()
            })

        return state

    async def _check_conversation_completion(self, state: ConversationState) -> ConversationState:
        """Check if conversation has gathered sufficient information."""
        completion_score = await self.context_manager.calculate_completion(
            state["context"],
            state["gathered_requirements"]
        )

        state["completion_percentage"] = int(completion_score * 100)

        # Check escalation conditions
        if state["round_count"] >= 5 and state["completion_percentage"] < 60:
            state["needs_escalation"] = True

        return state

    def _should_escalate(self, state: ConversationState) -> str:
        """Determine if conversation should be escalated to human."""
        if state["needs_escalation"]:
            return "escalate"
        elif state["completion_percentage"] >= 80:
            return "complete"
        else:
            return "continue"

    async def _escalate_conversation(self, state: ConversationState) -> ConversationState:
        """Escalate conversation to human sales team."""
        state["messages"].append({
            "type": "system",
            "content": "This conversation has been escalated to our sales team for personalized assistance.",
            "timestamp": datetime.utcnow().isoformat()
        })
        return state

    async def create_conversation(
        self,
        language: str = "en",
        session_id: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation with initial state."""
        conversation_id = uuid4()

        # Initialize state
        initial_state: ConversationState = {
            "conversation_id": str(conversation_id),
            "messages": [],
            "context": {
                "language": language,
                "confidence_scores": {},
                "answered_questions": [],
            },
            "gathered_requirements": [],
            "pending_questions": [],
            "current_topic": "general",
            "completion_percentage": 0,
            "round_count": 0,
            "needs_escalation": False,
        }

        # Generate initial questions
        initial_questions = await self.question_generator.generate_initial_questions(language)
        initial_state["pending_questions"] = initial_questions

        # Create conversation entity
        conversation = Conversation(
            id=conversation_id,
            session_id=session_id or str(uuid4()),
            customer_id=None,
            project_id=None,
            language=LanguageCode(language),
            started_at=datetime.utcnow(),
            last_interaction_at=datetime.utcnow(),
            status=ConversationStatus.ACTIVE,
            interactions=[],
            context=ConversationContext(
                current_topic="general",
                answered_questions=[],
                pending_questions=initial_questions,
                gathered_requirements=[],
                confidence_scores={}
            ),
            completion_percentage=0
        )

        return conversation

    async def process_message(
        self,
        conversation_id: UUID,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationState:
        """Process user message through LangGraph workflow."""

        # Load conversation state from checkpoint
        config = {"configurable": {"thread_id": str(conversation_id)}}

        # Get current state or initialize
        try:
            current_state = await self.workflow.aget_state(config)
            state = current_state.values
        except Exception:
            # If no checkpoint exists, create new state
            state: ConversationState = {
                "conversation_id": str(conversation_id),
                "messages": [],
                "context": {},
                "gathered_requirements": [],
                "pending_questions": [],
                "current_topic": "general",
                "completion_percentage": 0,
                "round_count": 0,
                "needs_escalation": False,
            }

        # Add user message
        state["messages"].append({
            "type": "user_message",
            "content": message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })

        # Run workflow
        result = await self.workflow.ainvoke(state, config)

        return result


# Dependency injection
async def get_conversation_service() -> ConversationService:
    """Dependency for getting conversation service."""
    db_conn = await get_db_connection()
    return ConversationService(db_conn)


# API Endpoints
@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """Create a new conversation."""
    conversation = await service.create_conversation(
        language=request.language,
        session_id=request.session_id
    )

    return ConversationResponse(
        conversation_id=str(conversation.id),
        status=conversation.status.value,
        interactions=[],
        completion_percentage=conversation.completion_percentage,
        next_questions=conversation.context.pending_questions
    )


@app.post("/conversations/{conversation_id}/messages", response_model=ConversationResponse)
async def send_message(
    conversation_id: str,
    request: ConversationMessageRequest,
    service: ConversationService = Depends(get_conversation_service)
):
    """Send a message to an existing conversation."""
    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    result_state = await service.process_message(
        conversation_id=conv_id,
        message=request.message,
        metadata=request.metadata
    )

    return ConversationResponse(
        conversation_id=conversation_id,
        status="active" if not result_state["needs_escalation"] else "escalated",
        interactions=[
            {"type": msg["type"], "content": msg["content"]}
            for msg in result_state["messages"]
        ],
        completion_percentage=result_state["completion_percentage"],
        next_questions=result_state["pending_questions"]
    )


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Get conversation status and history."""
    try:
        conv_id = UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid conversation ID")

    config = {"configurable": {"thread_id": conversation_id}}

    try:
        state = await service.workflow.aget_state(config)
        current_state = state.values

        return ConversationResponse(
            conversation_id=conversation_id,
            status="active",
            interactions=[
                {"type": msg["type"], "content": msg["content"]}
                for msg in current_state["messages"]
            ],
            completion_percentage=current_state["completion_percentage"],
            next_questions=current_state["pending_questions"]
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Conversation not found: {str(e)}")


@app.post("/conversations/{conversation_id}/complete")
async def complete_conversation(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service)
):
    """Mark conversation as completed."""
    # Implementation would update conversation status
    return {"status": "completed", "conversation_id": conversation_id}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "conversation"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
