"""Work package entity models for offer generation."""

from decimal import Decimal
from typing import List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, field_validator

from .value_objects import Money


class Deliverable(BaseModel):
    """
    Deliverable within a work package.

    Represents a concrete output or result that will be produced
    during the execution of the work package.
    """

    name: str = Field(..., description="Name of the deliverable")
    description: str = Field(..., description="Detailed description of the deliverable")
    acceptance_criteria: List[str] = Field(
        default_factory=list,
        description="List of criteria that must be met for acceptance"
    )

    @field_validator('name', 'description')
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure name and description are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class EstimatedHours(BaseModel):
    """
    PERT-based time estimation for work packages.

    Uses three-point estimation (optimistic, likely, pessimistic)
    with confidence scoring to calculate expected duration.
    """

    optimistic: Decimal = Field(..., description="Best-case scenario hours", gt=0)
    likely: Decimal = Field(..., description="Most probable hours", gt=0)
    pessimistic: Decimal = Field(..., description="Worst-case scenario hours", gt=0)
    confidence: float = Field(
        ...,
        description="Confidence level in the estimate (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )

    @field_validator('pessimistic')
    @classmethod
    def validate_estimates(cls, v: Decimal, info) -> Decimal:
        """Ensure optimistic <= likely <= pessimistic."""
        optimistic = info.data.get('optimistic')
        likely = info.data.get('likely')

        if optimistic and likely:
            if optimistic > likely:
                raise ValueError("Optimistic estimate must be <= likely estimate")
            if likely > v:
                raise ValueError("Likely estimate must be <= pessimistic estimate")

        return v

    @property
    def expected(self) -> Decimal:
        """
        Calculate expected hours using PERT formula.

        PERT (Program Evaluation and Review Technique):
        Expected = (Optimistic + 4 × Likely + Pessimistic) / 6

        Returns:
            Decimal: Expected hours with high precision
        """
        return (self.optimistic + 4 * self.likely + self.pessimistic) / 6


class WorkPackage(BaseModel):
    """
    Work package entity representing a logical unit of work within an offer.

    Each work package contains deliverables, time estimates, pricing,
    and can have dependencies on other work packages to form a project
    execution plan.

    Invariants:
    - Total cost = estimated_hours.expected × hourly_rate
    - Dependencies must form a DAG (no cycles)
    - At least one deliverable per package
    """

    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    offer_id: UUID = Field(..., description="Reference to parent offer")
    name: str = Field(..., description="Name of the work package")
    description: str = Field(..., description="Detailed description of the work")
    deliverables: List[Deliverable] = Field(
        ...,
        min_length=1,
        description="List of deliverables (at least one required)"
    )
    estimated_hours: EstimatedHours = Field(..., description="Three-point time estimation")
    hourly_rate: Money = Field(..., description="Rate per hour for this package")
    total_cost: Money = Field(..., description="Total cost (expected hours × hourly rate)")
    dependencies: List[UUID] = Field(
        default_factory=list,
        description="IDs of work packages that must be completed first"
    )
    order: int = Field(..., description="Display order in the offer", ge=1)

    @field_validator('name', 'description')
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure name and description are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator('total_cost')
    @classmethod
    def validate_total_cost(cls, v: Money, info) -> Money:
        """
        Validate that total_cost matches expected calculation.

        Total cost should equal estimated_hours.expected × hourly_rate
        with tolerance for rounding differences.
        """
        estimated_hours = info.data.get('estimated_hours')
        hourly_rate = info.data.get('hourly_rate')

        if estimated_hours and hourly_rate:
            expected_total = hourly_rate * estimated_hours.expected
            # Allow small rounding difference (0.01 currency units)
            tolerance = Decimal('0.01')
            diff = abs(v.amount - expected_total.amount)

            if diff > tolerance:
                raise ValueError(
                    f"Total cost {v.amount} does not match expected calculation "
                    f"{expected_total.amount} (expected hours × hourly rate)"
                )

        return v

    @field_validator('dependencies')
    @classmethod
    def validate_no_self_dependency(cls, v: List[UUID], info) -> List[UUID]:
        """Ensure work package doesn't depend on itself."""
        package_id = info.data.get('id')
        if package_id and package_id in v:
            raise ValueError("Work package cannot depend on itself")
        return v

    def has_dependencies(self) -> bool:
        """Check if this work package has any dependencies."""
        return len(self.dependencies) > 0

    def depends_on(self, package_id: UUID) -> bool:
        """Check if this work package depends on another package."""
        return package_id in self.dependencies
