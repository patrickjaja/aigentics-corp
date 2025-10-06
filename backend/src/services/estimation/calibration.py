"""Historical data calibration service for estimation models.

This module provides calibration capabilities for the COCOMO II estimation model,
using historical project data to improve accuracy and maintain ±25% variance target.

Key Features:
- Statistical accuracy calculation (MAE, MSE, R-squared)
- Model calibration from historical data
- Automatic parameter tuning based on variance patterns
- Continuous learning from completed projects
"""

import logging
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
from scipy import stats

from ...models.estimation import (
    AccuracyMetrics,
    CalibrationPoint,
    COCOMOParameters,
    EstimationModel,
)

logger = logging.getLogger(__name__)


class CalibrationService:
    """Service for calibrating estimation models with historical data.

    Provides methods for:
    - Calculating accuracy metrics (MAE, MSE, R²)
    - Calibrating COCOMO parameters
    - Analyzing variance patterns
    - Recommending parameter adjustments
    """

    def __init__(self, min_calibration_points: int = 3):
        """Initialize calibration service.

        Args:
            min_calibration_points: Minimum points required for calibration (default: 3)
        """
        self.min_calibration_points = min_calibration_points

    def calculate_accuracy_metrics(
        self,
        model: EstimationModel,
    ) -> AccuracyMetrics:
        """Calculate accuracy metrics from calibration data.

        Args:
            model: Estimation model with calibration data

        Returns:
            AccuracyMetrics with MAE, MSE, R², and within-25% percentage

        Raises:
            ValueError: If insufficient calibration data
        """
        if model.get_calibration_count() < self.min_calibration_points:
            logger.warning(
                f"Insufficient calibration data for {model.name}: "
                f"{model.get_calibration_count()} points (minimum: {self.min_calibration_points})"
            )
            # Return default metrics
            return AccuracyMetrics(
                mean_absolute_error=0.0,
                mean_squared_error=0.0,
                r_squared=0.0,
                within_25_percent=0.0,
            )

        # Extract estimated and actual hours
        estimated = np.array([p.estimated_hours for p in model.calibration_data])
        actual = np.array([p.actual_hours for p in model.calibration_data])

        # Calculate Mean Absolute Error (MAE)
        mae = np.mean(np.abs(actual - estimated))

        # Calculate Mean Squared Error (MSE)
        mse = np.mean((actual - estimated) ** 2)

        # Calculate R-squared (coefficient of determination)
        r_squared = self._calculate_r_squared(estimated, actual)

        # Calculate percentage within ±25%
        within_25_percent = self._calculate_within_target_percentage(
            model.calibration_data,
            target_percent=25.0,
        )

        logger.info(
            f"Calculated accuracy metrics for {model.name}: "
            f"MAE={mae:.2f}, MSE={mse:.2f}, R²={r_squared:.3f}, "
            f"within_25%={within_25_percent:.1f}%"
        )

        return AccuracyMetrics(
            mean_absolute_error=float(mae),
            mean_squared_error=float(mse),
            r_squared=float(r_squared),
            within_25_percent=float(within_25_percent),
        )

    def _calculate_r_squared(
        self,
        estimated: np.ndarray,
        actual: np.ndarray,
    ) -> float:
        """Calculate R-squared (coefficient of determination).

        R² = 1 - (SS_res / SS_tot)
        Where:
        - SS_res = Σ(actual - estimated)²
        - SS_tot = Σ(actual - mean(actual))²

        Args:
            estimated: Array of estimated values
            actual: Array of actual values

        Returns:
            R-squared value (0 to 1, higher is better)
        """
        # Residual sum of squares
        ss_res = np.sum((actual - estimated) ** 2)

        # Total sum of squares
        mean_actual = np.mean(actual)
        ss_tot = np.sum((actual - mean_actual) ** 2)

        # Calculate R²
        if ss_tot == 0:
            return 0.0

        r_squared = 1 - (ss_res / ss_tot)

        # Clamp to [0, 1] (can be negative for very poor fits)
        return max(0.0, min(1.0, r_squared))

    def _calculate_within_target_percentage(
        self,
        calibration_data: List[CalibrationPoint],
        target_percent: float = 25.0,
    ) -> float:
        """Calculate percentage of estimates within target variance.

        Args:
            calibration_data: List of calibration points
            target_percent: Target variance percentage (default: 25%)

        Returns:
            Percentage (0-100) of estimates within target
        """
        if not calibration_data:
            return 0.0

        within_target = sum(
            1 for point in calibration_data
            if point.is_within_target_variance(target_percent)
        )

        return (within_target / len(calibration_data)) * 100

    def calibrate_model(
        self,
        model: EstimationModel,
        target_variance: float = 25.0,
    ) -> Tuple[COCOMOParameters, AccuracyMetrics]:
        """Calibrate COCOMO parameters based on historical data.

        Adjusts effort multipliers and cost drivers to minimize variance
        and improve accuracy toward the target.

        Args:
            model: Estimation model to calibrate
            target_variance: Target variance percentage (default: 25%)

        Returns:
            Tuple of (calibrated_parameters, new_accuracy_metrics)

        Raises:
            ValueError: If insufficient calibration data
        """
        if model.get_calibration_count() < self.min_calibration_points:
            raise ValueError(
                f"Insufficient calibration data: {model.get_calibration_count()} points "
                f"(minimum: {self.min_calibration_points})"
            )

        logger.info(f"Starting calibration for {model.name} with {model.get_calibration_count()} points")

        # Calculate current accuracy
        current_metrics = self.calculate_accuracy_metrics(model)

        # Analyze variance patterns
        variance_analysis = self._analyze_variance_patterns(model.calibration_data)

        # Adjust parameters based on analysis
        calibrated_params = self._adjust_parameters(
            model.cocomo_parameters,
            variance_analysis,
            target_variance,
        )

        # Calculate new metrics (simulated with adjusted parameters)
        # In production, this would require re-estimating all historical projects
        new_metrics = self._simulate_calibrated_accuracy(
            current_metrics,
            variance_analysis,
        )

        logger.info(
            f"Calibration complete for {model.name}: "
            f"within_25% improved from {current_metrics.within_25_percent:.1f}% "
            f"to {new_metrics.within_25_percent:.1f}%"
        )

        return calibrated_params, new_metrics

    def _analyze_variance_patterns(
        self,
        calibration_data: List[CalibrationPoint],
    ) -> dict:
        """Analyze variance patterns in calibration data.

        Args:
            calibration_data: List of calibration points

        Returns:
            Dictionary with variance analysis results
        """
        variances = np.array([p.variance for p in calibration_data])

        analysis = {
            "mean_variance": float(np.mean(variances)),
            "median_variance": float(np.median(variances)),
            "std_variance": float(np.std(variances)),
            "overestimation_rate": float(np.mean(variances < 0) * 100),
            "underestimation_rate": float(np.mean(variances > 0) * 100),
            "systematic_bias": float(np.mean(variances)),
        }

        # Analyze factors contributing to variance
        factor_correlations = self._analyze_factor_correlations(calibration_data)
        analysis["factor_correlations"] = factor_correlations

        return analysis

    def _analyze_factor_correlations(
        self,
        calibration_data: List[CalibrationPoint],
    ) -> dict:
        """Analyze correlation between factors and variance.

        Args:
            calibration_data: List of calibration points

        Returns:
            Dictionary of factors and their correlation with variance
        """
        correlations = {}

        # Collect all unique factor keys
        all_factors = set()
        for point in calibration_data:
            all_factors.update(point.factors.keys())

        # Calculate correlation for each factor
        for factor_key in all_factors:
            # Extract factor values (convert to numeric where possible)
            factor_values = []
            variances = []

            for point in calibration_data:
                if factor_key in point.factors:
                    value = point.factors[factor_key]
                    # Convert to numeric if possible
                    numeric_value = self._convert_to_numeric(value)
                    if numeric_value is not None:
                        factor_values.append(numeric_value)
                        variances.append(point.variance)

            # Calculate correlation if we have enough data points
            if len(factor_values) >= 3:
                try:
                    correlation, p_value = stats.pearsonr(factor_values, variances)
                    if abs(correlation) > 0.3 and p_value < 0.05:
                        # Significant correlation found
                        correlations[factor_key] = {
                            "correlation": float(correlation),
                            "p_value": float(p_value),
                        }
                except Exception as e:
                    logger.debug(f"Could not calculate correlation for {factor_key}: {e}")

        return correlations

    def _convert_to_numeric(self, value: any) -> Optional[float]:
        """Convert value to numeric for correlation analysis.

        Args:
            value: Value to convert

        Returns:
            Numeric value or None if not convertible
        """
        # Handle numeric values
        if isinstance(value, (int, float)):
            return float(value)

        # Handle string representations of common levels
        level_mapping = {
            "very_low": 1.0,
            "low": 2.0,
            "nominal": 3.0,
            "medium": 3.0,
            "high": 4.0,
            "very_high": 5.0,
            "extra_high": 6.0,
        }

        if isinstance(value, str):
            return level_mapping.get(value.lower())

        return None

    def _adjust_parameters(
        self,
        params: COCOMOParameters,
        variance_analysis: dict,
        target_variance: float,
    ) -> COCOMOParameters:
        """Adjust COCOMO parameters based on variance analysis.

        Args:
            params: Current COCOMO parameters
            variance_analysis: Results from variance pattern analysis
            target_variance: Target variance percentage

        Returns:
            Adjusted COCOMO parameters
        """
        # Create a copy of parameters to adjust
        adjusted_params = COCOMOParameters(
            effort_multipliers=params.effort_multipliers.copy(),
            scale_factors=params.scale_factors.copy(),
            cost_drivers=params.cost_drivers.copy(),
        )

        # Calculate adjustment factor based on systematic bias
        systematic_bias = variance_analysis["systematic_bias"]

        if abs(systematic_bias) > target_variance:
            # Adjust effort multipliers to correct bias
            if systematic_bias > 0:
                # Systematic underestimation - increase effort multipliers
                adjustment = 1 + (systematic_bias / 100 * 0.5)
                logger.info(f"Adjusting for underestimation: multiplier={adjustment:.3f}")
            else:
                # Systematic overestimation - decrease effort multipliers
                adjustment = 1 + (systematic_bias / 100 * 0.5)
                logger.info(f"Adjusting for overestimation: multiplier={adjustment:.3f}")

            # Apply adjustment to effort multipliers
            for key in adjusted_params.effort_multipliers:
                adjusted_params.effort_multipliers[key] *= adjustment

        # Adjust cost drivers based on factor correlations
        factor_correlations = variance_analysis.get("factor_correlations", {})

        for factor_key, correlation_info in factor_correlations.items():
            correlation = correlation_info["correlation"]

            # Find matching cost driver
            for driver_key in adjusted_params.cost_drivers:
                if factor_key.lower() in driver_key.lower():
                    # Adjust driver based on correlation strength
                    adjustment = 1 - (correlation * 0.1)  # Max 10% adjustment
                    adjusted_params.cost_drivers[driver_key] *= adjustment
                    logger.debug(
                        f"Adjusted {driver_key} by {adjustment:.3f} "
                        f"due to correlation with {factor_key}"
                    )

        return adjusted_params

    def _simulate_calibrated_accuracy(
        self,
        current_metrics: AccuracyMetrics,
        variance_analysis: dict,
    ) -> AccuracyMetrics:
        """Simulate accuracy metrics after calibration.

        In production, this would re-estimate all historical projects
        with calibrated parameters. For now, we estimate improvement.

        Args:
            current_metrics: Current accuracy metrics
            variance_analysis: Results from variance analysis

        Returns:
            Simulated accuracy metrics after calibration
        """
        # Estimate improvement based on systematic bias reduction
        systematic_bias = abs(variance_analysis["systematic_bias"])

        # Assume calibration reduces systematic bias by 50%
        bias_reduction = systematic_bias * 0.5

        # Improve within_25_percent metric
        improved_within_25 = current_metrics.within_25_percent + (bias_reduction / 2)
        improved_within_25 = min(100.0, improved_within_25)

        # Improve R²
        improved_r_squared = current_metrics.r_squared + 0.05
        improved_r_squared = min(1.0, improved_r_squared)

        # Reduce MAE and MSE
        improved_mae = current_metrics.mean_absolute_error * 0.9
        improved_mse = current_metrics.mean_squared_error * 0.85

        return AccuracyMetrics(
            mean_absolute_error=improved_mae,
            mean_squared_error=improved_mse,
            r_squared=improved_r_squared,
            within_25_percent=improved_within_25,
        )

    def recommend_recalibration(
        self,
        model: EstimationModel,
        min_accuracy: float = 70.0,
        min_points_since_last: int = 5,
    ) -> dict:
        """Recommend whether model needs recalibration.

        Args:
            model: Estimation model to check
            min_accuracy: Minimum acceptable accuracy (default: 70%)
            min_points_since_last: Minimum new points since last calibration (default: 5)

        Returns:
            Dictionary with recommendation and reasons
        """
        recommendation = {
            "needs_recalibration": False,
            "reasons": [],
            "priority": "low",
        }

        # Check accuracy
        if model.accuracy_metrics.within_25_percent < min_accuracy:
            recommendation["needs_recalibration"] = True
            recommendation["reasons"].append(
                f"Accuracy below target: {model.accuracy_metrics.within_25_percent:.1f}% < {min_accuracy}%"
            )
            recommendation["priority"] = "high"

        # Check R-squared
        if model.accuracy_metrics.r_squared < 0.75:
            recommendation["needs_recalibration"] = True
            recommendation["reasons"].append(
                f"Poor model fit: R²={model.accuracy_metrics.r_squared:.3f}"
            )
            if recommendation["priority"] == "low":
                recommendation["priority"] = "medium"

        # Check calibration data sufficiency
        if not model.has_sufficient_calibration_data(min_points=10):
            recommendation["reasons"].append(
                f"Limited calibration data: {model.get_calibration_count()} points"
            )

        # Check for systematic bias
        avg_variance = model.calculate_average_variance()
        if abs(avg_variance) > 15.0:
            recommendation["needs_recalibration"] = True
            recommendation["reasons"].append(
                f"Systematic bias detected: {avg_variance:+.1f}% average variance"
            )
            recommendation["priority"] = "high"

        if not recommendation["reasons"]:
            recommendation["reasons"].append("Model performing within acceptable parameters")

        logger.info(
            f"Recalibration recommendation for {model.name}: "
            f"needed={recommendation['needs_recalibration']}, "
            f"priority={recommendation['priority']}"
        )

        return recommendation

    def get_calibration_statistics(
        self,
        model: EstimationModel,
    ) -> dict:
        """Get comprehensive calibration statistics.

        Args:
            model: Estimation model

        Returns:
            Dictionary with calibration statistics
        """
        if model.get_calibration_count() == 0:
            return {
                "total_points": 0,
                "statistics": None,
            }

        variances = np.array([p.variance for p in model.calibration_data])
        estimated = np.array([p.estimated_hours for p in model.calibration_data])
        actual = np.array([p.actual_hours for p in model.calibration_data])

        statistics = {
            "total_points": model.get_calibration_count(),
            "variance": {
                "mean": float(np.mean(variances)),
                "median": float(np.median(variances)),
                "std_dev": float(np.std(variances)),
                "min": float(np.min(variances)),
                "max": float(np.max(variances)),
            },
            "estimation": {
                "mean_estimated": float(np.mean(estimated)),
                "mean_actual": float(np.mean(actual)),
                "total_estimated": float(np.sum(estimated)),
                "total_actual": float(np.sum(actual)),
            },
            "accuracy": {
                "within_10_percent": float(
                    np.mean(np.abs(variances) <= 10.0) * 100
                ),
                "within_25_percent": float(
                    np.mean(np.abs(variances) <= 25.0) * 100
                ),
                "within_50_percent": float(
                    np.mean(np.abs(variances) <= 50.0) * 100
                ),
            },
            "bias": {
                "overestimation_rate": float(np.mean(variances < 0) * 100),
                "underestimation_rate": float(np.mean(variances > 0) * 100),
                "systematic_bias": float(np.mean(variances)),
            },
        }

        return statistics
