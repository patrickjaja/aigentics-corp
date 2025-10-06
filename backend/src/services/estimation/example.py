"""Example usage of the Estimation Service.

This file demonstrates how to use the estimation service for project
effort estimation and calibration.
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from ...models.estimation import CalibrationPoint
from ...models.project import (
    Project,
    ProjectCategory,
    Requirement,
    RequirementType,
    Priority,
    ProjectConstraints,
)
from ...models.value_objects import Money
from .main import get_estimation_service, CalibrationRequest


def example_basic_estimation():
    """Example: Basic project estimation."""
    print("\n=== Basic Project Estimation ===\n")

    # Create a sample project
    project = Project(
        id=uuid4(),
        customer_id=uuid4(),
        name="E-Commerce Platform Development",
        description="Build a modern e-commerce platform with inventory management",
        category=ProjectCategory.SOFTWARE_DEVELOPMENT,
        requirements=[
            Requirement(
                id=uuid4(),
                description="Implement shopping cart functionality",
                priority=Priority.HIGH,
                type=RequirementType.FUNCTIONAL,
                acceptance_criteria=[
                    "Add/remove items from cart",
                    "Calculate totals with taxes",
                    "Save cart for logged-in users",
                ],
            ),
            Requirement(
                id=uuid4(),
                description="Payment gateway integration",
                priority=Priority.HIGH,
                type=RequirementType.FUNCTIONAL,
                acceptance_criteria=[
                    "Support credit card payments",
                    "Support PayPal",
                    "Handle payment failures gracefully",
                ],
            ),
            Requirement(
                id=uuid4(),
                description="Inventory management system",
                priority=Priority.MEDIUM,
                type=RequirementType.FUNCTIONAL,
                acceptance_criteria=[
                    "Track stock levels",
                    "Auto-reorder notifications",
                    "SKU management",
                ],
            ),
            Requirement(
                id=uuid4(),
                description="System performance requirements",
                priority=Priority.HIGH,
                type=RequirementType.NON_FUNCTIONAL,
                acceptance_criteria=[
                    "Page load < 2 seconds",
                    "Support 1000 concurrent users",
                    "99.9% uptime",
                ],
            ),
        ],
        constraints=ProjectConstraints(
            max_budget=Money(amount=Decimal("75000.00"), currency="EUR"),
        ),
    )

    # Get estimation service
    service = get_estimation_service()

    # Estimate the project
    estimate = service.estimate_project(
        project=project,
        size_kloc=None,  # Will be estimated from requirements
        complexity_factors={
            "team_experience": "high",
            "technology_familiarity": "medium",
            "product_complexity": "high",
        },
        adjustment_factor=1.0,
    )

    print(f"Project: {project.name}")
    print(f"Category: {project.category.value}")
    print(f"Requirements: {len(project.requirements)}")
    print(f"\nEstimation Results:")
    print(f"  Estimated hours: {estimate.estimated_hours:.2f}")
    print(f"  Optimistic: {estimate.optimistic_hours:.2f}")
    print(f"  Likely: {estimate.likely_hours:.2f}")
    print(f"  Pessimistic: {estimate.pessimistic_hours:.2f}")
    print(f"  Confidence: {estimate.confidence:.2%}")
    print(f"\nModel: {estimate.model_name}")
    print(f"Factors applied:")
    for factor, value in estimate.factors_applied.items():
        print(f"  {factor}: {value:.3f}")


def example_with_calibration():
    """Example: Estimation with historical calibration."""
    print("\n=== Estimation with Calibration ===\n")

    service = get_estimation_service()

    # Simulate adding calibration data from completed projects
    calibration_data = [
        CalibrationRequest(
            project_id=uuid4(),
            estimated_hours=500.0,
            actual_hours=475.0,
            factors={
                "team_experience": "high",
                "requirements_stability": "stable",
                "technology_familiarity": "expert",
            },
        ),
        CalibrationRequest(
            project_id=uuid4(),
            estimated_hours=800.0,
            actual_hours=850.0,
            factors={
                "team_experience": "medium",
                "requirements_stability": "unstable",
                "technology_familiarity": "medium",
            },
        ),
        CalibrationRequest(
            project_id=uuid4(),
            estimated_hours=1200.0,
            actual_hours=1100.0,
            factors={
                "team_experience": "high",
                "requirements_stability": "stable",
                "technology_familiarity": "high",
            },
        ),
    ]

    print("Adding calibration data from completed projects...\n")
    for i, calibration in enumerate(calibration_data, 1):
        metrics = service.add_calibration_point(
            project_category=ProjectCategory.SOFTWARE_DEVELOPMENT,
            calibration_request=calibration,
        )
        variance = ((calibration.actual_hours - calibration.estimated_hours)
                   / calibration.estimated_hours * 100)
        print(f"Project {i}: Estimated {calibration.estimated_hours:.0f}h, "
              f"Actual {calibration.actual_hours:.0f}h, "
              f"Variance {variance:+.1f}%")

    print(f"\nUpdated Accuracy Metrics:")
    metrics = service.get_accuracy_metrics(ProjectCategory.SOFTWARE_DEVELOPMENT)
    print(f"  MAE: {metrics.mean_absolute_error:.2f} hours")
    print(f"  MSE: {metrics.mean_squared_error:.2f}")
    print(f"  R²: {metrics.r_squared:.3f}")
    print(f"  Within ±25%: {metrics.within_25_percent:.1f}%")
    print(f"  Calibration points: {metrics.calibration_count}")


def example_accuracy_check():
    """Example: Check model accuracy and recommendations."""
    print("\n=== Model Accuracy Check ===\n")

    service = get_estimation_service()

    # Check accuracy for all project categories
    for category in ProjectCategory:
        print(f"\n{category.value.replace('_', ' ').title()}:")

        metrics = service.get_accuracy_metrics(category)
        print(f"  Calibration points: {metrics.calibration_count}")
        print(f"  Within ±25%: {metrics.within_25_percent:.1f}%")
        print(f"  R²: {metrics.r_squared:.3f}")

        if metrics.calibration_count > 0:
            if metrics.within_25_percent >= 70.0:
                print(f"  Status: ✓ Meeting accuracy target")
            else:
                print(f"  Status: ✗ Below accuracy target")


def example_health_check():
    """Example: Service health check."""
    print("\n=== Service Health Check ===\n")

    service = get_estimation_service()
    health = service.health_check()

    print(f"Status: {health['status']}")
    print(f"Timestamp: {health['timestamp']}")
    print(f"\nModels:")

    for category, model_health in health['models'].items():
        print(f"\n  {category.replace('_', ' ').title()}:")
        print(f"    Name: {model_health['name']}")
        print(f"    Calibration points: {model_health['calibration_points']}")
        print(f"    Accuracy: {model_health['accuracy']:.1f}%")
        print(f"    Needs recalibration: {model_health['needs_recalibration']}")
        print(f"    Last updated: {model_health['last_updated']}")


if __name__ == "__main__":
    """Run all examples."""
    print("=" * 60)
    print("Estimation Service Examples")
    print("=" * 60)

    example_basic_estimation()
    example_with_calibration()
    example_accuracy_check()
    example_health_check()

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("=" * 60 + "\n")
