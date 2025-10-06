"""Estimation service module.

Provides COCOMO II-based project effort estimation with historical data calibration.
"""

from .calibration import CalibrationService
from .main import (
    EstimationService,
    EstimateRequest,
    EstimateResponse,
    CalibrationRequest,
    AccuracyMetricsResponse,
    get_estimation_service,
)

__all__ = [
    "EstimationService",
    "CalibrationService",
    "EstimateRequest",
    "EstimateResponse",
    "CalibrationRequest",
    "AccuracyMetricsResponse",
    "get_estimation_service",
]
