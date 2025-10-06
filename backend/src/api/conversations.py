"""
Conversation API Endpoints (T043-T045)

OpenAPI-compliant endpoints for conversation management.
Implements contract spec from specs/001-build-an-ai/contracts/conversation-api.yaml
"""

from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field, field_validator

from ..models.conversation import ConversationStatus
from ..services.conversation.main import ConversationService, get_conversation_service
from ..infrastructure.middleware.auth import verify_api_key
from ..infrastructure.middleware.rate_limit import check_rate_limit


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)]
)


# Request/Response Models
class Question(BaseModel):
    """AI-generated question model."""
    id: str
    text: str
    type: str = Field(..., pattern="^(text|single_choice|multiple_choice|number|date)$")
    options: Optional[List[str]] = None
    required: bool = False
    help_text: Optional[str] = None


class StartConversationRequest(BaseModel):
    """Request model for starting a new conversation (T043)."""
    language: str = Field(
        ...,
        pattern="^(de|en|fr|es|it|nl|pl|pt|cs|da|el|hu|ro|sv|bg|hr|et|fi|ga|lt|lv|mt|sk|sl)$",
        description="ISO 639-1 language code"
    )
    session_id: Optional[str] = Field(None, description="Optional session ID for tracking")


class ConversationResponse(BaseModel):
    """Response model for conversation creation (T043)."""
    conversation_id: str = Field(..., description="UUID of the created conversation")
    status: str = Field(
        ...,
        pattern="^(active|paused|completed|abandoned|escalated)$"
    )
    initial_questions: List[Question] = Field(..., max_length=5)
    language: str


class SendMessageRequest(BaseModel):
    """Request model for sending a message (T044)."""
    message: str = Field(..., max_length=5000, description="User's message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    @field_validator('message')
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Message cannot be empty')
        return v


class AIResponse(BaseModel):
    """AI response with next questions (T044)."""
    message: str
    questions: List[Question] = Field(..., max_length=5)
    completion_percentage: int = Field(..., ge=0, le=100)
    suggested_category: Optional[str] = Field(
        None,
        pattern="^(software_development|consulting|infrastructure|mixed)$"
    )
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class ConversationDetails(BaseModel):
    """Detailed conversation information (T045)."""
    conversation_id: str
    status: str = Field(
        ...,
        pattern="^(active|paused|completed|abandoned|escalated)$"
    )
    started_at: datetime
    last_interaction_at: Optional[datetime] = None
    completion_percentage: int = Field(..., ge=0, le=100)
    interactions_count: int
    gathered_requirements: List[str]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None


# API Endpoints

@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Conversation created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"}
    }
)
async def start_conversation(
    request: StartConversationRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: ConversationService = Depends(get_conversation_service)
) -> ConversationResponse:
    """
    T043: Start a new conversation

    Creates a new AI-powered conversation for gathering project requirements.
    Returns initial questions in the specified language.

    Rate limit: Applied via middleware
    Authentication: API key required
    """
    try:
        conversation = await service.create_conversation(
            language=request.language,
            session_id=request.session_id
        )

        # Convert pending questions to Question models
        initial_questions = [
            Question(
                id=f"q_{idx}",
                text=question,
                type="text",
                required=False
            )
            for idx, question in enumerate(conversation.context.pending_questions)
        ]

        return ConversationResponse(
            conversation_id=str(conversation.id),
            status=conversation.status.value,
            initial_questions=initial_questions[:5],  # Max 5 questions
            language=conversation.language.code
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_LANGUAGE",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="CONVERSATION_CREATION_FAILED",
                message="Failed to create conversation"
            ).model_dump()
        )


