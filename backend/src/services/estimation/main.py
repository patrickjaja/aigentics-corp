"""Estimation Service with COCOMO II model.

This service provides project effort estimation using the Intermediate COCOMO II
model, with calibration from historical data to maintain ±25% variance target.

Key Features:
- Intermediate COCOMO II effort estimation
- Historical data calibration
- Accuracy metrics (MAE, MSE, R-squared)
- Project hour estimation based on requirements
- Continuous learning from completed projects
- FastAPI endpoints for estimation
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from pydantic import BaseModel, Field

from ...models.estimation import (
    AccuracyMetrics,
    COCOMOParameters,
    CalibrationPoint,
    EstimationModel,
)
from ...models.project import Project, ProjectCategory, RequirementType

logger = logging.getLogger(__name__)


# Request/Response Models
class EstimateRequest(BaseModel):
    """Request model for project estimation."""

    project_id: UUID
    size_kloc: Optional[float] = Field(
        None,
        gt=0,
        description="Project size in KLOC (thousands of lines of code). If not provided, will be estimated from requirements."
    )
    complexity_factors: Dict[str, str] = Field(
        default_factory=dict,
        description="Complexity factors (e.g., team_experience: 'high', technology_familiarity: 'medium')"
    )
    adjustment_factor: float = Field(
        default=1.0,
        ge=0.5,
        le=2.0,
        description="Manual adjustment factor for estimation (default: 1.0)"
    )


class EstimateResponse(BaseModel):
    """Response model for project estimation."""

    estimate_id: UUID
    project_id: UUID
    estimated_hours: float
    optimistic_hours: float
    likely_hours: float
    pessimistic_hours: float
    confidence: float
    model_id: UUID
    model_name: str
    factors_applied: Dict[str, float]
    created_at: datetime


class CalibrationRequest(BaseModel):
    """Request model for adding calibration data."""

    project_id: UUID
    estimated_hours: float = Field(..., gt=0)
    actual_hours: float = Field(..., gt=0)
    factors: Dict[str, Any] = Field(default_factory=dict)


class AccuracyMetricsResponse(BaseModel):
    """Response model for accuracy metrics."""

    model_id: UUID
    model_name: str
    mean_absolute_error: float
    mean_squared_error: float
    r_squared: float
    within_25_percent: float
    calibration_count: int
    last_updated: datetime


# COCOMO II Constants
DEFAULT_SCALE_FACTORS = {
    "precedentedness": 3.72,          # Thoroughness of analysis, design
    "development_flexibility": 2.03,   # Conformance to requirements
    "architecture_risk_resolution": 4.24,  # Risk analysis thoroughness
    "team_cohesion": 3.29,            # Cooperation of stakeholders
    "process_maturity": 4.68,         # Process maturity (CMMI)
}

DEFAULT_COST_DRIVERS = {
    # Product factors
    "product_complexity": 1.0,
    "required_reusability": 1.0,
    "documentation_match": 1.0,

    # Platform factors
    "platform_difficulty": 1.0,
    "execution_time_constraint": 1.0,
    "main_storage_constraint": 1.0,

    # Personnel factors
    "analyst_capability": 0.85,
    "programmer_capability": 0.88,
    "personnel_continuity": 1.0,
    "application_experience": 0.91,
    "platform_experience": 1.0,
    "language_tool_experience": 0.95,

    # Project factors
    "time_constraint": 1.0,
    "tool_use": 0.90,
    "multisite_development": 1.0,
    "required_schedule": 1.0,
}


class EstimationService:
    """Service for project effort estimation using COCOMO II.

    Provides methods for:
    - Estimating project effort from requirements
    - Managing estimation models by project category
    - Calibrating models with historical data
    - Calculating accuracy metrics
    """

    def __init__(self):
        """Initialize the estimation service with default models."""
        self._models: Dict[ProjectCategory, EstimationModel] = {}
        self._initialize_default_models()

    def _initialize_default_models(self) -> None:
        """Initialize default estimation models for each project category."""
        for category in ProjectCategory:
            model = EstimationModel(
                id=uuid4(),
                name=f"{category.value.replace('_', ' ').title()} Estimation Model",
                project_category=category,
                cocomo_parameters=COCOMOParameters(
                    effort_multipliers={
                        "nominal": 1.0,
                        "simple": 0.85,
                        "complex": 1.15,
                        "very_complex": 1.30,
                    },
                    scale_factors=DEFAULT_SCALE_FACTORS.copy(),
                    cost_drivers=DEFAULT_COST_DRIVERS.copy(),
                ),
                calibration_data=[],
                accuracy_metrics=AccuracyMetrics(
                    mean_absolute_error=0.0,
                    mean_squared_error=0.0,
                    r_squared=0.0,
                    within_25_percent=0.0,
                ),
                last_updated=datetime.utcnow(),
            )
            self._models[category] = model
            logger.info(f"Initialized estimation model for {category.value}")

    def estimate_project(
        self,
        project: Project,
        size_kloc: Optional[float] = None,
        complexity_factors: Optional[Dict[str, str]] = None,
        adjustment_factor: float = 1.0,
    ) -> EstimateResponse:
        """Estimate project effort using COCOMO II model.

        Args:
            project: Project entity to estimate
            size_kloc: Project size in KLOC (estimated from requirements if not provided)
            complexity_factors: Complexity factors for cost driver adjustment
            adjustment_factor: Manual adjustment factor (0.5 to 2.0)

        Returns:
            EstimateResponse with effort estimation details

        Raises:
            ValueError: If project category has no estimation model
        """
        # Get the appropriate model
        model = self._models.get(project.category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project.category}")

        # Estimate size if not provided
        if size_kloc is None:
            size_kloc = self._estimate_size_from_requirements(project)

        # Calculate effort using COCOMO II
        effort_hours = self._calculate_cocomo_effort(
            model=model,
            size_kloc=size_kloc,
            complexity_factors=complexity_factors or {},
        )

        # Apply adjustment factor
        effort_hours *= adjustment_factor

        # Calculate PERT estimates (optimistic, likely, pessimistic)
        optimistic = effort_hours * 0.75
        likely = effort_hours
        pessimistic = effort_hours * 1.5

        # Calculate confidence based on model accuracy and calibration data
        confidence = self._calculate_confidence(model)

        # Get applied factors for transparency
        factors_applied = self._get_applied_factors(model, complexity_factors or {})

        logger.info(
            f"Estimated project {project.id}: {effort_hours:.2f} hours "
            f"(optimistic: {optimistic:.2f}, pessimistic: {pessimistic:.2f})"
        )

        return EstimateResponse(
            estimate_id=uuid4(),
            project_id=project.id,
            estimated_hours=round(effort_hours, 2),
            optimistic_hours=round(optimistic, 2),
            likely_hours=round(likely, 2),
            pessimistic_hours=round(pessimistic, 2),
            confidence=round(confidence, 2),
            model_id=model.id,
            model_name=model.name,
            factors_applied=factors_applied,
            created_at=datetime.utcnow(),
        )

    def _estimate_size_from_requirements(self, project: Project) -> float:
        """Estimate project size in KLOC from requirements.

        Uses a heuristic approach based on requirement count, complexity,
        and project category.

        Args:
            project: Project with requirements

        Returns:
            Estimated size in KLOC
        """
        # Base KLOC per requirement by category
        base_kloc_per_req = {
            ProjectCategory.SOFTWARE_DEVELOPMENT: 0.8,
            ProjectCategory.IT_CONSULTING: 0.3,
            ProjectCategory.INFRASTRUCTURE: 0.5,
            ProjectCategory.MIXED: 0.6,
        }

        base_kloc = base_kloc_per_req.get(project.category, 0.5)

        # Count requirements by type
        functional_count = len(project.get_functional_requirements())
        non_functional_count = len(project.get_non_functional_requirements())

        # Functional requirements contribute more to size
        estimated_kloc = (functional_count * base_kloc) + (non_functional_count * base_kloc * 0.5)

        # Adjust for high-priority requirements (typically more complex)
        high_priority_count = len(project.get_high_priority_requirements())
        if high_priority_count > 0:
            complexity_multiplier = 1.0 + (high_priority_count / len(project.requirements) * 0.2)
            estimated_kloc *= complexity_multiplier

        # Minimum size constraint
        return max(estimated_kloc, 0.5)

    def _calculate_cocomo_effort(
        self,
        model: EstimationModel,
        size_kloc: float,
        complexity_factors: Dict[str, str],
    ) -> float:
        """Calculate effort using Intermediate COCOMO II formula.

        Effort = A × (Size)^B × EAF
        Where:
        - A = base constant (2.94 for COCOMO II)
        - B = scale factor exponent
        - EAF = Effort Adjustment Factor (product of cost drivers)

        Args:
            model: Estimation model with COCOMO parameters
            size_kloc: Project size in KLOC
            complexity_factors: Complexity factors from user input

        Returns:
            Estimated effort in person-months (converted to hours)
        """
        # Base constant for COCOMO II
        A = 2.94

        # Calculate scale exponent B
        B = self._calculate_scale_exponent(model.cocomo_parameters)

        # Calculate Effort Adjustment Factor (EAF)
        eaf = self._calculate_effort_adjustment_factor(
            model.cocomo_parameters,
            complexity_factors,
        )

        # Calculate nominal effort in person-months
        effort_pm = A * (size_kloc ** B) * eaf

        # Convert person-months to hours (assuming 152 hours per person-month)
        effort_hours = effort_pm * 152

        logger.debug(
            f"COCOMO calculation: A={A}, B={B:.2f}, Size={size_kloc:.2f} KLOC, "
            f"EAF={eaf:.2f}, Effort={effort_hours:.2f} hours"
        )

        return effort_hours

    def _calculate_scale_exponent(self, params: COCOMOParameters) -> float:
        """Calculate the scale exponent B from scale factors.

        B = 0.91 + 0.01 × Σ(SF_i)

        Args:
            params: COCOMO parameters with scale factors

        Returns:
            Scale exponent B
        """
        scale_factor_sum = sum(params.scale_factors.values())
        B = 0.91 + (0.01 * scale_factor_sum)
        return B

    def _calculate_effort_adjustment_factor(
        self,
        params: COCOMOParameters,
        complexity_factors: Dict[str, str],
    ) -> float:
        """Calculate Effort Adjustment Factor (EAF) from cost drivers.

        EAF = Π(cost_driver_i)

        Adjusts cost drivers based on user-provided complexity factors.

        Args:
            params: COCOMO parameters with cost drivers
            complexity_factors: User-provided complexity factors

        Returns:
            Effort Adjustment Factor
        """
        eaf = 1.0

        # Apply cost drivers
        for driver, nominal_value in params.cost_drivers.items():
            # Check if user provided a complexity factor that affects this driver
            adjusted_value = self._adjust_cost_driver(
                driver,
                nominal_value,
                complexity_factors,
            )
            eaf *= adjusted_value

        return eaf

    def _adjust_cost_driver(
        self,
        driver: str,
        nominal_value: float,
        complexity_factors: Dict[str, str],
    ) -> float:
        """Adjust cost driver based on complexity factors.

        Args:
            driver: Cost driver name
            nominal_value: Nominal cost driver value
            complexity_factors: User-provided complexity factors

        Returns:
            Adjusted cost driver value
        """
        # Map complexity levels to multipliers
        complexity_multipliers = {
            "very_low": 0.70,
            "low": 0.85,
            "nominal": 1.00,
            "high": 1.15,
            "very_high": 1.30,
            "extra_high": 1.50,
        }

        # Check for relevant complexity factors
        for factor_key, factor_value in complexity_factors.items():
            if factor_key.lower() in driver.lower():
                multiplier = complexity_multipliers.get(
                    factor_value.lower(),
                    1.0
                )
                return nominal_value * multiplier

        return nominal_value

    def _calculate_confidence(self, model: EstimationModel) -> float:
        """Calculate confidence score for the estimation.

        Based on:
        - Model accuracy metrics (R², within 25% target)
        - Number of calibration points
        - Recency of calibration data

        Args:
            model: Estimation model

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from R-squared
        confidence = model.accuracy_metrics.r_squared

        # Adjust based on calibration data sufficiency
        if model.has_sufficient_calibration_data(min_points=10):
            confidence *= 1.1  # Boost for sufficient data
        else:
            # Penalize for insufficient data
            data_ratio = model.get_calibration_count() / 10
            confidence *= data_ratio

        # Adjust based on accuracy target
        if model.accuracy_metrics.meets_target_accuracy():
            confidence *= 1.05  # Boost for meeting target
        else:
            # Penalize for missing target
            accuracy_ratio = model.accuracy_metrics.within_25_percent / 70.0
            confidence *= accuracy_ratio

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))

    def _get_applied_factors(
        self,
        model: EstimationModel,
        complexity_factors: Dict[str, str],
    ) -> Dict[str, float]:
        """Get dictionary of applied factors for transparency.

        Args:
            model: Estimation model
            complexity_factors: User-provided complexity factors

        Returns:
            Dictionary of factor names and values
        """
        factors = {
            "scale_exponent": self._calculate_scale_exponent(model.cocomo_parameters),
            "effort_adjustment_factor": self._calculate_effort_adjustment_factor(
                model.cocomo_parameters,
                complexity_factors,
            ),
        }

        # Add scale factors
        for name, value in model.cocomo_parameters.scale_factors.items():
            factors[f"scale_factor_{name}"] = value

        return factors

    def add_calibration_point(
        self,
        project_category: ProjectCategory,
        calibration_request: CalibrationRequest,
    ) -> AccuracyMetricsResponse:
        """Add calibration point from completed project.

        Args:
            project_category: Category of the completed project
            calibration_request: Calibration data

        Returns:
            Updated accuracy metrics

        Raises:
            ValueError: If no model exists for category
        """
        model = self._models.get(project_category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project_category}")

        # Calculate variance
        variance = (
            (calibration_request.actual_hours - calibration_request.estimated_hours)
            / calibration_request.estimated_hours
        ) * 100

        # Create calibration point
        calibration_point = CalibrationPoint(
            project_id=calibration_request.project_id,
            estimated_hours=calibration_request.estimated_hours,
            actual_hours=calibration_request.actual_hours,
            variance=variance,
            factors=calibration_request.factors,
        )

        # Add to model
        model.add_calibration_point(calibration_point)

        # Recalculate accuracy metrics
        from .calibration import CalibrationService
        calibration_service = CalibrationService()
        new_metrics = calibration_service.calculate_accuracy_metrics(model)
        model.update_accuracy_metrics(new_metrics)

        logger.info(
            f"Added calibration point for {project_category.value}: "
            f"variance={variance:.2f}%, "
            f"within_25_percent={new_metrics.within_25_percent:.2f}%"
        )

        return AccuracyMetricsResponse(
            model_id=model.id,
            model_name=model.name,
            mean_absolute_error=new_metrics.mean_absolute_error,
            mean_squared_error=new_metrics.mean_squared_error,
            r_squared=new_metrics.r_squared,
            within_25_percent=new_metrics.within_25_percent,
            calibration_count=model.get_calibration_count(),
            last_updated=model.last_updated,
        )

    def get_accuracy_metrics(
        self,
        project_category: ProjectCategory,
    ) -> AccuracyMetricsResponse:
        """Get current accuracy metrics for a model.

        Args:
            project_category: Category of the estimation model

        Returns:
            Current accuracy metrics

        Raises:
            ValueError: If no model exists for category
        """
        model = self._models.get(project_category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project_category}")

        return AccuracyMetricsResponse(
            model_id=model.id,
            model_name=model.name,
            mean_absolute_error=model.accuracy_metrics.mean_absolute_error,
            mean_squared_error=model.accuracy_metrics.mean_squared_error,
            r_squared=model.accuracy_metrics.r_squared,
            within_25_percent=model.accuracy_metrics.within_25_percent,
            calibration_count=model.get_calibration_count(),
            last_updated=model.last_updated,
        )

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on estimation service.

        Returns:
            Health status and metrics
        """
        health = {
            "status": "healthy",
            "models": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        for category, model in self._models.items():
            model_health = {
                "name": model.name,
                "calibration_points": model.get_calibration_count(),
                "accuracy": model.accuracy_metrics.within_25_percent,
                "needs_recalibration": model.needs_recalibration(),
                "last_updated": model.last_updated.isoformat(),
            }
            health["models"][category.value] = model_health

        return health


# Singleton instance
_estimation_service: Optional[EstimationService] = None


def get_estimation_service() -> EstimationService:
    """Get or create the estimation service singleton.

    Returns:
        EstimationService instance
    """
    global _estimation_service
    if _estimation_service is None:
        _estimation_service = EstimationService()
    return _estimation_service
