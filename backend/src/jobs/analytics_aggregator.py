"""
Analytics Data Aggregation Job (T097)

Background job that pre-aggregates analytics data for fast dashboard loading.
Runs periodically to compute time-series aggregations and summary metrics.

Schedule: Hourly for real-time data, daily for historical summaries
"""

import asyncio
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import List, Dict
import logging

from ..models.analytics import (
    MetricType,
    TimeGranularity,
    AggregatedMetric
)
from ..services.analytics.main import AnalyticsService

logger = logging.getLogger(__name__)


class AnalyticsAggregator:
    """
    Aggregates raw metric events into pre-computed summaries.

    Benefits:
    - Fast dashboard loading (no real-time computation)
    - Reduced database load
    - Historical trend analysis
    - Efficient time-series queries
    """

    def __init__(self, db_connection=None):
        """
        Initialize aggregator.

        Args:
            db_connection: Database connection for reading/writing metrics
        """
        self.db = db_connection
        self.analytics_service = AnalyticsService(db_connection)
        self.logger = logger

    async def run_hourly_aggregation(self) -> None:
        """
        Run hourly aggregation job.

        Aggregates data from the past hour for real-time dashboards.
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)

        self.logger.info(f"Starting hourly aggregation: {start_time} to {end_time}")

        try:
            # Aggregate by metric type
            await self._aggregate_metric_counts(
                start_time, end_time, TimeGranularity.HOUR
            )

            # Aggregate offer values
            await self._aggregate_offer_values(
                start_time, end_time, TimeGranularity.HOUR
            )

            # Aggregate performance metrics
            await self._aggregate_performance(
                start_time, end_time, TimeGranularity.HOUR
            )

            self.logger.info("Hourly aggregation completed successfully")

        except Exception as e:
            self.logger.error(f"Hourly aggregation failed: {e}", exc_info=True)
            raise

    async def run_daily_aggregation(self) -> None:
        """
        Run daily aggregation job.

        Aggregates data from the previous day for historical analysis.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=1)

        end_time = datetime.combine(end_date, datetime.min.time())
        start_time = datetime.combine(start_date, datetime.min.time())

        self.logger.info(f"Starting daily aggregation: {start_date}")

        try:
            # Aggregate by day
            await self._aggregate_metric_counts(
                start_time, end_time, TimeGranularity.DAY
            )

            await self._aggregate_offer_values(
                start_time, end_time, TimeGranularity.DAY
            )

            await self._aggregate_performance(
                start_time, end_time, TimeGranularity.DAY
            )

            # Aggregate conversion funnel for the day
            await self._aggregate_conversion_funnel(start_date, end_date)

            self.logger.info("Daily aggregation completed successfully")

        except Exception as e:
            self.logger.error(f"Daily aggregation failed: {e}", exc_info=True)
            raise

    async def run_weekly_aggregation(self) -> None:
        """
        Run weekly aggregation job.

        Aggregates data from the previous week.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        self.logger.info(f"Starting weekly aggregation: {start_date} to {end_date}")

        try:
            end_time = datetime.combine(end_date, datetime.min.time())
            start_time = datetime.combine(start_date, datetime.min.time())

            await self._aggregate_metric_counts(
                start_time, end_time, TimeGranularity.WEEK
            )

            await self._aggregate_offer_values(
                start_time, end_time, TimeGranularity.WEEK
            )

            await self._aggregate_conversion_funnel(start_date, end_date)

            self.logger.info("Weekly aggregation completed successfully")

        except Exception as e:
            self.logger.error(f"Weekly aggregation failed: {e}", exc_info=True)
            raise

    async def run_monthly_aggregation(self) -> None:
        """
        Run monthly aggregation job.

        Aggregates data from the previous month.
        """
        today = date.today()
        first_of_month = date(today.year, today.month, 1)
        last_of_prev_month = first_of_month - timedelta(days=1)
        first_of_prev_month = date(last_of_prev_month.year, last_of_prev_month.month, 1)

        self.logger.info(f"Starting monthly aggregation: {first_of_prev_month} to {last_of_prev_month}")

        try:
            start_time = datetime.combine(first_of_prev_month, datetime.min.time())
            end_time = datetime.combine(last_of_prev_month, datetime.max.time())

            await self._aggregate_metric_counts(
                start_time, end_time, TimeGranularity.MONTH
            )

            await self._aggregate_offer_values(
                start_time, end_time, TimeGranularity.MONTH
            )

            await self._aggregate_conversion_funnel(
                first_of_prev_month, last_of_prev_month
            )

            self.logger.info("Monthly aggregation completed successfully")

        except Exception as e:
            self.logger.error(f"Monthly aggregation failed: {e}", exc_info=True)
            raise

    async def _aggregate_metric_counts(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> None:
        """
        Aggregate metric counts by type.

        Args:
            start_time: Period start
            end_time: Period end
            granularity: Aggregation level
        """
        if not self.db:
            return

        # Count each metric type
        for metric_type in MetricType:
            count = await self.db.count_metric_events(
                metric_type=metric_type,
                start_time=start_time,
                end_time=end_time
            )

            if count > 0:
                aggregated = AggregatedMetric(
                    metric_type=f"count_{metric_type.value}",
                    granularity=granularity,
                    period_start=start_time,
                    period_end=end_time,
                    count=count
                )

                await self.db.upsert_aggregated_metric(aggregated)

                self.logger.debug(
                    f"Aggregated {metric_type.value}: {count} events"
                )

    async def _aggregate_offer_values(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> None:
        """
        Aggregate offer value statistics.

        Args:
            start_time: Period start
            end_time: Period end
            granularity: Aggregation level
        """
        if not self.db:
            return

        # Get all offer events in period
        offer_events = await self.db.get_metric_events(
            metric_type=MetricType.OFFER_GENERATED,
            start_time=start_time,
            end_time=end_time
        )

        if not offer_events:
            return

        values = [e.value for e in offer_events if e.value]

        if values:
            aggregated = AggregatedMetric(
                metric_type="offer_values",
                granularity=granularity,
                period_start=start_time,
                period_end=end_time,
                count=len(values),
                sum_value=sum(values),
                avg_value=sum(values) / len(values),
                min_value=min(values),
                max_value=max(values),
                dimensions={
                    "total_value": str(sum(values)),
                    "avg_value": str(sum(values) / len(values))
                }
            )

            await self.db.upsert_aggregated_metric(aggregated)

            self.logger.debug(
                f"Aggregated offer values: count={len(values)}, "
                f"total={sum(values)}, avg={sum(values)/len(values)}"
            )

    async def _aggregate_performance(
        self,
        start_time: datetime,
        end_time: datetime,
        granularity: TimeGranularity
    ) -> None:
        """
        Aggregate performance metrics (response times, errors).

        Args:
            start_time: Period start
            end_time: Period end
            granularity: Aggregation level
        """
        if not self.db:
            return

        # Get API call events
        api_events = await self.db.get_metric_events(
            metric_type=MetricType.API_CALL,
            start_time=start_time,
            end_time=end_time
        )

        if not api_events:
            return

        # Calculate statistics
        durations = [e.duration_ms for e in api_events if e.duration_ms]
        errors = [e for e in api_events if e.status == "error"]

        if durations:
            aggregated = AggregatedMetric(
                metric_type="api_performance",
                granularity=granularity,
                period_start=start_time,
                period_end=end_time,
                count=len(durations),
                avg_value=Decimal(str(sum(durations) / len(durations))),
                min_value=Decimal(str(min(durations))),
                max_value=Decimal(str(max(durations))),
                dimensions={
                    "error_count": len(errors),
                    "error_rate": len(errors) / len(api_events) if api_events else 0.0
                }
            )

            await self.db.upsert_aggregated_metric(aggregated)

            self.logger.debug(
                f"Aggregated API performance: count={len(durations)}, "
                f"avg={sum(durations)/len(durations)}ms, errors={len(errors)}"
            )

    async def _aggregate_conversion_funnel(
        self,
        start_date: date,
        end_date: date
    ) -> None:
        """
        Aggregate conversion funnel metrics.

        Args:
            start_date: Period start date
            end_date: Period end date
        """
        if not self.db:
            return

        funnel = await self.analytics_service.get_conversion_funnel(
            start_date, end_date
        )

        # Store as aggregated metric
        aggregated = AggregatedMetric(
            metric_type="conversion_funnel",
            granularity=TimeGranularity.DAY,
            period_start=datetime.combine(start_date, datetime.min.time()),
            period_end=datetime.combine(end_date, datetime.max.time()),
            count=funnel.conversations_started,
            dimensions={
                "conversations_started": funnel.conversations_started,
                "conversations_completed": funnel.conversations_completed,
                "offers_generated": funnel.offers_generated,
                "offers_sent": funnel.offers_sent,
                "offers_viewed": funnel.offers_viewed,
                "offers_accepted": funnel.offers_accepted,
                "offers_rejected": funnel.offers_rejected,
                "completion_rate": funnel.completion_rate,
                "acceptance_rate": funnel.acceptance_rate,
                "overall_conversion": funnel.overall_conversion
            }
        )

        await self.db.upsert_aggregated_metric(aggregated)

        self.logger.debug(
            f"Aggregated conversion funnel: {funnel.conversations_started} started, "
            f"{funnel.offers_accepted} accepted ({funnel.overall_conversion:.1%})"
        )

    async def cleanup_old_aggregations(self, days_to_keep: int = 90) -> None:
        """
        Clean up old aggregated data.

        Args:
            days_to_keep: Number of days to retain
        """
        if not self.db:
            return

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        deleted_count = await self.db.delete_aggregations_before(cutoff_date)

        self.logger.info(
            f"Cleaned up {deleted_count} old aggregations (before {cutoff_date.date()})"
        )


# Scheduler functions for production use

async def run_hourly_job():
    """Run hourly aggregation (for cron/celery)"""
    aggregator = AnalyticsAggregator()
    await aggregator.run_hourly_aggregation()


async def run_daily_job():
    """Run daily aggregation (for cron/celery)"""
    aggregator = AnalyticsAggregator()
    await aggregator.run_daily_aggregation()


async def run_weekly_job():
    """Run weekly aggregation (for cron/celery)"""
    aggregator = AnalyticsAggregator()
    await aggregator.run_weekly_aggregation()


async def run_monthly_job():
    """Run monthly aggregation (for cron/celery)"""
    aggregator = AnalyticsAggregator()
    await aggregator.run_monthly_aggregation()


async def run_cleanup_job():
    """Run cleanup job (for cron/celery)"""
    aggregator = AnalyticsAggregator()
    await aggregator.cleanup_old_aggregations(days_to_keep=90)


# CLI entry point for manual execution
if __name__ == "__main__":
    import sys

    async def main():
        aggregator = AnalyticsAggregator()

        job_type = sys.argv[1] if len(sys.argv) > 1 else "hourly"

        if job_type == "hourly":
            await aggregator.run_hourly_aggregation()
        elif job_type == "daily":
            await aggregator.run_daily_aggregation()
        elif job_type == "weekly":
            await aggregator.run_weekly_aggregation()
        elif job_type == "monthly":
            await aggregator.run_monthly_aggregation()
        elif job_type == "cleanup":
            await aggregator.cleanup_old_aggregations()
        else:
            print(f"Unknown job type: {job_type}")
            print("Usage: python analytics_aggregator.py [hourly|daily|weekly|monthly|cleanup]")
            sys.exit(1)

    asyncio.run(main())
