# Monitoring & Performance

Comprehensive monitoring and performance tracking for the AI Offer Agent system.

## Overview

This module provides:
- **Prometheus metrics** - HTTP, business, LLM, system metrics
- **Health checks** - Database, Redis, Qdrant, OpenAI connectivity
- **Performance monitoring** - Track SLA compliance (<30s offers, <3s API)
- **Grafana dashboards** - Visual monitoring and alerting

## Quick Start

### 1. Start Monitoring Stack

```bash
# Start Prometheus and Grafana
docker-compose up -d prometheus grafana

# Verify services
curl http://localhost:9090/-/healthy  # Prometheus
curl http://localhost:3001/api/health # Grafana
```

### 2. Access Dashboards

- **Grafana**: http://localhost:3001
  - Username: admin
  - Password: admin (from .env: GRAFANA_PASSWORD)
  - Dashboard: "AI Offer Agent - System Monitoring"

- **Prometheus**: http://localhost:9090
  - Query metrics directly
  - View targets and alerts

### 3. Check Application Health

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health (includes DB pool, slow queries, circuit breakers)
curl http://localhost:8000/health/detailed | jq

# Kubernetes probes
curl http://localhost:8000/ready  # Readiness
curl http://localhost:8000/live   # Liveness

# Prometheus metrics
curl http://localhost:8000/metrics
```

## Metrics Collection

### HTTP Metrics

```python
from monitoring import MetricsCollector

# Record HTTP request
MetricsCollector.record_http_request(
    method="POST",
    endpoint="/v1/offers",
    status_code=201,
    duration_seconds=12.5,
    request_size=1024,
    response_size=2048
)
```

### Business Metrics

```python
# Record conversation
MetricsCollector.record_conversation(
    language="de",
    duration_seconds=180.5,
    rounds=4,
    completed=True
)

# Record offer generation
MetricsCollector.record_offer_generation(
    duration_seconds=18.2,
    value_euros=75000.0,
    work_packages=5,
    status="generated"
)
```

### LLM Metrics

```python
# Record LLM request
MetricsCollector.record_llm_request(
    model="gpt-4",
    duration_seconds=2.3,
    prompt_tokens=850,
    completion_tokens=420,
    status="success"
)
```

### Workflow Metrics

```python
from monitoring import monitor_duration, workflow_duration_seconds

# Decorator approach
@monitor_duration(workflow_duration_seconds, workflow_name="offer_generation")
async def generate_offer():
    # ... implementation
    pass

# Manual approach
MetricsCollector.record_workflow_execution(
    workflow_name="conversation_flow",
    duration_seconds=45.2,
    status="completed"
)
```

## Available Metrics

### HTTP Metrics
- `http_requests_total` - Total requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `http_request_size_bytes` - Request body size
- `http_response_size_bytes` - Response body size
- `http_errors_total` - Error count by type

### Business Metrics
- `conversations_created_total` - Conversations by language
- `conversations_completed_total` - Completed conversations
- `conversation_duration_seconds` - Time to completion
- `conversation_rounds_total` - Question rounds per conversation
- `offers_generated_total` - Offers by status
- `offer_generation_duration_seconds` - Generation time (SLA: <30s)
- `offer_value_euros` - Offer value distribution
- `offers_downloaded_total` - PDF downloads
- `approvals_created_total` - Approval workflows
- `approvals_completed_total` - Approvals by decision

### LLM Metrics
- `llm_requests_total` - LLM API calls by model
- `llm_request_duration_seconds` - LLM response time
- `llm_tokens_total` - Token usage (prompt/completion)
- `llm_cost_euros` - Estimated costs

### System Metrics
- `database_connections_active` - Active DB connections
- `database_connections_idle` - Idle connections in pool
- `database_query_duration_seconds` - Query execution time
- `redis_operations_total` - Redis operations
- `redis_operation_duration_seconds` - Redis latency
- `qdrant_search_duration_seconds` - Vector search time
- `circuit_breaker_state` - Circuit breaker states (0=closed, 1=half_open, 2=open)
- `circuit_breaker_failures_total` - Circuit breaker failures

## Health Checks

### Endpoints

**GET /health** - Comprehensive health check
```json
{
  "status": "healthy",
  "timestamp": "2025-10-06T14:30:00Z",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 3600.5,
  "checks": {
    "database": {
      "status": "healthy",
      "response_time_ms": 2.5,
      "pool": {
        "size": 20,
        "checked_in": 15,
        "checked_out": 5
      }
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1.2,
      "version": "7.0.0"
    },
    "qdrant": {
      "status": "healthy",
      "response_time_ms": 15.3,
      "collections": 1
    },
    "openai": {
      "status": "healthy",
      "response_time_ms": 250.1,
      "model_available": true
    },
    "circuit_breakers": {
      "status": "healthy",
      "open_breakers": []
    }
  }
}
```

**GET /ready** - Kubernetes readiness probe
```json
{
  "ready": true,
  "timestamp": "2025-10-06T14:30:00Z",
  "dependencies": {
    "database": "connected",
    "redis": "connected",
    "qdrant": "connected",
    "openai": "available"
  },
  "degraded_services": []
}
```

**GET /live** - Kubernetes liveness probe
```json
{
  "alive": true,
  "timestamp": "2025-10-06T14:30:00Z"
}
```

**GET /health/detailed** - Extended diagnostics
- Includes slow query analysis
- Circuit breaker detailed states
- Connection pool statistics

## Performance SLAs

### Targets (from plan.md)

- ✅ **Offer Generation**: < 30 seconds (95th percentile)
- ✅ **API Response Time**: < 3 seconds (95th percentile)
- ✅ **Concurrent Users**: 1000 simultaneous users
- ✅ **Rate Limit**: 100 requests/minute per API key

### Monitoring SLA Compliance

Metrics automatically log warnings when SLAs are violated:

```python
# In metrics.py
if duration_seconds > 3.0:
    logger.warning(f"SLA violation: API response {duration_seconds:.2f}s (>3s)")

