"""Prometheus metrics integration for monitoring.

This module provides comprehensive metrics collection for:
- HTTP request duration and error rates
- Business metrics (offers, conversations, approvals)
- System metrics (database, Redis, external services)
- LangGraph workflow performance

Metrics are exposed on /metrics endpoint for Prometheus scraping.
"""

import logging
import time
from functools import wraps
from typing import Callable, Optional, Dict, Any

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.multiprocess import MultiProcessCollector
from prometheus_client.core import REGISTRY

logger = logging.getLogger(__name__)


# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

http_request_size_bytes = Summary(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
)

http_response_size_bytes = Summary(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
)

http_errors_total = Counter(
    "http_errors_total",
    "Total HTTP errors",
    ["method", "endpoint", "error_type"],
)


# ============================================================================
# Business Metrics
# ============================================================================

# Conversations
conversations_created_total = Counter(
    "conversations_created_total",
    "Total conversations created",
    ["language"],
)

conversations_completed_total = Counter(
    "conversations_completed_total",
    "Total conversations completed",
    ["language"],
)

conversation_messages_total = Counter(
    "conversation_messages_total",
    "Total conversation messages",
    ["role"],  # user, assistant, system
)

conversation_duration_seconds = Histogram(
    "conversation_duration_seconds",
    "Conversation duration from start to completion",
    buckets=[60, 300, 600, 1800, 3600, 7200],  # 1min to 2hrs
)

conversation_rounds_total = Histogram(
    "conversation_rounds_total",
    "Number of question rounds per conversation",
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
)

# Offers
offers_generated_total = Counter(
    "offers_generated_total",
    "Total offers generated",
    ["status"],
)

offer_generation_duration_seconds = Histogram(
    "offer_generation_duration_seconds",
    "Offer generation duration in seconds",
    buckets=[1, 5, 10, 15, 20, 25, 30, 40, 50, 60],
)

offer_value_euros = Histogram(
    "offer_value_euros",
    "Offer value in EUR",
    buckets=[1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000],
)

offer_work_packages_count = Histogram(
    "offer_work_packages_count",
    "Number of work packages per offer",
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20],
)

offers_downloaded_total = Counter(
    "offers_downloaded_total",
    "Total offer PDFs downloaded",
    ["format"],  # pdf
)

# Approvals
approvals_created_total = Counter(
    "approvals_created_total",
    "Total approval workflows created",
    ["reason"],  # high_value, custom
)

approvals_completed_total = Counter(
    "approvals_completed_total",
    "Total approval workflows completed",
    ["decision"],  # approved, rejected
)

approval_duration_seconds = Histogram(
    "approval_duration_seconds",
    "Approval workflow duration",
    buckets=[60, 300, 1800, 3600, 86400, 172800, 604800],  # 1min to 1week
)

# Customers
customers_created_total = Counter(
    "customers_created_total",
    "Total customers created",
)

gdpr_requests_total = Counter(
    "gdpr_requests_total",
    "Total GDPR requests",
    ["request_type"],  # deletion, export, consent
)


# ============================================================================
# AI/LLM Metrics
# ============================================================================

llm_requests_total = Counter(
    "llm_requests_total",
    "Total LLM API requests",
    ["model", "status"],
)

llm_request_duration_seconds = Histogram(
    "llm_request_duration_seconds",
    "LLM request duration",
    ["model"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0],
)

llm_tokens_total = Counter(
    "llm_tokens_total",
    "Total LLM tokens used",
    ["model", "token_type"],  # prompt, completion
)

llm_cost_euros = Counter(
    "llm_cost_euros",
    "Estimated LLM cost in EUR",
    ["model"],
)


# ============================================================================
# LangGraph Workflow Metrics
# ============================================================================

workflow_executions_total = Counter(
    "workflow_executions_total",
    "Total workflow executions",
    ["workflow_name", "status"],
)

workflow_duration_seconds = Histogram(
    "workflow_duration_seconds",
    "Workflow execution duration",
    ["workflow_name"],
    buckets=[1, 5, 10, 30, 60, 120, 300],
)

