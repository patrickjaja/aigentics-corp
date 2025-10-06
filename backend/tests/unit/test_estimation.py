"""
Unit tests for COCOMO estimation calculations.

Tests all estimation formulas, calibration logic, and accuracy metric calculations
to ensure 100% coverage of business logic.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from src.models.estimation import (
    COCOMOParameters,
    CalibrationPoint,
    AccuracyMetrics,
    EstimationModel,
)
from src.models.project import Project, ProjectCategory, ProjectRequirement, RequirementType
from src.services.estimation.main import EstimationService
from src.services.estimation.calibration import CalibrationService


class TestCalibrationPoint:
    """Test cases for CalibrationPoint entity."""

    def test_calibration_point_creation(self):
        """Test creation of calibration point."""
        point = CalibrationPoint(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=475.0,
            variance=-5.0,
            factors={"team_experience": "high"},
        )
        assert point.estimated_hours == 500.0
        assert point.actual_hours == 475.0
        assert point.variance == -5.0

    def test_calibration_point_within_target_variance(self):
        """Test checking if variance is within target."""
        point = CalibrationPoint(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=475.0,
            variance=-5.0,
            factors={},
        )
        assert point.is_within_target_variance(target_percent=25.0)
        assert point.is_within_target_variance(target_percent=10.0)
        assert not point.is_within_target_variance(target_percent=3.0)

    def test_calibration_point_positive_variance(self):
        """Test calibration point with positive variance (over-budget)."""
        point = CalibrationPoint(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=600.0,
            variance=20.0,
            factors={},
        )
        assert point.variance == 20.0
        assert point.is_within_target_variance(target_percent=25.0)

    def test_calibration_point_outside_target(self):
        """Test calibration point outside target variance."""
        point = CalibrationPoint(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=700.0,
            variance=40.0,
            factors={},
        )
        assert not point.is_within_target_variance(target_percent=25.0)


class TestAccuracyMetrics:
    """Test cases for AccuracyMetrics entity."""

    def test_accuracy_metrics_creation(self):
        """Test creation of accuracy metrics."""
        metrics = AccuracyMetrics(
            mean_absolute_error=42.5,
            mean_squared_error=2156.25,
            r_squared=0.87,
            within_25_percent=78.5,
        )
        assert metrics.mean_absolute_error == 42.5
        assert metrics.r_squared == 0.87
        assert metrics.within_25_percent == 78.5

    def test_accuracy_metrics_meets_target(self):
        """Test checking if accuracy meets target."""
        metrics = AccuracyMetrics(
            mean_absolute_error=30.0,
            mean_squared_error=1000.0,
            r_squared=0.85,
            within_25_percent=75.0,
        )
        assert metrics.meets_target_accuracy(min_within_25_percent=70.0)
        assert not metrics.meets_target_accuracy(min_within_25_percent=80.0)

    def test_accuracy_metrics_is_good_fit(self):
        """Test checking if model provides good statistical fit."""
        good_metrics = AccuracyMetrics(
            mean_absolute_error=20.0,
            mean_squared_error=500.0,
            r_squared=0.85,
            within_25_percent=80.0,
        )
        assert good_metrics.is_good_fit(min_r_squared=0.75)

        poor_metrics = AccuracyMetrics(
            mean_absolute_error=100.0,
            mean_squared_error=15000.0,
            r_squared=0.60,
            within_25_percent=50.0,
        )
        assert not poor_metrics.is_good_fit(min_r_squared=0.75)

    def test_accuracy_metrics_boundary_values(self):
        """Test accuracy metrics at boundary values."""
        perfect_metrics = AccuracyMetrics(
            mean_absolute_error=0.0,
            mean_squared_error=0.0,
            r_squared=1.0,
            within_25_percent=100.0,
        )
        assert perfect_metrics.meets_target_accuracy()
        assert perfect_metrics.is_good_fit()


class TestEstimationModel:
    """Test cases for EstimationModel entity."""

    def create_test_model(self) -> EstimationModel:
        """Create a test estimation model."""
        return EstimationModel(
            id=uuid4(),
            name="Test Estimation Model",
            project_category=ProjectCategory.SOFTWARE_DEVELOPMENT,
            cocomo_parameters=COCOMOParameters(
                effort_multipliers={"nominal": 1.0, "simple": 0.85, "complex": 1.15},
                scale_factors={
                    "precedentedness": 3.72,
                    "development_flexibility": 2.03,
                    "architecture_risk_resolution": 4.24,
                    "team_cohesion": 3.29,
                    "process_maturity": 4.68,
                },
                cost_drivers={
                    "product_complexity": 1.0,
                    "analyst_capability": 0.85,
                    "programmer_capability": 0.88,
                },
            ),
            calibration_data=[],
            accuracy_metrics=AccuracyMetrics(
                mean_absolute_error=0.0,
                mean_squared_error=0.0,
                r_squared=0.0,
                within_25_percent=0.0,
            ),
        )

    def test_estimation_model_creation(self):
        """Test creation of estimation model."""
        model = self.create_test_model()
        assert model.name == "Test Estimation Model"
        assert model.project_category == ProjectCategory.SOFTWARE_DEVELOPMENT
        assert len(model.calibration_data) == 0

    def test_add_calibration_point(self):
        """Test adding calibration point to model."""
        model = self.create_test_model()
        point = CalibrationPoint(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=475.0,
            variance=-5.0,
            factors={},
        )
        model.add_calibration_point(point)
        assert len(model.calibration_data) == 1
        assert model.calibration_data[0] == point

    def test_get_recent_calibration_points(self):
        """Test retrieving recent calibration points."""
        model = self.create_test_model()

        # Add 15 calibration points
        for i in range(15):
            point = CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=500.0 + i * 10,
                actual_hours=490.0 + i * 10,
                variance=-2.0,
                factors={},
            )
            model.add_calibration_point(point)

        # Get last 10 points
        recent = model.get_recent_calibration_points(limit=10)
        assert len(recent) == 10
        # Should be the last 10 added
        assert recent[0].estimated_hours == 550.0

    def test_calculate_average_variance(self):
        """Test calculating average variance across calibration points."""
        model = self.create_test_model()

        # Add points with different variances
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=500.0,
                actual_hours=475.0,
                variance=-5.0,
                factors={},
            )
        )
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=600.0,
                actual_hours=630.0,
                variance=5.0,
                factors={},
            )
        )
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=400.0,
                actual_hours=400.0,
                variance=0.0,
                factors={},
            )
        )

        avg_variance = model.calculate_average_variance()
        assert avg_variance == 0.0  # (-5 + 5 + 0) / 3

    def test_calculate_average_variance_empty(self):
        """Test calculating average variance with no data."""
        model = self.create_test_model()
        assert model.calculate_average_variance() == 0.0

    def test_get_points_within_target(self):
        """Test filtering calibration points within target variance."""
        model = self.create_test_model()

        # Add points with different variances
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=500.0,
                actual_hours=475.0,
                variance=-5.0,
                factors={},
            )
        )
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=500.0,
                actual_hours=650.0,
                variance=30.0,  # Outside 25% target
                factors={},
            )
        )
        model.add_calibration_point(
            CalibrationPoint(
                project_id=uuid4(),
                estimated_hours=500.0,
                actual_hours=600.0,
                variance=20.0,
                factors={},
            )
        )

        within_target = model.get_points_within_target(target_percent=25.0)
        assert len(within_target) == 2

    def test_calculate_accuracy_rate(self):
        """Test calculating accuracy rate."""
        model = self.create_test_model()

        # Add 10 points, 7 within target
        for i in range(7):
            model.add_calibration_point(
                CalibrationPoint(
                    project_id=uuid4(),
                    estimated_hours=500.0,
                    actual_hours=490.0,
                    variance=-2.0,
                    factors={},
                )
            )
        for i in range(3):
            model.add_calibration_point(
                CalibrationPoint(
                    project_id=uuid4(),
                    estimated_hours=500.0,
                    actual_hours=700.0,
                    variance=40.0,
                    factors={},
                )
            )

        accuracy_rate = model.calculate_accuracy_rate(target_percent=25.0)
        assert accuracy_rate == 70.0

    def test_needs_recalibration(self):
        """Test checking if model needs recalibration."""
        model = self.create_test_model()

        # Model with poor accuracy
        model.accuracy_metrics = AccuracyMetrics(
            mean_absolute_error=100.0,
            mean_squared_error=15000.0,
            r_squared=0.50,
            within_25_percent=60.0,  # Below 70% threshold
        )
        assert model.needs_recalibration(min_accuracy=70.0)

        # Model with good accuracy
        model.accuracy_metrics = AccuracyMetrics(
            mean_absolute_error=30.0,
            mean_squared_error=1000.0,
            r_squared=0.85,
            within_25_percent=80.0,
        )
        assert not model.needs_recalibration(min_accuracy=70.0)

    def test_update_accuracy_metrics(self):
        """Test updating model accuracy metrics."""
        model = self.create_test_model()
        old_timestamp = model.last_updated

        new_metrics = AccuracyMetrics(
            mean_absolute_error=25.0,
            mean_squared_error=750.0,
            r_squared=0.90,
            within_25_percent=85.0,
        )

        model.update_accuracy_metrics(new_metrics)
        assert model.accuracy_metrics == new_metrics
        assert model.last_updated > old_timestamp

    def test_has_sufficient_calibration_data(self):
        """Test checking for sufficient calibration data."""
        model = self.create_test_model()

        # Initially no data
        assert not model.has_sufficient_calibration_data(min_points=10)

        # Add 10 points
        for i in range(10):
            model.add_calibration_point(
                CalibrationPoint(
                    project_id=uuid4(),
                    estimated_hours=500.0,
                    actual_hours=490.0,
                    variance=-2.0,
                    factors={},
                )
            )

        assert model.has_sufficient_calibration_data(min_points=10)
        assert not model.has_sufficient_calibration_data(min_points=15)


class TestCOCOMOCalculations:
    """Test cases for COCOMO II calculation formulas."""

    def test_scale_exponent_calculation(self):
        """Test calculation of scale exponent B."""
        service = EstimationService()
        params = COCOMOParameters(
            effort_multipliers={},
            scale_factors={
                "precedentedness": 3.72,
                "development_flexibility": 2.03,
                "architecture_risk_resolution": 4.24,
                "team_cohesion": 3.29,
                "process_maturity": 4.68,
            },
            cost_drivers={},
        )

        # B = 0.91 + 0.01 × Σ(SF_i)
        # Sum = 3.72 + 2.03 + 4.24 + 3.29 + 4.68 = 17.96
        # B = 0.91 + 0.01 × 17.96 = 1.0896
        B = service._calculate_scale_exponent(params)
        assert abs(B - 1.0896) < 0.001

    def test_effort_adjustment_factor_nominal(self):
        """Test EAF calculation with nominal cost drivers."""
        service = EstimationService()
        params = COCOMOParameters(
            effort_multipliers={},
            scale_factors={},
            cost_drivers={
                "product_complexity": 1.0,
                "analyst_capability": 1.0,
                "programmer_capability": 1.0,
            },
        )

        # All nominal values should multiply to 1.0
        eaf = service._calculate_effort_adjustment_factor(params, {})
        assert eaf == 1.0

    def test_effort_adjustment_factor_with_adjustments(self):
        """Test EAF calculation with adjusted cost drivers."""
        service = EstimationService()
        params = COCOMOParameters(
            effort_multipliers={},
            scale_factors={},
            cost_drivers={
                "product_complexity": 1.0,
                "analyst_capability": 0.85,
                "programmer_capability": 0.88,
            },
        )

        # EAF = 1.0 × 0.85 × 0.88 = 0.748
        eaf = service._calculate_effort_adjustment_factor(params, {})
        assert abs(eaf - 0.748) < 0.001

    def test_cocomo_effort_calculation_basic(self):
        """Test basic COCOMO effort calculation."""
        service = EstimationService()
        model = service._models[ProjectCategory.SOFTWARE_DEVELOPMENT]

        # Calculate effort for 10 KLOC project
        effort_hours = service._calculate_cocomo_effort(
            model=model,
            size_kloc=10.0,
            complexity_factors={},
        )

        # Effort should be positive and reasonable
        assert effort_hours > 0
        # Rough sanity check: 10 KLOC should take hundreds to thousands of hours
        assert 500 < effort_hours < 5000

    def test_cocomo_effort_scales_with_size(self):
        """Test that effort scales appropriately with project size."""
        service = EstimationService()
        model = service._models[ProjectCategory.SOFTWARE_DEVELOPMENT]

        effort_10k = service._calculate_cocomo_effort(
            model=model,
            size_kloc=10.0,
            complexity_factors={},
        )

        effort_20k = service._calculate_cocomo_effort(
            model=model,
            size_kloc=20.0,
            complexity_factors={},
        )

        # Effort should more than double (non-linear relationship)
        assert effort_20k > 2 * effort_10k

    def test_cost_driver_adjustment(self):
        """Test cost driver adjustment based on complexity factors."""
        service = EstimationService()

        # Test with "high" complexity
        adjusted_high = service._adjust_cost_driver(
            driver="programmer_capability",
            nominal_value=1.0,
            complexity_factors={"programmer": "high"},
        )
        assert adjusted_high == 1.15

        # Test with "very_low" complexity
        adjusted_low = service._adjust_cost_driver(
            driver="analyst_capability",
            nominal_value=1.0,
            complexity_factors={"analyst": "very_low"},
        )
        assert adjusted_low == 0.70

        # Test with no matching factor
        adjusted_none = service._adjust_cost_driver(
            driver="product_complexity",
            nominal_value=1.0,
            complexity_factors={"other_factor": "high"},
        )
        assert adjusted_none == 1.0


class TestEstimationService:
    """Test cases for EstimationService."""

    def create_test_project(self) -> Project:
        """Create a test project."""
        return Project(
            id=uuid4(),
            customer_id=uuid4(),
            name="Test Project",
            category=ProjectCategory.SOFTWARE_DEVELOPMENT,
            requirements=[
                ProjectRequirement(
                    id=uuid4(),
                    type=RequirementType.FUNCTIONAL,
                    description="User authentication",
                    priority="high",
                ),
                ProjectRequirement(
                    id=uuid4(),
                    type=RequirementType.FUNCTIONAL,
                    description="Dashboard",
                    priority="medium",
                ),
                ProjectRequirement(
                    id=uuid4(),
                    type=RequirementType.NON_FUNCTIONAL,
                    description="Performance",
                    priority="high",
                ),
            ],
        )

    def test_service_initialization(self):
        """Test that service initializes with models for all categories."""
        service = EstimationService()
        assert len(service._models) == len(ProjectCategory)

        for category in ProjectCategory:
            assert category in service._models
            assert service._models[category].project_category == category

    def test_estimate_project_basic(self):
        """Test basic project estimation."""
        service = EstimationService()
        project = self.create_test_project()

        estimate = service.estimate_project(
            project=project,
            size_kloc=5.0,
        )

        assert estimate.project_id == project.id
        assert estimate.estimated_hours > 0
        assert estimate.optimistic_hours < estimate.likely_hours
        assert estimate.likely_hours < estimate.pessimistic_hours
        assert 0 <= estimate.confidence <= 1.0

    def test_estimate_project_pert_estimates(self):
        """Test PERT estimates (optimistic, likely, pessimistic)."""
        service = EstimationService()
        project = self.create_test_project()

        estimate = service.estimate_project(
            project=project,
            size_kloc=5.0,
        )

        # Optimistic should be 75% of likely
        assert abs(estimate.optimistic_hours - estimate.likely_hours * 0.75) < 1.0
        # Pessimistic should be 150% of likely
        assert abs(estimate.pessimistic_hours - estimate.likely_hours * 1.5) < 1.0

    def test_estimate_project_with_adjustment_factor(self):
        """Test project estimation with manual adjustment factor."""
        service = EstimationService()
        project = self.create_test_project()

        estimate_normal = service.estimate_project(
            project=project,
            size_kloc=5.0,
            adjustment_factor=1.0,
        )

        estimate_adjusted = service.estimate_project(
            project=project,
            size_kloc=5.0,
            adjustment_factor=1.5,
        )

        # Adjusted estimate should be 1.5x the normal estimate
        assert abs(estimate_adjusted.estimated_hours - estimate_normal.estimated_hours * 1.5) < 1.0

    def test_estimate_size_from_requirements(self):
        """Test estimating project size from requirements."""
        service = EstimationService()
        project = self.create_test_project()

        size_kloc = service._estimate_size_from_requirements(project)

        # Should estimate positive size
        assert size_kloc > 0
        # Should be at least the minimum (0.5 KLOC)
        assert size_kloc >= 0.5

    def test_estimate_project_without_size(self):
        """Test project estimation without explicit size (auto-estimate)."""
        service = EstimationService()
        project = self.create_test_project()

        estimate = service.estimate_project(project=project)

        assert estimate.estimated_hours > 0
        assert estimate.confidence >= 0

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        service = EstimationService()
        model = service._models[ProjectCategory.SOFTWARE_DEVELOPMENT]

        # Update with good metrics
        model.accuracy_metrics = AccuracyMetrics(
            mean_absolute_error=30.0,
            mean_squared_error=1000.0,
            r_squared=0.85,
            within_25_percent=80.0,
        )

        # Add sufficient calibration data
        for i in range(15):
            model.add_calibration_point(
                CalibrationPoint(
                    project_id=uuid4(),
                    estimated_hours=500.0,
                    actual_hours=490.0,
                    variance=-2.0,
                    factors={},
                )
            )

        confidence = service._calculate_confidence(model)
        assert 0 <= confidence <= 1.0
        assert confidence > 0.7  # Should be high with good metrics

    def test_add_calibration_point_service(self):
        """Test adding calibration point through service."""
        service = EstimationService()
        from src.services.estimation.main import CalibrationRequest

        request = CalibrationRequest(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=475.0,
            factors={"team_experience": "high"},
        )

        response = service.add_calibration_point(
            project_category=ProjectCategory.SOFTWARE_DEVELOPMENT,
            calibration_request=request,
        )

        assert response.calibration_count == 1
        assert response.model_name is not None

    def test_get_accuracy_metrics_service(self):
        """Test retrieving accuracy metrics through service."""
        service = EstimationService()

        response = service.get_accuracy_metrics(
            project_category=ProjectCategory.SOFTWARE_DEVELOPMENT
        )

        assert response.model_id is not None
        assert response.calibration_count >= 0

    def test_health_check(self):
        """Test service health check."""
        service = EstimationService()
        health = service.health_check()

        assert health["status"] == "healthy"
        assert "models" in health
        assert len(health["models"]) == len(ProjectCategory)


class TestCalibrationService:
    """Test cases for CalibrationService."""

    def test_calculate_accuracy_metrics(self):
        """Test calculation of accuracy metrics from calibration data."""
        calibration_service = CalibrationService()

        # Create model with calibration data
        model = EstimationModel(
            id=uuid4(),
            name="Test Model",
            project_category=ProjectCategory.SOFTWARE_DEVELOPMENT,
            cocomo_parameters=COCOMOParameters(
                effort_multipliers={},
                scale_factors={},
                cost_drivers={},
            ),
            calibration_data=[],
            accuracy_metrics=AccuracyMetrics(
                mean_absolute_error=0.0,
                mean_squared_error=0.0,
                r_squared=0.0,
                within_25_percent=0.0,
            ),
        )

        # Add calibration points
        for i in range(10):
            variance = -5.0 + i  # Variances from -5% to +4%
            actual = 500.0 * (1 + variance / 100)
            model.add_calibration_point(
                CalibrationPoint(
                    project_id=uuid4(),
                    estimated_hours=500.0,
                    actual_hours=actual,
                    variance=variance,
                    factors={},
                )
            )

        # Calculate metrics
        metrics = calibration_service.calculate_accuracy_metrics(model)

        assert metrics.mean_absolute_error >= 0
        assert metrics.mean_squared_error >= 0
        assert 0 <= metrics.r_squared <= 1
        assert 0 <= metrics.within_25_percent <= 100
