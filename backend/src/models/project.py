"""Project entity model for the AI Offer Agent system."""

from datetime import date, datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .value_objects import BudgetRange, Money


class ProjectCategory(str, Enum):
    """Categorization of project types."""

    SOFTWARE_DEVELOPMENT = "software_development"
    IT_CONSULTING = "consulting"
    INFRASTRUCTURE = "infrastructure"
    MIXED = "mixed"


class Priority(str, Enum):
    """Priority levels for requirements."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RequirementType(str, Enum):
    """Type classification for requirements."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"


class Requirement(BaseModel):
    """Individual project requirement with priority and acceptance criteria.

    A requirement represents a specific need or constraint for the project,
    categorized by priority and type (functional or non-functional).
    """

    id: UUID = Field(default_factory=uuid4)
    description: str = Field(..., description="Detailed description of the requirement")
    priority: Priority = Field(..., description="Priority level of this requirement")
    type: RequirementType = Field(..., description="Classification of the requirement type")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of criteria that must be met for this requirement to be considered complete"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "description": "Implement user authentication with OAuth2",
                "priority": "high",
                "type": "functional",
                "acceptance_criteria": [
                    "Support Google and Microsoft OAuth2 providers",
                    "Session management with JWT tokens",
                    "Password reset functionality"
                ]
            }
        }


class ProjectConstraints(BaseModel):
    """Constraints and limitations for the project.

    Defines optional constraints including budget limits, deadlines,
    technology preferences, and team size restrictions.
    """

    max_budget: Optional[Money] = Field(
        None,
        description="Maximum budget available for the project"
    )
    deadline: Optional[date] = Field(
        None,
        description="Hard deadline for project completion"
    )
    technology_preferences: List[str] = Field(
        default_factory=list,
        description="Preferred technologies, frameworks, or platforms"
    )
    team_size_limit: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum number of team members allowed"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "max_budget": {"amount": "50000.00", "currency": "EUR"},
                "deadline": "2025-12-31",
                "technology_preferences": ["Python", "FastAPI", "PostgreSQL"],
                "team_size_limit": 5
            }
        }


class Timeline(BaseModel):
    """Project timeline with start and end dates.

    Represents the planned duration of the project with optional
    milestones or phases.
    """

    start_date: Optional[date] = Field(
        None,
        description="Planned project start date"
    )
    end_date: Optional[date] = Field(
        None,
        description="Planned project end date"
    )

    class Config:
        frozen = False


class Project(BaseModel):
    """Project entity representing a customer's IT project.

    Aggregate root for project-related information including requirements,
    constraints, timeline, and budget. Projects are created from conversations
    and used to generate offers.

    Invariants:
    - Project must have at least one requirement
    - Budget and timeline constraints are optional but affect estimation
    """

    id: UUID = Field(default_factory=uuid4)
    customer_id: UUID = Field(..., description="Reference to the customer who owns this project")
    name: str = Field(..., min_length=1, description="Project name or title")
    description: str = Field(..., description="Detailed project description")
    category: ProjectCategory = Field(..., description="Category of the project type")
    requirements: List[Requirement] = Field(
        ...,
        min_length=1,
        description="List of project requirements (at least one required)"
    )
    constraints: ProjectConstraints = Field(
        default_factory=ProjectConstraints,
        description="Project constraints and limitations"
    )
    timeline: Optional[Timeline] = Field(
        None,
        description="Planned project timeline"
    )
    budget_indication: Optional[BudgetRange] = Field(
        None,
        description="Indicative budget range for the project"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the project was created"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "customer_id": "987e6543-e21b-12d3-a456-426614174000",
                "name": "E-Commerce Platform Development",
                "description": "Build a modern e-commerce platform with inventory management and payment integration",
                "category": "software_development",
                "requirements": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "description": "Implement shopping cart functionality",
                        "priority": "high",
                        "type": "functional",
                        "acceptance_criteria": [
                            "Add/remove items from cart",
                            "Calculate totals with taxes",
                            "Save cart for logged-in users"
                        ]
                    }
                ],
                "constraints": {
                    "max_budget": {"amount": "75000.00", "currency": "EUR"},
                    "deadline": "2025-06-30",
                    "technology_preferences": ["Python", "React", "PostgreSQL"],
                    "team_size_limit": 4
                },
                "timeline": {
                    "start_date": "2025-01-15",
                    "end_date": "2025-06-30"
                },
                "budget_indication": {
                    "min_amount": {"amount": "50000.00", "currency": "EUR"},
                    "max_amount": {"amount": "75000.00", "currency": "EUR"}
                },
                "created_at": "2025-09-30T10:00:00Z"
            }
        }

    def get_high_priority_requirements(self) -> List[Requirement]:
        """Get all high priority requirements.

        Returns:
            List of requirements with HIGH priority
        """
        return [req for req in self.requirements if req.priority == Priority.HIGH]

    def get_functional_requirements(self) -> List[Requirement]:
        """Get all functional requirements.

        Returns:
            List of functional requirements
        """
        return [req for req in self.requirements if req.type == RequirementType.FUNCTIONAL]

    def get_non_functional_requirements(self) -> List[Requirement]:
        """Get all non-functional requirements.

        Returns:
            List of non-functional requirements
        """
        return [req for req in self.requirements if req.type == RequirementType.NON_FUNCTIONAL]

    def has_budget_constraint(self) -> bool:
        """Check if project has a budget constraint.

        Returns:
            True if max_budget is set in constraints
        """
        return self.constraints.max_budget is not None

    def has_deadline(self) -> bool:
        """Check if project has a deadline.

        Returns:
            True if deadline is set in constraints
        """
        return self.constraints.deadline is not None

    def is_budget_within_range(self, amount: Money) -> bool:
        """Check if given amount is within the project's budget indication.

        Args:
            amount: The amount to check

        Returns:
            True if amount is within budget_indication range, or if no range is set
        """
        if not self.budget_indication:
            return True
        return self.budget_indication.contains(amount)
