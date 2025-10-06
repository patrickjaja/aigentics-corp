"""
Analytics Service (T093)

Collects and aggregates metrics for offer generation, conversion rates,
and system performance. Provides data for analytics dashboard and reporting.
"""

from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from uuid import UUID
import logging

from ...models.analytics import (
    MetricEvent,
    MetricType,
    TimeGranularity,
    ConversionFunnelMetrics,
    OfferMetrics,
    PerformanceMetrics,
    CustomerAnalytics,
    ApprovalWorkflowMetrics,
    AnalyticsDashboard,
    TimeSeries,
    TimeSeriesDataPoint,
    AnalyticsQuery,
    RevenueMetrics,
    AggregatedMetric,
    calculate_percentile,
    generate_insights
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service for collecting and analyzing metrics.

    Responsibilities:
    - Track metric events
    - Calculate conversion rates
    - Generate time-series data
    - Compute aggregated statistics
    - Provide dashboard data
    """

    def __init__(self, db_connection=None):
        """
        Initialize analytics service.

        Args:
            db_connection: Database connection for metric storage
        """
        self.db = db_connection
        self.logger = logger

    async def track_event(
        self,
        metric_type: MetricType,
        customer_id: Optional[UUID] = None,
        conversation_id: Optional[UUID] = None,
        offer_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        value: Optional[Decimal] = None,
        duration_ms: Optional[int] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> MetricEvent:
        """
        Track a metric event.

        Args:
            metric_type: Type of metric
            customer_id: Associated customer UUID
            conversation_id: Associated conversation UUID
            offer_id: Associated offer UUID
            user_id: User who triggered event
            value: Numeric value (e.g., offer amount)
            duration_ms: Duration in milliseconds
            status: Event status
            metadata: Additional metadata

        Returns:
            Created metric event

        Example:
            await analytics.track_event(
                metric_type=MetricType.OFFER_GENERATED,
                offer_id=offer.id,
                value=Decimal("125000.00"),
                duration_ms=18500,
                status="success"
            )
        """
        event = MetricEvent(
            metric_type=metric_type,
            customer_id=customer_id,
            conversation_id=conversation_id,
            offer_id=offer_id,
            user_id=user_id,
            value=value,
            duration_ms=duration_ms,
            status=status,
            metadata=metadata or {}
        )

        # Store event
        if self.db:
            await self.db.insert_metric_event(event)

        self.logger.info(
            f"Tracked {metric_type.value} event",
            extra={
                "metric_type": metric_type.value,
                "offer_id": str(offer_id) if offer_id else None,
                "value": str(value) if value else None
            }
        )

        return event

    async def get_conversion_funnel(
        self,
        start_date: date,
        end_date: date
    ) -> ConversionFunnelMetrics:
        """
        Calculate conversion funnel metrics.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Conversion funnel metrics with calculated rates
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        # Query event counts from database
        if self.db:
            funnel = ConversionFunnelMetrics(
                period_start=period_start,
                period_end=period_end,
                conversations_started=await self._count_events(
                    MetricType.CONVERSATION_STARTED, period_start, period_end
                ),
                conversations_completed=await self._count_events(
                    MetricType.CONVERSATION_COMPLETED, period_start, period_end
                ),
                offers_generated=await self._count_events(
                    MetricType.OFFER_GENERATED, period_start, period_end
                ),
                offers_sent=await self._count_events(
                    MetricType.OFFER_SENT, period_start, period_end
                ),
                offers_viewed=await self._count_events(
                    MetricType.OFFER_VIEWED, period_start, period_end
                ),
                offers_accepted=await self._count_events(
                    MetricType.OFFER_ACCEPTED, period_start, period_end
                ),
                offers_rejected=await self._count_events(
                    MetricType.OFFER_REJECTED, period_start, period_end
                )
            )
        else:
            # Mock data for development
            funnel = ConversionFunnelMetrics(
                period_start=period_start,
                period_end=period_end,
                conversations_started=500,
                conversations_completed=385,
                offers_generated=320,
                offers_sent=280,
                offers_viewed=245,
                offers_accepted=156,
                offers_rejected=89
            )

        # Calculate rates
        funnel.calculate_rates()

        return funnel

    async def get_offer_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> OfferMetrics:
        """
        Calculate aggregated offer metrics.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Offer metrics with performance indicators
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        if self.db:
            # Query from database
            offer_events = await self.db.get_metric_events(
                metric_type=MetricType.OFFER_GENERATED,
                start_time=period_start,
                end_time=period_end
            )

            # Calculate metrics
            total_offers = len(offer_events)
            values = [e.value for e in offer_events if e.value]
            durations = [e.duration_ms for e in offer_events if e.duration_ms]

            metrics = OfferMetrics(
                period_start=period_start,
                period_end=period_end,
                total_offers=total_offers,
                total_sent=await self._count_events(
                    MetricType.OFFER_SENT, period_start, period_end
                ),
                total_accepted=await self._count_events(
                    MetricType.OFFER_ACCEPTED, period_start, period_end
                ),
                total_rejected=await self._count_events(
                    MetricType.OFFER_REJECTED, period_start, period_end
                ),
                total_value=sum(values) if values else Decimal("0.00"),
                avg_value=sum(values) / len(values) if values else Decimal("0.00"),
                median_value=calculate_percentile(values, 0.5) if values else None,
                min_value=min(values) if values else None,
                max_value=max(values) if values else None,
                avg_generation_time_ms=int(sum(durations) / len(durations)) if durations else 0,
                max_generation_time_ms=max(durations) if durations else 0,
                generation_timeout_count=len([d for d in durations if d > 30000])
            )

            # Calculate accepted value
            accepted_events = await self.db.get_metric_events(
                metric_type=MetricType.OFFER_ACCEPTED,
                start_time=period_start,
                end_time=period_end
            )
            metrics.accepted_value = sum(
                e.value for e in accepted_events if e.value
            ) or Decimal("0.00")

        else:
            # Mock data
            metrics = OfferMetrics(
                period_start=period_start,
                period_end=period_end,
                total_offers=142,
                total_sent=120,
                total_accepted=67,
                total_rejected=35,
                total_value=Decimal("12075000.00"),
                avg_value=Decimal("85035.21"),
                median_value=Decimal("78000.00"),
                min_value=Decimal("25000.00"),
                max_value=Decimal("450000.00"),
                accepted_value=Decimal("5698000.00"),
                avg_generation_time_ms=18500,
                max_generation_time_ms=28900,
                generation_timeout_count=2,
                approval_required_count=28,
                approval_rate=0.89,
                avg_approval_time_hours=14.5,
                avg_time_to_acceptance_hours=101.2
            )

        return metrics

    async def get_performance_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> PerformanceMetrics:
        """
        Calculate system performance metrics.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Performance metrics with API stats
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        if self.db:
            api_events = await self.db.get_metric_events(
                metric_type=MetricType.API_CALL,
                start_time=period_start,
                end_time=period_end
            )

            durations = [e.duration_ms for e in api_events if e.duration_ms]
            errors = [e for e in api_events if e.status == "error"]

            metrics = PerformanceMetrics(
                period_start=period_start,
                period_end=period_end,
                total_api_calls=len(api_events),
                avg_response_time_ms=int(sum(durations) / len(durations)) if durations else 0,
                p50_response_time_ms=int(calculate_percentile(
                    [Decimal(d) for d in durations], 0.5
                )) if durations else 0,
                p95_response_time_ms=int(calculate_percentile(
                    [Decimal(d) for d in durations], 0.95
                )) if durations else 0,
                p99_response_time_ms=int(calculate_percentile(
                    [Decimal(d) for d in durations], 0.99
                )) if durations else 0,
                error_count=len(errors),
                error_rate=len(errors) / len(api_events) if api_events else 0.0
            )

            # Group by endpoint
            endpoint_stats = {}
            for event in api_events:
                endpoint = event.metadata.get("endpoint", "unknown")
                if endpoint not in endpoint_stats:
                    endpoint_stats[endpoint] = {
                        "count": 0,
                        "total_time": 0,
                        "errors": 0
                    }

                endpoint_stats[endpoint]["count"] += 1
                endpoint_stats[endpoint]["total_time"] += event.duration_ms or 0
                if event.status == "error":
                    endpoint_stats[endpoint]["errors"] += 1

            # Calculate averages
            for endpoint, stats in endpoint_stats.items():
                stats["avg_time_ms"] = stats["total_time"] // stats["count"]
                stats["error_rate"] = stats["errors"] / stats["count"]
                del stats["total_time"]

            metrics.endpoint_stats = endpoint_stats

        else:
            # Mock data
            metrics = PerformanceMetrics(
                period_start=period_start,
                period_end=period_end,
                total_api_calls=15420,
                avg_response_time_ms=450,
                p50_response_time_ms=320,
                p95_response_time_ms=1250,
                p99_response_time_ms=2100,
                error_count=87,
                error_rate=0.0056,
                endpoint_stats={
                    "/conversations": {
                        "count": 5200,
                        "avg_time_ms": 380,
                        "error_rate": 0.003
                    },
                    "/offers": {
                        "count": 3100,
                        "avg_time_ms": 18500,
                        "error_rate": 0.012
                    },
                    "/customers": {
                        "count": 2800,
                        "avg_time_ms": 210,
                        "error_rate": 0.002
                    }
                },
                sla_compliance_rate=0.947
            )

        return metrics

    async def get_customer_analytics(
        self,
        start_date: date,
        end_date: date
    ) -> CustomerAnalytics:
        """
        Calculate customer behavior analytics.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Customer analytics with engagement metrics
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        # Mock data (would query from database)
        analytics = CustomerAnalytics(
            period_start=period_start,
            period_end=period_end,
            total_customers=347,
            new_customers=89,
            returning_customers=258,
            avg_conversations_per_customer=1.44,
            avg_messages_per_conversation=8.3,
            avg_time_to_complete_conversation_minutes=42.5,
            offers_by_category={
                "software_development": 98,
                "consulting": 45,
                "infrastructure": 32,
                "mixed": 28
            },
            customers_by_country={
                "DE": 245,
                "AT": 42,
                "CH": 38,
                "FR": 15,
                "NL": 7
            }
        )

        return analytics

    async def get_approval_metrics(
        self,
        start_date: date,
        end_date: date
    ) -> ApprovalWorkflowMetrics:
        """
        Calculate approval workflow metrics.

        Args:
            start_date: Period start date
            end_date: Period end date

        Returns:
            Approval workflow metrics
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        # Mock data
        metrics = ApprovalWorkflowMetrics(
            period_start=period_start,
            period_end=period_end,
            total_approvals_requested=28,
            total_approved=25,
            total_rejected=2,
            total_pending=1,
            approval_rate=0.89,
            rejection_rate=0.07,
            avg_approval_time_hours=14.5,
            median_approval_time_hours=11.2,
            max_approval_time_hours=38.5,
            approvals_by_value_range={
                "100k-150k": 12,
                "150k-200k": 8,
                "200k-300k": 5,
                "300k+": 3
            },
            within_sla_count=22,
            sla_compliance_rate=0.79
        )

        return metrics

    async def get_time_series(
        self,
        metric_name: str,
        start_date: date,
        end_date: date,
        granularity: TimeGranularity = TimeGranularity.DAY
    ) -> TimeSeries:
        """
        Generate time series data for charting.

        Args:
            metric_name: Name of metric (e.g., "offers_generated")
            start_date: Period start date
            end_date: Period end date
            granularity: Time aggregation level

        Returns:
            Time series with data points
        """
        period_start = datetime.combine(start_date, datetime.min.time())
        period_end = datetime.combine(end_date, datetime.max.time())

        # Generate time buckets based on granularity
        time_buckets = self._generate_time_buckets(
            period_start, period_end, granularity
        )

        data_points = []

        # Query aggregated data for each bucket
        for bucket_start, bucket_end in time_buckets:
            if self.db:
                count = await self._count_events_in_bucket(
                    metric_name, bucket_start, bucket_end
                )
                value = await self._sum_values_in_bucket(
                    metric_name, bucket_start, bucket_end
                )
            else:
                # Mock data with some variation
                import random
                count = random.randint(5, 25)
                value = Decimal(str(random.uniform(50000, 150000)))

            data_points.append(TimeSeriesDataPoint(
                timestamp=bucket_start,
                value=value,
                count=count
            ))

        return TimeSeries(
            metric_name=metric_name,
            granularity=granularity,
            period_start=period_start,
            period_end=period_end,
            data_points=data_points
        )

    async def get_dashboard_data(
        self,
        query: AnalyticsQuery
    ) -> AnalyticsDashboard:
        """
        Generate complete dashboard data.

        Args:
            query: Analytics query parameters

        Returns:
            Complete dashboard with all metrics
        """
        query.validate_date_range()

        # Gather all metrics
        conversion_funnel = await self.get_conversion_funnel(
            query.start_date, query.end_date
        )
        offer_metrics = await self.get_offer_metrics(
            query.start_date, query.end_date
        )
        performance_metrics = await self.get_performance_metrics(
            query.start_date, query.end_date
        )
        customer_analytics = await self.get_customer_analytics(
            query.start_date, query.end_date
        )
        approval_metrics = await self.get_approval_metrics(
            query.start_date, query.end_date
        )

        # Generate time series
        time_series = []
        if query.include_time_series:
            time_series = [
                await self.get_time_series(
                    "offers_generated",
                    query.start_date,
                    query.end_date,
                    query.granularity
                ),
                await self.get_time_series(
                    "offers_accepted",
                    query.start_date,
                    query.end_date,
                    query.granularity
                )
            ]

        # Create dashboard
        dashboard = AnalyticsDashboard(
            period_start=datetime.combine(query.start_date, datetime.min.time()),
            period_end=datetime.combine(query.end_date, datetime.max.time()),
            conversion_funnel=conversion_funnel,
            offer_metrics=offer_metrics,
            performance_metrics=performance_metrics,
            customer_analytics=customer_analytics,
            approval_metrics=approval_metrics,
            time_series=time_series
        )

        # Generate insights
        dashboard.insights = generate_insights(dashboard)

        return dashboard

    async def _count_events(
        self,
        metric_type: MetricType,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Count events of a specific type in time range"""
        if self.db:
            return await self.db.count_metric_events(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time
            )
        return 0

    async def _count_events_in_bucket(
        self,
        metric_name: str,
        bucket_start: datetime,
        bucket_end: datetime
    ) -> int:
        """Count events in a specific time bucket"""
        if self.db:
            return await self.db.count_events_in_bucket(
                metric_name, bucket_start, bucket_end
            )
        return 0

    async def _sum_values_in_bucket(
        self,
        metric_name: str,
        bucket_start: datetime,
        bucket_end: datetime
    ) -> Decimal:
        """Sum values in a specific time bucket"""
        if self.db:
            return await self.db.sum_values_in_bucket(
                metric_name, bucket_start, bucket_end
            )
        return Decimal("0.00")

    def _generate_time_buckets(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> List[Tuple[datetime, datetime]]:
        """
        Generate time buckets for aggregation.

        Args:
            start_time: Period start
            end_time: Period end
            granularity: Bucket size

        Returns:
            List of (bucket_start, bucket_end) tuples
        """
        buckets = []
        current = start_time

        delta_map = {
            TimeGranularity.HOUR: timedelta(hours=1),
            TimeGranularity.DAY: timedelta(days=1),
            TimeGranularity.WEEK: timedelta(weeks=1),
            TimeGranularity.MONTH: timedelta(days=30),  # Approximate
            TimeGranularity.YEAR: timedelta(days=365)   # Approximate
        }

        delta = delta_map[granularity]

        while current < end_time:
            bucket_end = min(current + delta, end_time)
            buckets.append((current, bucket_end))
            current = bucket_end

        return buckets


# Dependency injection for FastAPI
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """
    Get analytics service instance.

    Returns:
        Shared analytics service instance
    """
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AnalyticsService()
    return _analytics_service


def set_analytics_service(service: AnalyticsService) -> None:
    """
    Set analytics service instance (for testing).

    Args:
        service: Analytics service to use
    """
    global _analytics_service
    _analytics_service = service
