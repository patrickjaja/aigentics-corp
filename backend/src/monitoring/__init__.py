"""Monitoring and metrics module.

This module provides comprehensive monitoring capabilities:
- Prometheus metrics collection
- Health check endpoints
- Performance tracking
"""

from .metrics import (
    MetricsCollector,
    monitor_duration,
    get_metrics,
    get_metrics_content_type,
    # HTTP metrics
    http_requests_total,
    http_request_duration_seconds,
    # Business metrics
    offers_generated_total,
    offer_generation_duration_seconds,
    conversations_created_total,
    # LLM metrics
    llm_requests_total,
    llm_request_duration_seconds,
    llm_tokens_total,
    # System metrics
    database_connections_active,
    circuit_breaker_state,
)

__all__ = [
    "MetricsCollector",
    "monitor_duration",
    "get_metrics",
    "get_metrics_content_type",
    "http_requests_total",
    "http_request_duration_seconds",
    "offers_generated_total",
    "offer_generation_duration_seconds",
    "conversations_created_total",
    "llm_requests_total",
    "llm_request_duration_seconds",
    "llm_tokens_total",
    "database_connections_active",
    "circuit_breaker_state",
]
