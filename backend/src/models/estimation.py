"""Estimation entity model for the AI Offer Agent system."""

from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .project import ProjectCategory


class COCOMOParameters(BaseModel):
    """COCOMO II model parameters for effort estimation.

    Contains the calibrated parameters for the Intermediate COCOMO II
    estimation model, including effort multipliers, scale factors, and
    cost drivers specific to different project categories.
    """

    effort_multipliers: Dict[str, float] = Field(
        default_factory=dict,
        description="Effort adjustment multipliers for various factors"
    )
    scale_factors: Dict[str, float] = Field(
        default_factory=dict,
        description="Scale factors affecting project complexity (precedentedness, development flexibility, etc.)"
    )
    cost_drivers: Dict[str, float] = Field(
        default_factory=dict,
        description="Cost drivers affecting effort (product, platform, personnel, project factors)"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "effort_multipliers": {
                    "nominal": 1.0,
                    "simple": 0.85,
                    "complex": 1.15
                },
                "scale_factors": {
                    "precedentedness": 3.72,
                    "development_flexibility": 2.03,
                    "architecture_risk_resolution": 4.24,
                    "team_cohesion": 3.29,
                    "process_maturity": 4.68
                },
                "cost_drivers": {
                    "product_complexity": 1.0,
                    "required_reusability": 1.0,
                    "analyst_capability": 0.85,
                    "programmer_capability": 0.88,
                    "application_experience": 0.91
                }
            }
        }


class CalibrationPoint(BaseModel):
    """Historical data point used for model calibration.

    Represents actual project data comparing estimated vs actual hours,
    used to continuously improve the estimation model's accuracy.
    """

    project_id: UUID = Field(
        ...,
        description="Reference to the completed project"
    )
    estimated_hours: float = Field(
        ...,
        gt=0,
        description="Originally estimated hours for the project"
    )
    actual_hours: float = Field(
        ...,
        gt=0,
        description="Actual hours spent on the project"
    )
    variance: float = Field(
        ...,
        description="Percentage variance between estimated and actual ((actual - estimated) / estimated * 100)"
    )
    factors: Dict[str, Any] = Field(
        default_factory=dict,
        description="Project-specific factors that influenced the variance (complexity, team experience, etc.)"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "project_id": "123e4567-e89b-12d3-a456-426614174000",
                "estimated_hours": 500.0,
                "actual_hours": 475.0,
                "variance": -5.0,
                "factors": {
                    "team_experience": "high",
                    "requirements_stability": "stable",
                    "technology_familiarity": "expert",
                    "scope_changes": 2
                }
            }
        }

    def is_within_target_variance(self, target_percent: float = 25.0) -> bool:
        """Check if variance is within acceptable target range.

        Args:
            target_percent: Target variance percentage (default: 25%)

        Returns:
            True if absolute variance is within target range
        """
        return abs(self.variance) <= target_percent


class AccuracyMetrics(BaseModel):
    """Statistical metrics measuring estimation model accuracy.

    Tracks various accuracy metrics to evaluate and improve the
    estimation model's performance over time.
    """

    mean_absolute_error: float = Field(
        ...,
        ge=0,
        description="Average absolute difference between estimated and actual hours"
    )
    mean_squared_error: float = Field(
        ...,
        ge=0,
        description="Average squared difference (penalizes larger errors more)"
    )
    r_squared: float = Field(
        ...,
        ge=0,
        le=1,
        description="Coefficient of determination (0 to 1, higher is better)"
    )
    within_25_percent: float = Field(
        ...,
        ge=0,
        le=100,
        description="Percentage of estimates within ±25% of actual hours"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "mean_absolute_error": 42.5,
                "mean_squared_error": 2156.25,
                "r_squared": 0.87,
                "within_25_percent": 78.5
            }
        }

    def meets_target_accuracy(self, min_within_25_percent: float = 70.0) -> bool:
        """Check if model meets minimum accuracy target.

        Args:
            min_within_25_percent: Minimum percentage required (default: 70%)

        Returns:
            True if accuracy meets or exceeds target
        """
        return self.within_25_percent >= min_within_25_percent

    def is_good_fit(self, min_r_squared: float = 0.75) -> bool:
        """Check if model provides a good statistical fit.

        Args:
            min_r_squared: Minimum R² value required (default: 0.75)

        Returns:
            True if R² indicates good fit
        """
        return self.r_squared >= min_r_squared


