"""
Analytics data models for metrics and reporting (T092)

Tracks offer generation metrics, conversion rates, and performance indicators.
Supports time-series aggregation for dashboard visualizations.
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MetricType(Enum):
    """Types of metrics collected"""
    CONVERSATION_STARTED = "conversation_started"
    CONVERSATION_COMPLETED = "conversation_completed"
    OFFER_GENERATED = "offer_generated"
    OFFER_SENT = "offer_sent"
    OFFER_VIEWED = "offer_viewed"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_COMPLETED = "approval_completed"
    API_CALL = "api_call"
    ERROR_OCCURRED = "error_occurred"


class TimeGranularity(Enum):
    """Time aggregation granularity"""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class MetricEvent(BaseModel):
    """
    Individual metric event.

    Each event represents a single occurrence of a tracked action.
    Events are aggregated for time-series analysis.
    """
    id: UUID = Field(default_factory=uuid4)
    metric_type: MetricType
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Context
    customer_id: Optional[UUID] = None
    conversation_id: Optional[UUID] = None
    offer_id: Optional[UUID] = None
    user_id: Optional[UUID] = None

    # Metadata
    value: Optional[Decimal] = None  # For offer values, response times, etc.
    metadata: Dict[str, any] = Field(default_factory=dict)

    # Performance
    duration_ms: Optional[int] = None  # For API calls, generation times
    status: Optional[str] = None  # success, error, timeout

    class Config:
        use_enum_values = True


class ConversionFunnelMetrics(BaseModel):
    """
    Conversion funnel metrics for a time period.

    Tracks the customer journey from conversation to accepted offer.
    """
    period_start: datetime
    period_end: datetime

    # Funnel stages
    conversations_started: int = 0
    conversations_completed: int = 0
    offers_generated: int = 0
    offers_sent: int = 0
    offers_viewed: int = 0
    offers_accepted: int = 0
    offers_rejected: int = 0

    # Conversion rates (calculated)
    completion_rate: float = Field(default=0.0, ge=0.0, le=1.0)  # completed / started
    generation_rate: float = Field(default=0.0, ge=0.0, le=1.0)  # generated / completed
    send_rate: float = Field(default=0.0, ge=0.0, le=1.0)  # sent / generated
    view_rate: float = Field(default=0.0, ge=0.0, le=1.0)  # viewed / sent
    acceptance_rate: float = Field(default=0.0, ge=0.0, le=1.0)  # accepted / sent
    overall_conversion: float = Field(default=0.0, ge=0.0, le=1.0)  # accepted / started

    def calculate_rates(self) -> None:
        """Calculate conversion rates from counts"""
        if self.conversations_started > 0:
            self.completion_rate = self.conversations_completed / self.conversations_started
            self.overall_conversion = self.offers_accepted / self.conversations_started

        if self.conversations_completed > 0:
            self.generation_rate = self.offers_generated / self.conversations_completed

        if self.offers_generated > 0:
            self.send_rate = self.offers_sent / self.offers_generated

        if self.offers_sent > 0:
            self.view_rate = self.offers_viewed / self.offers_sent
            self.acceptance_rate = self.offers_accepted / self.offers_sent


class OfferMetrics(BaseModel):
    """
    Aggregated offer generation metrics.

    Provides insights into offer performance and value.
    """
    period_start: datetime
    period_end: datetime

    # Volume
    total_offers: int = 0
    total_sent: int = 0
    total_accepted: int = 0
    total_rejected: int = 0

    # Value (in EUR)
    total_value: Decimal = Decimal("0.00")
    avg_value: Decimal = Decimal("0.00")
    median_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None
    accepted_value: Decimal = Decimal("0.00")  # Total value of accepted offers

    # Performance
    avg_generation_time_ms: int = 0
    max_generation_time_ms: int = 0
    generation_timeout_count: int = 0  # Offers that took >30s

    # Approval workflow
    approval_required_count: int = 0
    approval_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    avg_approval_time_hours: float = 0.0

    # Time to conversion
    avg_time_to_acceptance_hours: float = 0.0
    median_time_to_acceptance_hours: Optional[float] = None


class TimeSeriesDataPoint(BaseModel):
    """
    Single data point in a time series.

    Used for charting trends over time.
    """
    timestamp: datetime
    value: Decimal
    count: Optional[int] = None
    metadata: Dict[str, any] = Field(default_factory=dict)


class TimeSeries(BaseModel):
    """
    Time series data for visualization.

    Contains multiple data points with configurable granularity.
    """
    metric_name: str
    granularity: TimeGranularity
    period_start: datetime
    period_end: datetime
    data_points: List[TimeSeriesDataPoint] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class PerformanceMetrics(BaseModel):
    """
    System performance metrics.

    Tracks API response times and system health.
    """
    period_start: datetime
    period_end: datetime

    # API performance
    total_api_calls: int = 0
    avg_response_time_ms: int = 0
    p50_response_time_ms: int = 0
    p95_response_time_ms: int = 0
    p99_response_time_ms: int = 0

    # Endpoints
    endpoint_stats: Dict[str, Dict[str, any]] = Field(default_factory=dict)
    # Example: {
    #   "/offers": {
    #     "count": 150,
    #     "avg_time_ms": 18500,
    #     "error_rate": 0.02
    #   }
    # }

    # Errors
    error_count: int = 0
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    errors_by_type: Dict[str, int] = Field(default_factory=dict)

    # SLA compliance
    sla_compliance_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    # Percentage of requests meeting SLA targets:
    # - POST /conversations: <2s
    # - POST /offers: <30s
    # - GET endpoints: <1s


class CustomerAnalytics(BaseModel):
    """
    Customer behavior analytics.

    Provides insights into customer engagement and preferences.
    """
    period_start: datetime
    period_end: datetime

    # Customer segments
    total_customers: int = 0
    new_customers: int = 0
    returning_customers: int = 0

    # Engagement
    avg_conversations_per_customer: float = 0.0
    avg_messages_per_conversation: float = 0.0
    avg_time_to_complete_conversation_minutes: float = 0.0

    # By industry (if available)
    customers_by_industry: Dict[str, int] = Field(default_factory=dict)

    # By project type
    offers_by_category: Dict[str, int] = Field(default_factory=dict)
    # Example: {
    #   "software_development": 45,
    #   "consulting": 20,
    #   "infrastructure": 15
    # }

    # Geography (optional)
    customers_by_country: Dict[str, int] = Field(default_factory=dict)


class ApprovalWorkflowMetrics(BaseModel):
    """
    Approval workflow analytics.

    Tracks approval process efficiency and outcomes.
    """
    period_start: datetime
    period_end: datetime

    # Volume
    total_approvals_requested: int = 0
    total_approved: int = 0
    total_rejected: int = 0
    total_pending: int = 0

    # Rates
    approval_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    rejection_rate: float = Field(default=0.0, ge=0.0, le=1.0)

    # Performance
    avg_approval_time_hours: float = 0.0
    median_approval_time_hours: Optional[float] = None
    max_approval_time_hours: float = 0.0

    # By approver
    approvals_by_user: Dict[str, int] = Field(default_factory=dict)

    # By value threshold
    approvals_by_value_range: Dict[str, int] = Field(default_factory=dict)
    # Example: {
    #   "0-50k": 5,
    #   "50k-100k": 8,
    #   "100k-200k": 12,
    #   "200k+": 3
    # }

    # SLA compliance
    within_sla_count: int = 0  # Approved within target time
    sla_compliance_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class AnalyticsDashboard(BaseModel):
    """
    Complete analytics dashboard data.

    Aggregates all metrics for a comprehensive view.
    """
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    period_start: datetime
    period_end: datetime

    # Core metrics
    conversion_funnel: ConversionFunnelMetrics
    offer_metrics: OfferMetrics
    performance_metrics: PerformanceMetrics
    customer_analytics: CustomerAnalytics
    approval_metrics: ApprovalWorkflowMetrics

    # Time series (for charts)
    time_series: List[TimeSeries] = Field(default_factory=list)

    # Key insights (auto-generated)
    insights: List[str] = Field(default_factory=list)
    # Example: [
    #   "Conversion rate increased 15% from last period",
    #   "Average offer value trending up",
    #   "Approval time decreased by 2 hours"
    # ]


class AggregatedMetric(BaseModel):
    """
    Pre-aggregated metric stored in database.

    Used for fast dashboard loading without real-time computation.
    Populated by analytics_aggregator job.
    """
    id: UUID = Field(default_factory=uuid4)
    metric_type: str  # Type of aggregation
    granularity: TimeGranularity
    period_start: datetime
    period_end: datetime

    # Aggregated values
    count: int = 0
    sum_value: Optional[Decimal] = None
    avg_value: Optional[Decimal] = None
    min_value: Optional[Decimal] = None
    max_value: Optional[Decimal] = None

    # Additional metadata
    dimensions: Dict[str, any] = Field(default_factory=dict)
    # Example: {"category": "software_development", "status": "accepted"}

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class AnalyticsQuery(BaseModel):
    """
    Query parameters for analytics data.

    Used by API endpoints to filter and aggregate metrics.
    """
    start_date: date
    end_date: date
    granularity: TimeGranularity = TimeGranularity.DAY

    # Filters
    metric_types: Optional[List[MetricType]] = None
    customer_ids: Optional[List[UUID]] = None
    offer_categories: Optional[List[str]] = None

    # Aggregations
    include_conversion_funnel: bool = True
    include_time_series: bool = True
    include_performance: bool = True

    class Config:
        use_enum_values = True

    def validate_date_range(self) -> None:
        """Validate that date range is reasonable"""
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")

        delta = self.end_date - self.start_date
        max_days = {
            TimeGranularity.HOUR: 7,
            TimeGranularity.DAY: 365,
            TimeGranularity.WEEK: 730,
            TimeGranularity.MONTH: 1095,
            TimeGranularity.YEAR: 3650
        }

        if delta.days > max_days[self.granularity]:
            raise ValueError(
                f"Date range too large for {self.granularity.value} granularity. "
                f"Maximum: {max_days[self.granularity]} days"
            )


class RevenueMetrics(BaseModel):
    """
    Revenue-focused analytics.

    Financial metrics for business reporting.
    """
    period_start: datetime
    period_end: datetime

    # Revenue
    total_pipeline_value: Decimal = Decimal("0.00")  # All pending offers
    total_won_value: Decimal = Decimal("0.00")  # Accepted offers
    total_lost_value: Decimal = Decimal("0.00")  # Rejected offers

    # Forecasting
    forecasted_revenue: Decimal = Decimal("0.00")  # Based on historical acceptance rate
    forecast_confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # By period
    revenue_by_month: Dict[str, Decimal] = Field(default_factory=dict)
    # Example: {"2025-10": 125000.00, "2025-11": 142000.00}

    # Trends
    mom_growth: Optional[float] = None  # Month-over-month growth percentage
    yoy_growth: Optional[float] = None  # Year-over-year growth percentage

    # Average deal metrics
    avg_deal_size: Decimal = Decimal("0.00")
    avg_sales_cycle_days: float = 0.0
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)


class AlertThreshold(BaseModel):
    """
    Threshold configuration for metric alerts.

    Triggers notifications when metrics exceed/fall below thresholds.
    """
    id: UUID = Field(default_factory=uuid4)
    metric_type: str
    threshold_value: Decimal
    operator: str  # "gt", "lt", "eq", "gte", "lte"
    severity: str  # "info", "warning", "critical"
    enabled: bool = True

    # Notification
    notification_channels: List[str] = Field(default_factory=list)
    # Example: ["email", "slack", "webhook"]

    # Examples:
    # - Alert when offer generation time > 25s (approaching 30s SLA)
    # - Alert when acceptance rate < 40% (below target)
    # - Alert when error rate > 5%


# Helper functions for analytics calculations

def calculate_percentile(values: List[Decimal], percentile: float) -> Decimal:
    """
    Calculate percentile value from a list.

    Args:
        values: List of values
        percentile: Percentile to calculate (0.0 to 1.0)

    Returns:
        Percentile value
    """
    if not values:
        return Decimal("0.00")

    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile)
    return sorted_values[min(index, len(sorted_values) - 1)]


def calculate_moving_average(
    time_series: List[TimeSeriesDataPoint],
    window: int
) -> List[TimeSeriesDataPoint]:
    """
    Calculate moving average for time series data.

    Args:
        time_series: Original time series
        window: Size of moving average window

    Returns:
        Smoothed time series
    """
    if len(time_series) < window:
        return time_series

    smoothed = []
    for i in range(len(time_series) - window + 1):
        window_values = [dp.value for dp in time_series[i:i+window]]
        avg_value = sum(window_values) / len(window_values)

        smoothed.append(TimeSeriesDataPoint(
            timestamp=time_series[i + window - 1].timestamp,
            value=avg_value,
            metadata={"window": window, "smoothed": True}
        ))

    return smoothed


def generate_insights(dashboard: AnalyticsDashboard) -> List[str]:
    """
    Generate automated insights from dashboard data.

    Args:
        dashboard: Analytics dashboard

    Returns:
        List of insight strings
    """
    insights = []

    # Conversion rate insights
    if dashboard.conversion_funnel.overall_conversion > 0.3:
        insights.append(
            f"Strong conversion rate of {dashboard.conversion_funnel.overall_conversion:.1%}"
        )
    elif dashboard.conversion_funnel.overall_conversion < 0.2:
        insights.append(
            f"Low conversion rate of {dashboard.conversion_funnel.overall_conversion:.1%} - investigate funnel drop-offs"
        )

    # Offer value insights
    if dashboard.offer_metrics.total_offers > 0:
        avg_value = dashboard.offer_metrics.avg_value
        insights.append(
            f"Average offer value: €{avg_value:,.2f}"
        )

    # Performance insights
    if dashboard.performance_metrics.avg_response_time_ms > 2000:
        insights.append(
            "⚠️ API response times above target - consider optimization"
        )

    # Approval insights
    if dashboard.approval_metrics.avg_approval_time_hours > 24:
        insights.append(
            f"⚠️ Average approval time ({dashboard.approval_metrics.avg_approval_time_hours:.1f}h) exceeds 24h target"
        )

    return insights
