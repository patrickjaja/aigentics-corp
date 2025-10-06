# Estimation Service

COCOMO II-based project effort estimation with historical data calibration.

## Overview

The Estimation Service provides project effort estimation using the Intermediate COCOMO II (Constructive Cost Model) model. It includes:

- **COCOMO II Estimation**: Industry-standard effort estimation model
- **Historical Calibration**: Continuous learning from completed projects
- **Accuracy Metrics**: MAE, MSE, R-squared, and ±25% variance tracking
- **Category-Specific Models**: Separate models for different project types
- **REST API**: FastAPI endpoints for estimation and calibration

## Features

### 1. Project Estimation

Estimates project effort in hours based on:
- Project requirements (functional and non-functional)
- Project size (KLOC - thousands of lines of code)
- Complexity factors (team experience, technology familiarity, etc.)
- COCOMO scale factors and cost drivers

Returns:
- Estimated hours (likely case)
- Optimistic hours (best case)
- Pessimistic hours (worst case)
- Confidence score (0-1)

### 2. Historical Calibration

Improves estimation accuracy by learning from completed projects:
- Stores estimated vs actual hours
- Calculates variance and identifies patterns
- Adjusts COCOMO parameters to reduce systematic bias
- Maintains ±25% variance target

### 3. Accuracy Metrics

Tracks model performance:
- **MAE** (Mean Absolute Error): Average absolute difference
- **MSE** (Mean Squared Error): Penalizes larger errors
- **R²** (R-squared): Coefficient of determination (0-1)
- **Within 25%**: Percentage of estimates within ±25% of actual

### 4. Continuous Learning

- Adds calibration points from completed projects
- Analyzes variance patterns and factor correlations
- Recommends recalibration when accuracy drops
- Automatically adjusts parameters to improve accuracy

## COCOMO II Model

### Formula

```
Effort (PM) = A × Size^B × EAF
Effort (hours) = Effort (PM) × 152 hours/month
```

Where:
- **A**: Base constant (2.94 for COCOMO II)
- **Size**: Project size in KLOC (thousands of lines of code)
- **B**: Scale exponent = 0.91 + 0.01 × Σ(scale factors)
- **EAF**: Effort Adjustment Factor = Π(cost drivers)

### Scale Factors

Five scale factors affecting project complexity:
1. **Precedentedness** (3.72): Thoroughness of analysis and design
2. **Development Flexibility** (2.03): Conformance to requirements
3. **Architecture Risk Resolution** (4.24): Risk analysis thoroughness
4. **Team Cohesion** (3.29): Cooperation of stakeholders
5. **Process Maturity** (4.68): Process maturity level (CMMI)

### Cost Drivers

17 cost drivers in four categories:

**Product Factors:**
- Product complexity
- Required reusability
- Documentation match to lifecycle needs

**Platform Factors:**
- Platform difficulty
- Execution time constraint
- Main storage constraint

**Personnel Factors:**
- Analyst capability (0.85 nominal)
- Programmer capability (0.88 nominal)
- Personnel continuity
- Application experience (0.91 nominal)
- Platform experience
- Language and tool experience (0.95 nominal)

**Project Factors:**
- Time constraint
- Tool use (0.90 nominal)
- Multisite development
- Required development schedule

## API Endpoints

### POST /estimation/estimate

Estimate project effort.

**Request:**
```json
{
  "project": {
    "id": "uuid",
    "name": "E-Commerce Platform",
    "category": "software_development",
    "requirements": [...],
    "constraints": {...}
  },
  "size_kloc": 5.0,
  "complexity_factors": {
    "team_experience": "high",
    "technology_familiarity": "medium"
  },
  "adjustment_factor": 1.0
}
```

**Response:**
```json
{
  "estimate_id": "uuid",
  "project_id": "uuid",
  "estimated_hours": 760.5,
  "optimistic_hours": 570.4,
  "likely_hours": 760.5,
  "pessimistic_hours": 1140.8,
  "confidence": 0.87,
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "factors_applied": {
    "scale_exponent": 1.09,
    "effort_adjustment_factor": 0.92
  },
  "created_at": "2025-10-06T12:00:00Z"
}
```

### POST /estimation/calibration/{project_category}

Add calibration data from a completed project.

**Request:**
```json
{
  "project_id": "uuid",
  "estimated_hours": 760.5,
  "actual_hours": 725.0,
  "factors": {
    "team_experience": "high",
    "requirements_stability": "stable",
    "scope_changes": 2
  }
}
```

**Response:**
```json
{
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "mean_absolute_error": 42.5,
  "mean_squared_error": 2156.25,
  "r_squared": 0.87,
  "within_25_percent": 78.5,
  "calibration_count": 15,
  "last_updated": "2025-10-06T12:00:00Z"
}
```

### GET /estimation/metrics/{project_category}

Get accuracy metrics for an estimation model.

**Response:**
```json
{
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "mean_absolute_error": 42.5,
  "mean_squared_error": 2156.25,
  "r_squared": 0.87,
  "within_25_percent": 78.5,
  "calibration_count": 15,
  "last_updated": "2025-10-06T12:00:00Z"
}
```

### GET /estimation/statistics/{project_category}

Get comprehensive calibration statistics.