class EstimationModel(BaseModel):
    """Estimation model entity for project effort calculation.

    Manages COCOMO II-based estimation models calibrated for specific
    project categories. Includes historical calibration data and accuracy
    metrics for continuous learning and improvement.

    Invariants:
    - Must maintain ±25% variance target
    - Calibration data retained for continuous learning
    - Model updated after each completed project
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(
        ...,
        min_length=1,
        description="Descriptive name for the estimation model"
    )
    project_category: ProjectCategory = Field(
        ...,
        description="Project category this model is calibrated for"
    )
    cocomo_parameters: COCOMOParameters = Field(
        ...,
        description="COCOMO II parameters for this model"
    )
    calibration_data: List[CalibrationPoint] = Field(
        default_factory=list,
        description="Historical project data used for calibration"
    )
    accuracy_metrics: AccuracyMetrics = Field(
        ...,
        description="Current accuracy metrics for this model"
    )
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp of last model update or calibration"
    )

    class Config:
        frozen = False
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "Software Development Estimation Model - 2025",
                "project_category": "software_development",
                "cocomo_parameters": {
                    "effort_multipliers": {
                        "nominal": 1.0,
                        "simple": 0.85,
                        "complex": 1.15
                    },
                    "scale_factors": {
                        "precedentedness": 3.72,
                        "development_flexibility": 2.03,
                        "architecture_risk_resolution": 4.24,
                        "team_cohesion": 3.29,
                        "process_maturity": 4.68
                    },
                    "cost_drivers": {
                        "product_complexity": 1.0,
                        "required_reusability": 1.0,
                        "analyst_capability": 0.85,
                        "programmer_capability": 0.88
                    }
                },
                "calibration_data": [
                    {
                        "project_id": "123e4567-e89b-12d3-a456-426614174000",
                        "estimated_hours": 500.0,
                        "actual_hours": 475.0,
                        "variance": -5.0,
                        "factors": {
                            "team_experience": "high"
                        }
                    }
                ],
                "accuracy_metrics": {
                    "mean_absolute_error": 42.5,
                    "mean_squared_error": 2156.25,
                    "r_squared": 0.87,
                    "within_25_percent": 78.5
                },
                "last_updated": "2025-09-30T12:00:00Z"
            }
        }

    def add_calibration_point(self, calibration_point: CalibrationPoint) -> None:
        """Add a new calibration point from a completed project.

        Args:
            calibration_point: Historical project data point
        """
        self.calibration_data.append(calibration_point)
        self.last_updated = datetime.utcnow()

    def get_recent_calibration_points(self, limit: int = 10) -> List[CalibrationPoint]:
        """Get the most recent calibration points.

        Args:
            limit: Maximum number of points to return (default: 10)

        Returns:
            List of most recent calibration points
        """
        return self.calibration_data[-limit:]

    def calculate_average_variance(self) -> float:
        """Calculate average variance across all calibration points.

        Returns:
            Average variance percentage, or 0.0 if no calibration data
        """
        if not self.calibration_data:
            return 0.0

        total_variance = sum(point.variance for point in self.calibration_data)
        return total_variance / len(self.calibration_data)

    def get_points_within_target(self, target_percent: float = 25.0) -> List[CalibrationPoint]:
        """Get calibration points within target variance.

        Args:
            target_percent: Target variance percentage (default: 25%)

        Returns:
            List of calibration points within target variance
        """
        return [
            point for point in self.calibration_data
            if point.is_within_target_variance(target_percent)
        ]

    def calculate_accuracy_rate(self, target_percent: float = 25.0) -> float:
        """Calculate percentage of estimates within target variance.

        Args:
            target_percent: Target variance percentage (default: 25%)

        Returns:
            Percentage (0-100) of estimates within target
        """
        if not self.calibration_data:
            return 0.0

        within_target = len(self.get_points_within_target(target_percent))
        return (within_target / len(self.calibration_data)) * 100

    def needs_recalibration(self, min_accuracy: float = 70.0) -> bool:
        """Check if model needs recalibration based on accuracy.

        Args:
            min_accuracy: Minimum acceptable accuracy percentage (default: 70%)

        Returns:
            True if model accuracy is below minimum threshold
        """
        return not self.accuracy_metrics.meets_target_accuracy(min_accuracy)

    def update_accuracy_metrics(self, new_metrics: AccuracyMetrics) -> None:
        """Update the model's accuracy metrics.

        Args:
            new_metrics: New accuracy metrics calculated from calibration data
        """
        self.accuracy_metrics = new_metrics
        self.last_updated = datetime.utcnow()

    def get_calibration_count(self) -> int:
        """Get total number of calibration points.

        Returns:
            Number of calibration points
        """
        return len(self.calibration_data)

    def has_sufficient_calibration_data(self, min_points: int = 10) -> bool:
        """Check if model has sufficient calibration data.

        Args:
            min_points: Minimum number of calibration points required (default: 10)

        Returns:
            True if calibration data meets minimum requirement
        """
        return self.get_calibration_count() >= min_points