workflow_step_duration_seconds = Histogram(
    "workflow_step_duration_seconds",
    "Individual workflow step duration",
    ["workflow_name", "step_name"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

workflow_errors_total = Counter(
    "workflow_errors_total",
    "Total workflow errors",
    ["workflow_name", "error_type"],
)


# ============================================================================
# System Metrics
# ============================================================================

# Database
database_connections_active = Gauge(
    "database_connections_active",
    "Active database connections",
)

database_connections_idle = Gauge(
    "database_connections_idle",
    "Idle database connections in pool",
)

database_query_duration_seconds = Histogram(
    "database_query_duration_seconds",
    "Database query duration",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

database_errors_total = Counter(
    "database_errors_total",
    "Total database errors",
    ["error_type"],
)

# Redis
redis_operations_total = Counter(
    "redis_operations_total",
    "Total Redis operations",
    ["operation", "status"],
)

redis_operation_duration_seconds = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# Qdrant
qdrant_operations_total = Counter(
    "qdrant_operations_total",
    "Total Qdrant operations",
    ["operation", "status"],
)

qdrant_search_duration_seconds = Histogram(
    "qdrant_search_duration_seconds",
    "Qdrant search duration",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

qdrant_collection_size = Gauge(
    "qdrant_collection_size",
    "Number of vectors in Qdrant collection",
    ["collection"],
)

# Circuit Breakers
circuit_breaker_state = Gauge(
    "circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service"],
)

circuit_breaker_failures_total = Counter(
    "circuit_breaker_failures_total",
    "Total circuit breaker failures",
    ["service"],
)

circuit_breaker_success_total = Counter(
    "circuit_breaker_success_total",
    "Total circuit breaker successes",
    ["service"],
)


# ============================================================================
# Application Info
# ============================================================================

application_info = Info(
    "application",
    "Application information",
)

application_info.info({
    "name": "ai_offer_agent",
    "version": "1.0.0",
    "environment": "production",
})


# ============================================================================
# Metric Collection Utilities
# ============================================================================

class MetricsCollector:
    """Central metrics collector for the application."""

    @staticmethod
    def record_http_request(
        method: str,
        endpoint: str,
        status_code: int,
        duration_seconds: float,
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Record HTTP request metrics.

        Args:
            method: HTTP method
            endpoint: Endpoint path
            status_code: HTTP status code
            duration_seconds: Request duration
            request_size: Request body size
            response_size: Response body size
        """
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_code,
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint,
        ).observe(duration_seconds)

        if request_size > 0:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint,
            ).observe(request_size)

        if response_size > 0:
            http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint,
            ).observe(response_size)

        # Check for SLA violations
        if duration_seconds > 3.0:
            logger.warning(
                f"SLA violation: {method} {endpoint} took {duration_seconds:.2f}s (>3s)"
            )

    @staticmethod
    def record_conversation(
        language: str,
        duration_seconds: float,
        rounds: int,
        completed: bool = True,
    ):
        """Record conversation metrics.

        Args:
            language: Conversation language
            duration_seconds: Total conversation duration
            rounds: Number of question rounds
            completed: Whether conversation completed successfully
        """
        conversations_created_total.labels(language=language).inc()

        if completed:
            conversations_completed_total.labels(language=language).inc()
            conversation_duration_seconds.observe(duration_seconds)
            conversation_rounds_total.observe(rounds)

    @staticmethod
    def record_offer_generation(
        duration_seconds: float,
        value_euros: float,
        work_packages: int,
        status: str = "generated",
    ):
        """Record offer generation metrics.

        Args:
            duration_seconds: Generation duration
            value_euros: Offer value in EUR
            work_packages: Number of work packages
            status: Offer status
        """
        offers_generated_total.labels(status=status).inc()
        offer_generation_duration_seconds.observe(duration_seconds)
        offer_value_euros.observe(value_euros)
        offer_work_packages_count.observe(work_packages)

        # Check performance target: <30s
        if duration_seconds > 30:
            logger.warning(
                f"Offer generation SLA violation: {duration_seconds:.2f}s (>30s target)"
            )

    @staticmethod
    def record_llm_request(
        model: str,
        duration_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        status: str = "success",
    ):
        """Record LLM request metrics.

        Args:
            model: LLM model name
            duration_seconds: Request duration
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            status: Request status
        """
        llm_requests_total.labels(model=model, status=status).inc()
        llm_request_duration_seconds.labels(model=model).observe(duration_seconds)
        llm_tokens_total.labels(model=model, token_type="prompt").inc(prompt_tokens)
        llm_tokens_total.labels(model=model, token_type="completion").inc(completion_tokens)

        # Rough cost estimation (GPT-4 pricing as of 2024)
        # Input: ~$0.03/1K tokens, Output: ~$0.06/1K tokens
        cost_usd = (prompt_tokens * 0.03 + completion_tokens * 0.06) / 1000
        cost_eur = cost_usd * 0.92  # Rough USD to EUR conversion
        llm_cost_euros.labels(model=model).inc(cost_eur)

    @staticmethod
    def record_workflow_execution(
        workflow_name: str,
        duration_seconds: float,
        status: str = "completed",
    ):
        """Record workflow execution metrics.

        Args:
            workflow_name: Name of the workflow
            duration_seconds: Execution duration
            status: Execution status
        """
        workflow_executions_total.labels(
            workflow_name=workflow_name,
            status=status,
        ).inc()
        workflow_duration_seconds.labels(workflow_name=workflow_name).observe(duration_seconds)

    @staticmethod
    def update_database_connections(active: int, idle: int):
        """Update database connection metrics.

        Args:
            active: Number of active connections
            idle: Number of idle connections
        """
        database_connections_active.set(active)
        database_connections_idle.set(idle)

    @staticmethod
    def update_circuit_breaker_state(service: str, state: str):
        """Update circuit breaker state.

        Args:
            service: Service name
            state: Circuit breaker state (closed, half_open, open)
        """
        state_value = {"closed": 0, "half_open": 1, "open": 2}.get(state, 0)
        circuit_breaker_state.labels(service=service).set(state_value)


def monitor_duration(metric: Histogram, **labels):
    """Decorator to monitor function duration.

    Args:
        metric: Prometheus Histogram to record to
        **labels: Metric labels

    Example:
        @monitor_duration(workflow_duration_seconds, workflow_name="offer_generation")
        async def generate_offer():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric.labels(**labels).observe(duration)
                raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def get_metrics() -> bytes:
    """Get all metrics in Prometheus format.

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get metrics content type.

    Returns:
        Content type for Prometheus metrics
    """
    return CONTENT_TYPE_LATEST
