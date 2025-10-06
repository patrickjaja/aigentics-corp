"""Domain models for the AI Offer Agent."""

from .value_objects import EmailAddress, PhoneNumber, LanguageCode, Money, BudgetRange
from .customer import Customer, GDPRConsent, ConsentPurpose
from .project import Project, ProjectCategory, Requirement, ProjectConstraints, Priority, RequirementType
from .conversation import Conversation, ConversationStatus, Interaction, InteractionType, ConversationContext
from .offer import Offer, OfferStatus, OfferEvent
from .work_package import WorkPackage, Deliverable, EstimatedHours
from .approval import ApprovalWorkflow, ApprovalStatus, ApprovalDecision, Comment, OfferModification
from .estimation import EstimationModel, COCOMOParameters, CalibrationPoint, AccuracyMetrics
# TODO: Import when implemented
from .api_client import APIClient, RateLimit, UsageStats

__all__ = [
    # Value Objects
    "EmailAddress",
    "PhoneNumber",
    "LanguageCode",
    "Money",
    "BudgetRange",
    # Customer
    "Customer",
    "GDPRConsent",
    "ConsentPurpose",
    # Project
    "Project",
    "ProjectCategory",
    "Requirement",
    "ProjectConstraints",
    "Priority",
    "RequirementType",
    # Conversation
    "Conversation",
    "ConversationStatus",
    "Interaction",
    "InteractionType",
    "ConversationContext",
    # Offer
    "Offer",
    "OfferStatus",
    "OfferEvent",
    # Work Package
    "WorkPackage",
    "Deliverable",
    "EstimatedHours",
    # Approval
    "ApprovalWorkflow",
    "ApprovalStatus",
    "ApprovalDecision",
    "Comment",
    "OfferModification",
    # Estimation
    "EstimationModel",
    "COCOMOParameters",
    "CalibrationPoint",
    "AccuracyMetrics",
    # TODO: Add when implemented
    # API Client
    "APIClient",
    "RateLimit",
    "UsageStats",
]
