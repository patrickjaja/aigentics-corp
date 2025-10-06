"""Tests for monitoring and metrics functionality."""

import pytest
from prometheus_client import REGISTRY


def test_metrics_registered():
    """Test that all metrics are properly registered."""
    from src.monitoring.metrics import (
        http_requests_total,
        http_request_duration_seconds,
        offers_generated_total,
        conversations_created_total,
        llm_requests_total,
    )

    # Verify metrics are registered
    registered_metrics = [metric.describe()[0].name for metric in REGISTRY.collect()]

    assert "http_requests_total" in registered_metrics
    assert "http_request_duration_seconds" in registered_metrics
    assert "offers_generated_total" in registered_metrics
    assert "conversations_created_total" in registered_metrics
    assert "llm_requests_total" in registered_metrics


def test_metrics_collector_http_request():
    """Test MetricsCollector.record_http_request."""
    from src.monitoring.metrics import MetricsCollector, http_requests_total

    # Get initial value
    initial_value = http_requests_total.labels(
        method="GET", endpoint="/test", status=200
    )._value.get()

    # Record request
    MetricsCollector.record_http_request(
        method="GET",
        endpoint="/test",
        status_code=200,
        duration_seconds=0.5,
    )

    # Verify increment
    new_value = http_requests_total.labels(
        method="GET", endpoint="/test", status=200
    )._value.get()

    assert new_value == initial_value + 1


def test_metrics_collector_conversation():
    """Test MetricsCollector.record_conversation."""
    from src.monitoring.metrics import MetricsCollector, conversations_created_total

    initial_value = conversations_created_total.labels(language="de")._value.get()

    MetricsCollector.record_conversation(
        language="de", duration_seconds=120.5, rounds=4, completed=True
    )

    new_value = conversations_created_total.labels(language="de")._value.get()
    assert new_value == initial_value + 1


def test_metrics_collector_offer_generation():
    """Test MetricsCollector.record_offer_generation."""
    from src.monitoring.metrics import MetricsCollector, offers_generated_total

    initial_value = offers_generated_total.labels(status="generated")._value.get()

    MetricsCollector.record_offer_generation(
        duration_seconds=18.5,
        value_euros=50000.0,
        work_packages=5,
        status="generated",
    )

    new_value = offers_generated_total.labels(status="generated")._value.get()
    assert new_value == initial_value + 1


def test_metrics_collector_llm_request():
    """Test MetricsCollector.record_llm_request."""
    from src.monitoring.metrics import MetricsCollector, llm_requests_total

    initial_value = llm_requests_total.labels(
        model="gpt-4", status="success"
    )._value.get()

    MetricsCollector.record_llm_request(
        model="gpt-4",
        duration_seconds=2.3,
        prompt_tokens=500,
        completion_tokens=300,
        status="success",
    )

    new_value = llm_requests_total.labels(
        model="gpt-4", status="success"
    )._value.get()
    assert new_value == initial_value + 1


def test_get_metrics():
    """Test get_metrics returns Prometheus format."""
    from src.monitoring.metrics import get_metrics, get_metrics_content_type

    metrics = get_metrics()
    content_type = get_metrics_content_type()

    assert isinstance(metrics, bytes)
    assert b"http_requests_total" in metrics
    assert "text/plain" in content_type


@pytest.mark.asyncio
async def test_health_check_endpoints():
    """Test health check endpoints are accessible."""
    from src.api.health import router
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    # Test liveness
    response = client.get("/live")
    assert response.status_code == 200
    assert response.json()["alive"] is True

    # Note: Other health checks may fail without actual dependencies
    # Those should be tested in integration tests


def test_monitor_duration_decorator():
    """Test monitor_duration decorator."""
    from src.monitoring.metrics import monitor_duration, workflow_duration_seconds
    import asyncio

    @monitor_duration(workflow_duration_seconds, workflow_name="test_workflow")
    async def test_async_function():
        await asyncio.sleep(0.1)
        return "result"

    # Run the decorated function
    result = asyncio.run(test_async_function())
    assert result == "result"

    # Note: Verifying the metric was recorded requires inspecting the histogram
    # which is more complex and better suited for integration tests
