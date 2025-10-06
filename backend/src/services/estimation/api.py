"""FastAPI endpoints for the Estimation Service.

This module provides REST API endpoints for:
- Project effort estimation
- Historical data calibration
- Accuracy metrics retrieval
- Service health checks
"""

import logging
from typing import Any, Dict
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...models.project import Project, ProjectCategory
from .main import (
    CalibrationRequest,
    EstimateRequest,
    EstimateResponse,
    AccuracyMetricsResponse,
    get_estimation_service,
)
from .calibration import CalibrationService

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/estimation",
    tags=["estimation"],
)


# Request/Response Models for API
class ProjectEstimateRequest(BaseModel):
    """API request model for project estimation."""

    project: Project
    size_kloc: float | None = None
    complexity_factors: Dict[str, str] = {}
    adjustment_factor: float = 1.0


class CalibrationStatsResponse(BaseModel):
    """Response model for calibration statistics."""

    model_id: UUID
    model_name: str
    statistics: Dict[str, Any]


class RecalibrationRecommendationResponse(BaseModel):
    """Response model for recalibration recommendation."""

    model_id: UUID
    model_name: str
    needs_recalibration: bool
    reasons: list[str]
    priority: str


@router.post("/estimate", response_model=EstimateResponse)
async def estimate_project(
    request: ProjectEstimateRequest,
) -> EstimateResponse:
    """Estimate project effort using COCOMO II model.

    Calculates effort estimation based on project requirements, size,
    and complexity factors using the Intermediate COCOMO II model.

    Args:
        request: Project estimation request with details

    Returns:
        EstimateResponse with effort estimates and confidence

    Raises:
        HTTPException: If estimation fails
    """
    try:
        service = get_estimation_service()

        estimate = service.estimate_project(
            project=request.project,
            size_kloc=request.size_kloc,
            complexity_factors=request.complexity_factors,
            adjustment_factor=request.adjustment_factor,
        )

        logger.info(
            f"Successfully estimated project {request.project.id}: "
            f"{estimate.estimated_hours:.2f} hours"
        )

        return estimate

    except ValueError as e:
        logger.error(f"Validation error during estimation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during estimation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during estimation",
        )


@router.post("/calibration/{project_category}", response_model=AccuracyMetricsResponse)
async def add_calibration_data(
    project_category: ProjectCategory,
    calibration: CalibrationRequest,
) -> AccuracyMetricsResponse:
    """Add calibration data from a completed project.

    Updates the estimation model for the specified project category
    with actual project data to improve accuracy.

    Args:
        project_category: Category of the completed project
        calibration: Calibration data with estimated vs actual hours

    Returns:
        Updated accuracy metrics for the model

    Raises:
        HTTPException: If calibration fails
    """
    try:
        service = get_estimation_service()

        metrics = service.add_calibration_point(
            project_category=project_category,
            calibration_request=calibration,
        )

        logger.info(
            f"Added calibration data for {project_category.value}: "
            f"project {calibration.project_id}"
        )

        return metrics

    except ValueError as e:
        logger.error(f"Validation error during calibration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during calibration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during calibration",
        )