if duration_seconds > 30:
    logger.warning(f"Offer generation SLA violation: {duration_seconds:.2f}s (>30s)")
```

### Grafana Alerts

Dashboard includes alerts for:
- API response time > 3s (5-minute average)
- Offer generation > 30s (95th percentile)
- Error rate > 10/sec
- Open circuit breakers

## Prometheus Queries

### Common Queries

```promql
# 95th percentile API response time
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Offer generation performance
histogram_quantile(0.95, rate(offer_generation_duration_seconds_bucket[5m]))

# Error rate per endpoint
rate(http_errors_total[5m])

# LLM cost per hour
rate(llm_cost_euros[1h])

# Database connection utilization
database_connections_active / (database_connections_active + database_connections_idle)

# Circuit breaker open count
count(circuit_breaker_state == 2)

# Successful offers per hour
rate(offers_generated_total{status="generated"}[1h]) * 3600
```

### Alerting Rules

See `infrastructure/prometheus/alerts.yml` for configured alerts.

## Grafana Dashboard

### Dashboard Panels

1. **HTTP Performance**
   - Request rate
   - Response time (95th percentile)
   - Error rate

2. **Business Metrics**
   - Offer generation time
   - Offers generated/hour
   - Conversation flow

3. **LLM Usage**
   - Request duration
   - Token usage
   - Cost tracking

4. **System Health**
   - Database connections
   - Redis latency
   - Qdrant search time
   - Circuit breaker states

### Custom Dashboard

Import `infrastructure/grafana/dashboards/ai-offer-agent.json` or create custom:

1. Go to Grafana → Dashboards → Import
2. Upload JSON or paste content
3. Select Prometheus datasource
4. Save

## Integration Examples

### FastAPI Middleware

```python
from monitoring import MetricsCollector
from fastapi import Request
import time

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    MetricsCollector.record_http_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code,
        duration_seconds=duration
    )

    return response
```

### LangGraph Integration

```python
from monitoring import workflow_duration_seconds, workflow_step_duration_seconds

class OfferGenerationWorkflow:
    async def execute(self):
        start_time = time.time()

        try:
            # ... workflow steps

            duration = time.time() - start_time
            workflow_duration_seconds.labels(
                workflow_name="offer_generation"
            ).observe(duration)

        except Exception as e:
            workflow_errors_total.labels(
                workflow_name="offer_generation",
                error_type=type(e).__name__
            ).inc()
            raise
```

## Troubleshooting

### High Response Times

```bash
# Check slow queries
curl http://localhost:8000/health/detailed | jq '.checks.database.slow_queries'

# Check database pool
curl http://localhost:8000/health/detailed | jq '.checks.database.pool_details'

# Review Grafana dashboard
# Look for: DB query duration, connection pool usage
```

### Circuit Breakers Opening

```bash
# Check circuit breaker states
curl http://localhost:8000/health | jq '.checks.circuit_breakers'

# Reset circuit breakers (if needed)
# This would require admin API endpoint
```

### Missing Metrics

```bash
# Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Check application metrics endpoint
curl http://localhost:8000/metrics | grep http_requests_total

# Verify Grafana datasource
# Grafana → Configuration → Data Sources → Prometheus → Test
```

## Best Practices

1. **Use decorators** for automatic metric collection
2. **Log SLA violations** for quick identification
3. **Monitor circuit breakers** to detect service degradation
4. **Track costs** especially LLM token usage
5. **Set up alerts** for critical metrics
6. **Review dashboards** during load testing
7. **Analyze slow queries** regularly

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Load Testing Guide](../../tests/load/README.md)
- [Performance Requirements](../../../specs/001-build-an-ai/plan.md)