@router.post(
    "/{conversationId}/messages",
    response_model=AIResponse,
    responses={
        200: {"description": "AI response with next questions"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        404: {"model": ErrorResponse, "description": "Conversation not found"},
        422: {"model": ErrorResponse, "description": "Maximum conversation rounds exceeded"}
    }
)
async def send_message(
    conversationId: str,
    request: SendMessageRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: ConversationService = Depends(get_conversation_service)
) -> AIResponse:
    """
    T044: Send a message in the conversation

    Processes user message through LangGraph AI workflow and returns
    AI response with up to 5 follow-up questions.

    Enforces maximum rounds limit (typically 5) to prevent infinite loops.
    """
    try:
        conversation_id = UUID(conversationId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid conversation ID format"
            ).model_dump()
        )

    try:
        # Process message through LangGraph workflow
        result_state = await service.process_message(
            conversation_id=conversation_id,
            message=request.message,
            metadata=request.context
        )

        # Check if max rounds exceeded
        if result_state.get("round_count", 0) > 5:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=ErrorResponse(
                    error_code="MAX_ROUNDS_EXCEEDED",
                    message="Maximum conversation rounds exceeded",
                    details={"max_rounds": 5, "current_round": result_state["round_count"]}
                ).model_dump()
            )

        # Extract AI response message
        ai_messages = [
            msg for msg in result_state["messages"]
            if msg.get("type") == "ai_question"
        ]

        latest_ai_message = ai_messages[-1]["content"] if ai_messages else "Thank you for your input."

        # Convert pending questions to Question models
        questions = [
            Question(
                id=f"q_{idx}",
                text=question,
                type="text",
                required=False
            )
            for idx, question in enumerate(result_state.get("pending_questions", []))
        ]

        # Determine suggested category based on context
        context = result_state.get("context", {})
        suggested_category = context.get("suggested_category")
        confidence_score = context.get("confidence_scores", {}).get("category")

        return AIResponse(
            message=latest_ai_message,
            questions=questions[:5],  # Max 5 questions
            completion_percentage=result_state.get("completion_percentage", 0),
            suggested_category=suggested_category,
            confidence_score=confidence_score
        )

    except HTTPException:
        raise
    except Exception as e:
        # Conversation not found or other error
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="CONVERSATION_NOT_FOUND",
                message=f"Conversation {conversationId} not found"
            ).model_dump()
        )


@router.get(
    "/{conversationId}",
    response_model=ConversationDetails,
    responses={
        200: {"description": "Conversation details"},
        404: {"model": ErrorResponse, "description": "Conversation not found"}
    }
)
async def get_conversation(
    conversationId: str,
    x_api_key: str = Header(..., alias="X-API-Key"),
    service: ConversationService = Depends(get_conversation_service)
) -> ConversationDetails:
    """
    T045: Get conversation details

    Retrieves current state of conversation including:
    - Status and completion percentage
    - Interaction count
    - Gathered requirements
    - Timestamps
    """
    try:
        conversation_id = UUID(conversationId)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_UUID",
                message="Invalid conversation ID format"
            ).model_dump()
        )

    try:
        # Get conversation state from checkpoint
        config = {"configurable": {"thread_id": conversationId}}
        state = await service.workflow.aget_state(config)
        current_state = state.values

        # Calculate interactions count
        interactions_count = len([
            msg for msg in current_state.get("messages", [])
            if msg.get("type") in ["user_message", "ai_question"]
        ])

        # Extract status
        if current_state.get("needs_escalation"):
            conversation_status = "escalated"
        elif current_state.get("completion_percentage", 0) >= 80:
            conversation_status = "completed"
        else:
            conversation_status = "active"

        # Get timestamps (approximated from messages)
        messages = current_state.get("messages", [])
        started_at = datetime.fromisoformat(messages[0]["timestamp"]) if messages else datetime.utcnow()
        last_interaction_at = datetime.fromisoformat(messages[-1]["timestamp"]) if messages else None

        return ConversationDetails(
            conversation_id=conversationId,
            status=conversation_status,
            started_at=started_at,
            last_interaction_at=last_interaction_at,
            completion_percentage=current_state.get("completion_percentage", 0),
            interactions_count=interactions_count,
            gathered_requirements=current_state.get("gathered_requirements", [])
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error_code="CONVERSATION_NOT_FOUND",
                message=f"Conversation {conversationId} not found"
            ).model_dump()
        )
