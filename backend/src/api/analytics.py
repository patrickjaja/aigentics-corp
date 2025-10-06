"""
Analytics API Endpoints (T094)

Provides analytics data for offers, conversions, and performance metrics.
Admin-only endpoints for business intelligence and reporting.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Depends, Query, status
from pydantic import BaseModel, Field

from ..models.analytics import (
    AnalyticsDashboard,
    AnalyticsQuery,
    ConversionFunnelMetrics,
    OfferMetrics,
    TimeGranularity,
    TimeSeries
)
from ..services.analytics.main import AnalyticsService, get_analytics_service
from ..infrastructure.middleware.auth import verify_admin_api_key


router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    dependencies=[Depends(verify_admin_api_key)]
)


# Request/Response Models
class AnalyticsQueryRequest(BaseModel):
    """Query parameters for analytics"""
    start_date: date = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="End date (YYYY-MM-DD)")
    granularity: TimeGranularity = Field(
        default=TimeGranularity.DAY,
        description="Time aggregation (hour/day/week/month)"
    )


class ErrorResponse(BaseModel):
    """Standard error response"""
    error_code: str
    message: str
    details: Optional[dict] = None


# API Endpoints

@router.get(
    "/dashboard",
    response_model=AnalyticsDashboard,
    responses={
        200: {"description": "Complete analytics dashboard"},
        400: {"model": ErrorResponse, "description": "Invalid date range"},
        401: {"model": ErrorResponse, "description": "Unauthorized - admin key required"}
    }
)
async def get_analytics_dashboard(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: TimeGranularity = Query(
        default=TimeGranularity.DAY,
        description="Time granularity"
    ),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    service: AnalyticsService = Depends(get_analytics_service)
) -> AnalyticsDashboard:
    """
    Get complete analytics dashboard.

    Returns all metrics for the specified time period:
    - Conversion funnel
    - Offer metrics
    - Performance metrics
    - Customer analytics
    - Approval metrics
    - Time series data

    **Admin only**
    """
    try:
        query = AnalyticsQuery(
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        query.validate_date_range()

        dashboard = await service.get_dashboard_data(query)
        return dashboard

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_DATE_RANGE",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="ANALYTICS_ERROR",
                message="Failed to generate analytics",
                details={"error": str(e)}
            ).model_dump()
        )


@router.get(
    "/offers",
    response_model=OfferMetrics,
    responses={
        200: {"description": "Offer generation metrics"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_offer_metrics(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    service: AnalyticsService = Depends(get_analytics_service)
) -> OfferMetrics:
    """
    Get offer generation metrics.

    Provides:
    - Total offers generated
    - Acceptance/rejection rates
    - Average offer value
    - Generation time statistics
    - Approval workflow metrics

    **Admin only**

    **Example**:
    ```
    GET /analytics/offers?start_date=2025-10-01&end_date=2025-10-31
    ```
    """
    try:
        metrics = await service.get_offer_metrics(start_date, end_date)
        return metrics

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_DATE_RANGE",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="METRICS_ERROR",
                message="Failed to calculate offer metrics",
                details={"error": str(e)}
            ).model_dump()
        )


@router.get(
    "/conversion",
    response_model=ConversionFunnelMetrics,
    responses={
        200: {"description": "Conversion funnel metrics"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_conversion_funnel(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    service: AnalyticsService = Depends(get_analytics_service)
) -> ConversionFunnelMetrics:
    """
    Get conversion funnel metrics.

    Tracks customer journey:
    1. Conversations started
    2. Conversations completed
    3. Offers generated
    4. Offers sent
    5. Offers viewed
    6. Offers accepted

    Includes conversion rates between each stage.

    **Admin only**

    **Example**:
    ```
    GET /analytics/conversion?start_date=2025-10-01&end_date=2025-10-31
    ```
    """
    try:
        funnel = await service.get_conversion_funnel(start_date, end_date)
        return funnel

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_DATE_RANGE",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="FUNNEL_ERROR",
                message="Failed to calculate conversion funnel",
                details={"error": str(e)}
            ).model_dump()
        )


@router.get(
    "/time-series/{metric_name}",
    response_model=TimeSeries,
    responses={
        200: {"description": "Time series data"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_time_series(
    metric_name: str,
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    granularity: TimeGranularity = Query(
        default=TimeGranularity.DAY,
        description="Time granularity (hour/day/week/month)"
    ),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    service: AnalyticsService = Depends(get_analytics_service)
) -> TimeSeries:
    """
    Get time series data for a metric.

    Available metrics:
    - `offers_generated` - Offers generated over time
    - `offers_accepted` - Offers accepted over time
    - `conversations_started` - Conversations started over time
    - `avg_offer_value` - Average offer value over time

    Used for charting trends.

    **Admin only**

    **Example**:
    ```
    GET /analytics/time-series/offers_generated?start_date=2025-10-01&end_date=2025-10-31&granularity=day
    ```
    """
    try:
        time_series = await service.get_time_series(
            metric_name=metric_name,
            start_date=start_date,
            end_date=end_date,
            granularity=granularity
        )
        return time_series

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error_code="INVALID_REQUEST",
                message=str(e)
            ).model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="TIME_SERIES_ERROR",
                message="Failed to generate time series",
                details={"error": str(e)}
            ).model_dump()
        )


# Export metrics (CSV/JSON)
@router.get(
    "/export",
    responses={
        200: {"description": "Exported analytics data (CSV or JSON)"},
        400: {"model": ErrorResponse, "description": "Invalid request"},
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def export_analytics(
    start_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query(default="json", description="Export format (json/csv)"),
    x_admin_key: str = Header(..., alias="X-Admin-Key"),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Export analytics data.

    Formats:
    - `json` - JSON format for API consumption
    - `csv` - CSV format for Excel

    **Admin only**
    """
    try:
        query = AnalyticsQuery(
            start_date=start_date,
            end_date=end_date
        )
        dashboard = await service.get_dashboard_data(query)

        if format == "csv":
            # Convert to CSV (simplified)
            csv_content = "metric,value\n"
            csv_content += f"total_offers,{dashboard.offer_metrics.total_offers}\n"
            csv_content += f"total_accepted,{dashboard.offer_metrics.total_accepted}\n"
            csv_content += f"acceptance_rate,{dashboard.conversion_funnel.acceptance_rate}\n"
            csv_content += f"avg_value,{dashboard.offer_metrics.avg_value}\n"

            from fastapi.responses import Response
            return Response(
                content=csv_content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=analytics-{start_date}-{end_date}.csv"
                }
            )
        else:
            # Return JSON
            return dashboard.model_dump()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error_code="EXPORT_ERROR",
                message="Failed to export analytics",
                details={"error": str(e)}
            ).model_dump()
        )