@router.get("/metrics/{project_category}", response_model=AccuracyMetricsResponse)
async def get_accuracy_metrics(
    project_category: ProjectCategory,
) -> AccuracyMetricsResponse:
    """Get current accuracy metrics for an estimation model.

    Retrieves statistical accuracy metrics (MAE, MSE, R², within-25%)
    for the specified project category's estimation model.

    Args:
        project_category: Category of the estimation model

    Returns:
        Current accuracy metrics

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        service = get_estimation_service()
        metrics = service.get_accuracy_metrics(project_category)

        return metrics

    except ValueError as e:
        logger.error(f"Invalid project category: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving metrics",
        )


@router.get("/statistics/{project_category}", response_model=CalibrationStatsResponse)
async def get_calibration_statistics(
    project_category: ProjectCategory,
) -> CalibrationStatsResponse:
    """Get comprehensive calibration statistics.

    Provides detailed statistics about calibration data including
    variance analysis, bias detection, and accuracy breakdowns.

    Args:
        project_category: Category of the estimation model

    Returns:
        Comprehensive calibration statistics

    Raises:
        HTTPException: If retrieval fails
    """
    try:
        service = get_estimation_service()
        calibration_service = CalibrationService()

        # Get the model
        model = service._models.get(project_category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project_category}")

        # Get statistics
        statistics = calibration_service.get_calibration_statistics(model)

        return CalibrationStatsResponse(
            model_id=model.id,
            model_name=model.name,
            statistics=statistics,
        )

    except ValueError as e:
        logger.error(f"Invalid project category: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving statistics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error retrieving statistics",
        )


@router.get("/recommendation/{project_category}", response_model=RecalibrationRecommendationResponse)
async def get_recalibration_recommendation(
    project_category: ProjectCategory,
    min_accuracy: float = 70.0,
) -> RecalibrationRecommendationResponse:
    """Get recommendation for model recalibration.

    Analyzes model performance and recommends whether recalibration
    is needed to maintain accuracy targets.

    Args:
        project_category: Category of the estimation model
        min_accuracy: Minimum acceptable accuracy percentage (default: 70%)

    Returns:
        Recalibration recommendation with reasons and priority

    Raises:
        HTTPException: If analysis fails
    """
    try:
        service = get_estimation_service()
        calibration_service = CalibrationService()

        # Get the model
        model = service._models.get(project_category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project_category}")

        # Get recommendation
        recommendation = calibration_service.recommend_recalibration(
            model=model,
            min_accuracy=min_accuracy,
        )

        return RecalibrationRecommendationResponse(
            model_id=model.id,
            model_name=model.name,
            needs_recalibration=recommendation["needs_recalibration"],
            reasons=recommendation["reasons"],
            priority=recommendation["priority"],
        )

    except ValueError as e:
        logger.error(f"Invalid project category: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error getting recommendation: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error getting recommendation",
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Perform health check on estimation service.

    Returns service status and metrics for all estimation models.

    Returns:
        Health status with model information
    """
    try:
        service = get_estimation_service()
        health = service.health_check()

        return health

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post("/calibrate/{project_category}")
async def calibrate_model(
    project_category: ProjectCategory,
    target_variance: float = 25.0,
) -> Dict[str, Any]:
    """Calibrate estimation model with historical data.

    Adjusts COCOMO parameters based on historical calibration data
    to improve accuracy and reduce systematic bias.

    Args:
        project_category: Category of the estimation model
        target_variance: Target variance percentage (default: 25%)

    Returns:
        Calibration results with before/after metrics

    Raises:
        HTTPException: If calibration fails
    """
    try:
        service = get_estimation_service()
        calibration_service = CalibrationService()

        # Get the model
        model = service._models.get(project_category)
        if not model:
            raise ValueError(f"No estimation model found for category: {project_category}")

        # Store current metrics for comparison
        before_metrics = model.accuracy_metrics

        # Calibrate
        calibrated_params, after_metrics = calibration_service.calibrate_model(
            model=model,
            target_variance=target_variance,
        )

        # Update model (in production, this would be persisted to database)
        model.cocomo_parameters = calibrated_params
        model.update_accuracy_metrics(after_metrics)

        logger.info(
            f"Calibrated model for {project_category.value}: "
            f"within_25% improved from {before_metrics.within_25_percent:.1f}% "
            f"to {after_metrics.within_25_percent:.1f}%"
        )

        return {
            "model_id": str(model.id),
            "model_name": model.name,
            "before": {
                "within_25_percent": before_metrics.within_25_percent,
                "r_squared": before_metrics.r_squared,
                "mae": before_metrics.mean_absolute_error,
            },
            "after": {
                "within_25_percent": after_metrics.within_25_percent,
                "r_squared": after_metrics.r_squared,
                "mae": after_metrics.mean_absolute_error,
            },
            "improvement": {
                "within_25_percent_delta": after_metrics.within_25_percent - before_metrics.within_25_percent,
                "r_squared_delta": after_metrics.r_squared - before_metrics.r_squared,
            },
        }

    except ValueError as e:
        logger.error(f"Validation error during calibration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during calibration: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during calibration",
        )
