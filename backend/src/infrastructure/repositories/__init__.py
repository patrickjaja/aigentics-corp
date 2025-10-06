"""Repository implementations for aggregates."""
from .base import Repository
from .customer import CustomerRepository
from .conversation import ConversationRepository
from .offer import OfferRepository
from .approval import ApprovalWorkflowRepository

__all__ = [
    "Repository",
    "CustomerRepository",
    "ConversationRepository",
    "OfferRepository",
    "ApprovalWorkflowRepository",
]
