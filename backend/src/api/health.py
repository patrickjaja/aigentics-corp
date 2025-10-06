"""Health check endpoints for monitoring and orchestration.

This module provides comprehensive health checks for:
- Database connectivity (PostgreSQL)
- Redis cache availability
- Qdrant vector database
- OpenAI API access
- Circuit breaker states
- Overall system health

Used by:
- Load balancers for routing decisions
- Kubernetes liveness/readiness probes
- Monitoring systems (Prometheus, Grafana)
- CI/CD pipelines for deployment validation
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from ..infrastructure.circuit_breaker import get_circuit_breaker_registry
from ..monitoring.metrics import (
    get_metrics,
    get_metrics_content_type,
    MetricsCollector,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


# ============================================================================
# Response Models
# ============================================================================

class HealthStatus(BaseModel):
    """Health check response model."""

    status: str  # healthy, degraded, unhealthy
    timestamp: str
    version: str
    environment: str
    uptime_seconds: float
    checks: Dict[str, Dict[str, Any]]


class ReadinessStatus(BaseModel):
    """Readiness check response model."""

    ready: bool
    timestamp: str
    dependencies: Dict[str, str]
    degraded_services: list[str]


class LivenessStatus(BaseModel):
    """Liveness check response model."""

    alive: bool
    timestamp: str


# ============================================================================
# Global State
# ============================================================================

_startup_time: Optional[datetime] = None


def set_startup_time():
    """Set application startup time."""
    global _startup_time
    _startup_time = datetime.utcnow()


# ============================================================================
# Health Check Functions
# ============================================================================

async def check_database() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity.

    Returns:
        Dictionary with status and details
    """
    try:
        from sqlalchemy import text
        from ..infrastructure.optimization import _optimizer

        if not _optimizer or not _optimizer.engine:
            return {
                "status": "unhealthy",
                "message": "Database not initialized",
                "response_time_ms": 0,
            }

        start_time = asyncio.get_event_loop().time()

        async with _optimizer.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))

        response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        # Get connection pool status
        pool_status = _optimizer.get_pool_status()

        return {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2),
            "pool": pool_status,
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "response_time_ms": 0,
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity.

    Returns:
        Dictionary with status and details
    """
    try:
        import redis.asyncio as redis

        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url, decode_responses=True)

        start_time = asyncio.get_event_loop().time()

        # Ping Redis
        await client.ping()

        response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        # Get Redis info
        info = await client.info("server")

        await client.close()

        return {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2),
            "version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds"),
        }

    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "response_time_ms": 0,
        }


async def check_qdrant() -> Dict[str, Any]:
    """Check Qdrant vector database connectivity.

    Returns:
        Dictionary with status and details
    """
    try:
        from qdrant_client import AsyncQdrantClient

        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        client = AsyncQdrantClient(host=qdrant_host, port=qdrant_port)

        start_time = asyncio.get_event_loop().time()

        # Get cluster info
        collections = await client.get_collections()

        response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "offer_requirements")
        collection_exists = any(
            col.name == collection_name for col in collections.collections
        )

        return {
            "status": "healthy",
            "response_time_ms": round(response_time_ms, 2),
            "collections": len(collections.collections),
            "collection_exists": collection_exists,
        }

    except Exception as e:
        logger.error(f"Qdrant health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": str(e),
            "response_time_ms": 0,
        }


async def check_openai() -> Dict[str, Any]:
    """Check OpenAI API accessibility.

    Returns:
        Dictionary with status and details
    """
    try:
        from openai import AsyncOpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            return {
                "status": "degraded",
                "message": "OpenAI API key not configured",
                "response_time_ms": 0,
            }

        client = AsyncOpenAI(api_key=api_key)

        start_time = asyncio.get_event_loop().time()

        # List available models (lightweight check)
        models = await client.models.list()

        response_time_ms = (asyncio.get_event_loop().time() - start_time) * 1000

        # Check if required model is available
        required_model = os.getenv("OPENAI_MODEL", "gpt-4")
        model_available = any(model.id == required_model for model in models.data)

        return {
            "status": "healthy" if model_available else "degraded",
            "response_time_ms": round(response_time_ms, 2),
            "model_available": model_available,
            "models_count": len(models.data),
        }

    except Exception as e:
        logger.error(f"OpenAI health check failed: {e}")
        return {
            "status": "degraded",  # Not critical, system can degrade gracefully
            "message": str(e),
            "response_time_ms": 0,
        }


async def check_circuit_breakers() -> Dict[str, Any]:
    """Check circuit breaker states.

    Returns:
        Dictionary with circuit breaker statuses
    """
    try:
        registry = get_circuit_breaker_registry()
        states = registry.get_all_states()
        open_breakers = registry.get_open_breakers()

        return {
            "status": "healthy" if not open_breakers else "degraded",
            "open_breakers": open_breakers,
            "total_breakers": len(states),
            "breakers": states,
        }

    except Exception as e:
        logger.error(f"Circuit breaker check failed: {e}")
        return {
            "status": "unknown",
            "message": str(e),
        }


# ============================================================================
# Health Check Endpoints
# ============================================================================

@router.get("/health", response_model=HealthStatus)
async def health_check():
    """Comprehensive health check endpoint.

    Returns system health status including all dependencies.
    Used by monitoring systems to track overall health.

    Returns:
        HealthStatus with detailed check results
    """
    checks = await asyncio.gather(
        check_database(),
        check_redis(),
        check_qdrant(),
        check_openai(),
        check_circuit_breakers(),
        return_exceptions=True,
    )

    check_results = {
        "database": checks[0] if not isinstance(checks[0], Exception) else {
            "status": "unhealthy", "message": str(checks[0])
        },
        "redis": checks[1] if not isinstance(checks[1], Exception) else {
            "status": "unhealthy", "message": str(checks[1])
        },
        "qdrant": checks[2] if not isinstance(checks[2], Exception) else {
            "status": "unhealthy", "message": str(checks[2])
        },
        "openai": checks[3] if not isinstance(checks[3], Exception) else {
            "status": "degraded", "message": str(checks[3])
        },
        "circuit_breakers": checks[4] if not isinstance(checks[4], Exception) else {
            "status": "unknown", "message": str(checks[4])
        },
    }

    # Determine overall status
    unhealthy_count = sum(
        1 for check in check_results.values()
        if isinstance(check, dict) and check.get("status") == "unhealthy"
    )
    degraded_count = sum(
        1 for check in check_results.values()
        if isinstance(check, dict) and check.get("status") == "degraded"
    )

    if unhealthy_count > 0:
        overall_status = "unhealthy"
    elif degraded_count > 0:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Calculate uptime
    uptime_seconds = 0.0
    if _startup_time:
        uptime_seconds = (datetime.utcnow() - _startup_time).total_seconds()

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version=os.getenv("API_VERSION", "1.0.0"),
        environment=os.getenv("ENVIRONMENT", "development"),
        uptime_seconds=uptime_seconds,
        checks=check_results,
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check():
    """Readiness probe for Kubernetes.

    Indicates whether the application is ready to serve traffic.
    Returns 200 if ready, 503 if not ready.

    Returns:
        ReadinessStatus indicating readiness state
    """
    # Check critical dependencies (DB, Redis)
    db_check, redis_check = await asyncio.gather(
        check_database(),
        check_redis(),
        return_exceptions=True,
    )

    dependencies = {}
    degraded_services = []

    # Database check (critical)
    if isinstance(db_check, Exception) or db_check.get("status") != "healthy":
        dependencies["database"] = "unavailable"
        degraded_services.append("database")
    else:
        dependencies["database"] = "connected"

    # Redis check (critical)
    if isinstance(redis_check, Exception) or redis_check.get("status") != "healthy":
        dependencies["redis"] = "unavailable"
        degraded_services.append("redis")
    else:
        dependencies["redis"] = "connected"

    # Qdrant check (non-critical, can degrade gracefully)
    try:
        qdrant_check = await check_qdrant()
        dependencies["qdrant"] = "connected" if qdrant_check.get("status") == "healthy" else "degraded"
        if qdrant_check.get("status") != "healthy":
            degraded_services.append("qdrant")
    except Exception:
        dependencies["qdrant"] = "degraded"
        degraded_services.append("qdrant")

    # OpenAI check (non-critical, can degrade gracefully)
    try:
        openai_check = await check_openai()
        dependencies["openai"] = "available" if openai_check.get("status") == "healthy" else "degraded"
        if openai_check.get("status") != "healthy":
            degraded_services.append("openai")
    except Exception:
        dependencies["openai"] = "degraded"
        degraded_services.append("openai")

    # Ready if critical services are available
    ready = not any(
        service in ["database", "redis"]
        for service in degraded_services
    )

    return ReadinessStatus(
        ready=ready,
        timestamp=datetime.utcnow().isoformat(),
        dependencies=dependencies,
        degraded_services=degraded_services,
    )


@router.get("/live", response_model=LivenessStatus)
async def liveness_check():
    """Liveness probe for Kubernetes.

    Indicates whether the application is alive and running.
    Should always return 200 unless the application is completely broken.

    Returns:
        LivenessStatus indicating the application is alive
    """
    return LivenessStatus(
        alive=True,
        timestamp=datetime.utcnow().isoformat(),
    )


@router.get("/metrics")
async def metrics_endpoint():
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus text format for scraping.

    Returns:
        Response with Prometheus metrics
    """
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type(),
    )


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with additional diagnostics.

    Returns extended health information including:
    - Response times for all services
    - Connection pool statistics
    - Circuit breaker states
    - Recent error counts

    Returns:
        Detailed health information
    """
    health = await health_check()

    # Add database pool statistics
    from ..infrastructure.optimization import _optimizer
    if _optimizer:
        pool_stats = _optimizer.get_pool_status()
        query_stats = _optimizer.get_query_stats()

        health.checks["database"]["pool_details"] = pool_stats
        health.checks["database"]["slow_queries"] = {
            query: stats
            for query, stats in query_stats.items()
            if stats.get("avg_time_ms", 0) > 1000
        }

    # Add circuit breaker details
    registry = get_circuit_breaker_registry()
    health.checks["circuit_breakers"]["detailed_states"] = registry.get_all_states()

    return health


# ============================================================================
# Startup Hook
# ============================================================================

def initialize_health_checks():
    """Initialize health check system."""
    set_startup_time()
    logger.info("Health check system initialized")