**Response:**
```json
{
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "statistics": {
    "total_points": 15,
    "variance": {
      "mean": -2.5,
      "median": -1.8,
      "std_dev": 12.3,
      "min": -15.2,
      "max": 18.7
    },
    "estimation": {
      "mean_estimated": 650.0,
      "mean_actual": 640.0,
      "total_estimated": 9750.0,
      "total_actual": 9600.0
    },
    "accuracy": {
      "within_10_percent": 45.2,
      "within_25_percent": 78.5,
      "within_50_percent": 95.3
    },
    "bias": {
      "overestimation_rate": 60.0,
      "underestimation_rate": 40.0,
      "systematic_bias": -2.5
    }
  }
}
```

### GET /estimation/recommendation/{project_category}

Get recalibration recommendation.

**Response:**
```json
{
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "needs_recalibration": false,
  "reasons": [
    "Model performing within acceptable parameters"
  ],
  "priority": "low"
}
```

### POST /estimation/calibrate/{project_category}

Calibrate model with historical data.

**Response:**
```json
{
  "model_id": "uuid",
  "model_name": "Software Development Estimation Model",
  "before": {
    "within_25_percent": 72.5,
    "r_squared": 0.82,
    "mae": 48.3
  },
  "after": {
    "within_25_percent": 78.5,
    "r_squared": 0.87,
    "mae": 42.5
  },
  "improvement": {
    "within_25_percent_delta": 6.0,
    "r_squared_delta": 0.05
  }
}
```

### GET /estimation/health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "models": {
    "software_development": {
      "name": "Software Development Estimation Model",
      "calibration_points": 15,
      "accuracy": 78.5,
      "needs_recalibration": false,
      "last_updated": "2025-10-06T12:00:00Z"
    },
    "consulting": {...},
    "infrastructure": {...},
    "mixed": {...}
  },
  "timestamp": "2025-10-06T12:00:00Z"
}
```

## Usage Examples

### Basic Estimation

```python
from services.estimation import get_estimation_service
from models.project import Project, ProjectCategory

# Get service
service = get_estimation_service()

# Estimate project
estimate = service.estimate_project(
    project=my_project,
    size_kloc=5.0,
    complexity_factors={
        "team_experience": "high",
        "technology_familiarity": "medium",
    },
    adjustment_factor=1.0,
)

print(f"Estimated hours: {estimate.estimated_hours}")
print(f"Confidence: {estimate.confidence}")
```

### Adding Calibration Data

```python
from services.estimation import get_estimation_service, CalibrationRequest

service = get_estimation_service()

# Add completed project data
calibration = CalibrationRequest(
    project_id=completed_project_id,
    estimated_hours=760.5,
    actual_hours=725.0,
    factors={
        "team_experience": "high",
        "requirements_stability": "stable",
    },
)

metrics = service.add_calibration_point(
    project_category=ProjectCategory.SOFTWARE_DEVELOPMENT,
    calibration_request=calibration,
)

print(f"Updated accuracy: {metrics.within_25_percent}%")
```

### Checking Model Accuracy

```python
from services.estimation import get_estimation_service
from models.project import ProjectCategory

service = get_estimation_service()

metrics = service.get_accuracy_metrics(
    ProjectCategory.SOFTWARE_DEVELOPMENT
)

print(f"MAE: {metrics.mean_absolute_error}")
print(f"R²: {metrics.r_squared}")
print(f"Within ±25%: {metrics.within_25_percent}%")
```

## Accuracy Targets

The service aims to maintain:
- **±25% variance**: 70%+ of estimates within ±25% of actual
- **R² ≥ 0.75**: Good statistical fit
- **Systematic bias < 15%**: Minimal over/underestimation tendency

When accuracy falls below targets, the service recommends recalibration.

## Project Categories

Separate models for each category:
- **software_development**: Web apps, mobile apps, software products
- **consulting**: IT consulting, advisory services
- **infrastructure**: Cloud setup, network configuration, DevOps
- **mixed**: Projects combining multiple categories

## Size Estimation

If project size (KLOC) is not provided, it's estimated from requirements:

| Category | Base KLOC/Requirement |
|----------|----------------------|
| Software Development | 0.8 KLOC |
| IT Consulting | 0.3 KLOC |
| Infrastructure | 0.5 KLOC |
| Mixed | 0.6 KLOC |

Adjustments:
- Functional requirements: 1.0x weight
- Non-functional requirements: 0.5x weight
- High-priority requirements: +20% complexity multiplier

## Dependencies

- **numpy**: Statistical calculations
- **scipy**: Advanced statistics and correlation analysis
- **pydantic**: Data validation
- **fastapi**: REST API endpoints

## Testing

```bash
# Run tests
pytest backend/tests/unit/test_estimation.py
pytest backend/tests/integration/test_estimation_service.py

# Check calibration accuracy
pytest backend/tests/unit/test_calibration.py -v
```

## Continuous Improvement

The estimation service learns from every completed project:

1. **Capture actual hours** when project completes
2. **Calculate variance** vs. original estimate
3. **Analyze factors** that influenced variance
4. **Adjust parameters** to reduce systematic bias
5. **Validate improvement** with accuracy metrics

This creates a continuous feedback loop that improves accuracy over time.

## References

- COCOMO II Model: [cocomo.org](http://cocomo.org)
- "Software Cost Estimation with COCOMO II" by Barry Boehm
- Intermediate COCOMO II specifications
