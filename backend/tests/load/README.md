# Load Testing for AI Offer Agent

This directory contains Locust load testing scenarios for the AI Offer Agent system.

## Performance Targets

Based on `specs/001-build-an-ai/plan.md`:

- **Offer Generation**: < 30 seconds
- **API Response Time**: < 3 seconds
- **Rate Limit**: 100 requests/minute
- **Concurrent Users**: Support 1000 concurrent users

## Running Load Tests

### Prerequisites

```bash
pip install locust
```

### Basic Load Test

```bash
# Run with default settings
locust -f locustfile.py --host=http://localhost:8000

# Open browser to http://localhost:8089
# Configure: 100 users, spawn rate 10 users/sec
```

### Command Line Testing

```bash
# Test with 100 users, spawn 10/sec, run for 5 minutes
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m --headless

# Stress test with 1000 users
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 10m --headless

# Save results to CSV
locust -f locustfile.py --host=http://localhost:8000 \
  --users 500 --spawn-rate 25 --run-time 10m --headless \
  --csv=results/load_test --html=results/load_test.html
```

### Distributed Load Testing

For very high load, use distributed mode:

```bash
# Start master
locust -f locustfile.py --master --host=http://localhost:8000

# Start workers (on same or different machines)
locust -f locustfile.py --worker --master-host=localhost
locust -f locustfile.py --worker --master-host=localhost
locust -f locustfile.py --worker --master-host=localhost
```

## Test Scenarios

### OfferAgentUser (Main User Flow)

Simulates realistic user behavior:

1. **Create Conversation** (weight: 10)
   - POST /v1/conversations
   - 3-5 rounds of questions
   - POST /v1/conversations/:id/messages

2. **Generate & Retrieve Offer** (weight: 8)
   - POST /v1/offers
   - Validates <30s generation time
   - GET /v1/offers/:id

3. **Download PDF** (weight: 5)
   - POST /v1/offers/:id/download
   - Includes GDPR consent

4. **Approval Workflow** (weight: 2)
   - GET /v1/approvals/pending
   - POST /v1/approvals/:id/review

5. **Health Check** (weight: 1)
   - GET /health

### StressTestUser (Stress Testing)

High-intensity user for testing:
- Rate limiting behavior
- Circuit breaker activation
- System degradation under stress
- Very short wait times (0.1-0.5s)

## Monitoring During Tests

### Real-time Monitoring

1. **Locust Web UI**: http://localhost:8089
   - Request statistics
   - Response times
   - Failure rates
   - Active users

2. **Grafana Dashboard**: http://localhost:3001
   - System metrics
   - Database performance
   - LLM usage
   - Circuit breaker states

3. **Prometheus**: http://localhost:9090
   - Query metrics directly
   - Alert status

### Key Metrics to Watch

```promql
# API response time (should be <3s)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Offer generation time (should be <30s)
histogram_quantile(0.95, rate(offer_generation_duration_seconds_bucket[5m]))

# Error rate
rate(http_errors_total[5m])

# Database connection pool
database_connections_active + database_connections_idle

# Circuit breaker states (should be 0=closed)
circuit_breaker_state
```

## Expected Results

### Success Criteria

- ✅ 95th percentile API response time < 3s
- ✅ 95th percentile offer generation < 30s
- ✅ Error rate < 1%
- ✅ Rate limiting working (429 responses for >100 req/min)
- ✅ System stable under 1000 concurrent users

### Performance Baseline

Example results from a healthy system:

```
Type     Name                                    # reqs    Median    95%ile    Avg
------------------------------------------------------------------------
POST     /v1/conversations [CREATE]              5000      150ms     300ms     180ms
POST     /v1/conversations/:id/messages [ANSWER] 18000     200ms     450ms     250ms
POST     /v1/offers [GENERATE]                   4000      8000ms    25000ms   12000ms
GET      /v1/offers/:id [GET]                    4000      50ms      150ms     75ms
POST     /v1/offers/:id/download [PDF]           2000      500ms     1200ms    650ms
GET      /health [CHECK]                         500       10ms      25ms      12ms
------------------------------------------------------------------------
         Aggregated                              33500     200ms     1500ms    850ms

Success rate: 99.8%
```

## Troubleshooting

### High Error Rates

```bash
# Check application logs
docker-compose logs -f backend

# Check circuit breaker states
curl http://localhost:8000/health/detailed | jq '.checks.circuit_breakers'
```

### Slow Response Times

```bash
# Check database connections
curl http://localhost:8000/health/detailed | jq '.checks.database.pool_details'

# Check for slow queries
curl http://localhost:8000/health/detailed | jq '.checks.database.slow_queries'
```

### Rate Limiting Issues

```bash
# Check Redis connectivity
curl http://localhost:8000/health | jq '.checks.redis'

# Adjust rate limits in .env
# API_RATE_LIMIT=200
# API_RATE_WINDOW_MINUTES=1
```

## Test Data Cleanup

After load testing, clean up test data:

```bash
# Run cleanup script
python scripts/cleanup_test_data.py

# Or manually via psql
psql -U offer_agent -d offer_agent -c "DELETE FROM conversations WHERE customer_id IN (SELECT id FROM customers WHERE email LIKE 'test.user%@example.com');"
```

## CI/CD Integration

### GitHub Actions Example

```yaml
- name: Run Load Tests
  run: |
    locust -f backend/tests/load/locustfile.py \
      --host=http://localhost:8000 \
      --users 100 --spawn-rate 10 --run-time 3m \
      --headless --csv=results/load_test

- name: Check Performance SLA
  run: |
    python scripts/check_performance_sla.py results/load_test_stats.csv
```

## References

- [Locust Documentation](https://docs.locust.io/)
- [Performance Requirements](../../specs/001-build-an-ai/plan.md)
- [Grafana Dashboard](../infrastructure/grafana/dashboards/ai-offer-agent.json)
- [Prometheus Metrics](../src/monitoring/metrics.py)
