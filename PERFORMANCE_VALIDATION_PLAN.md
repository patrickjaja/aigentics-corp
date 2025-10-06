# Performance Validation Plan - AI Offer Agent
**Task**: T100
**Date**: 2025-10-06
**Status**: Ready for Execution

## Performance Targets

| Metric | Target | SLA | Measurement Method |
|--------|--------|-----|-------------------|
| Offer Generation Time | < 30 seconds | p95 | Locust load testing |
| API Response Time | < 3 seconds | p95 | API endpoint monitoring |
| Concurrent Users | 1,000 users | sustained | Load testing |
| API Rate Limit | 100 req/min | per client | Kong Gateway metrics |
| Database Query Time | < 100ms | p95 | PostgreSQL explain analyze |
| Cache Hit Rate | > 80% | average | Redis metrics |
| Error Rate | < 1% | overall | Application logs |

## Test Scenarios

### 1. Offer Generation Performance Test

**Objective**: Validate offer generation completes within 30 seconds under load

**Test Configuration**:
```bash
# locust -f tests/load/locustfile.py --host=http://localhost:8000

Class: OfferGenerationUser
- Spawn rate: 10 users/second
- Target: 100 concurrent users
- Duration: 10 minutes
- Scenarios:
  1. Start conversation
  2. Answer 3-5 questions
  3. Generate offer
  4. Download PDF
```

**Success Criteria**:
- ✅ p50 < 20 seconds
- ✅ p95 < 30 seconds
- ✅ p99 < 40 seconds
- ✅ Error rate < 1%

**Metrics to Collect**:
- LangGraph workflow execution time
- GPT-4 API latency
- Database write operations
- PDF generation time
- Total end-to-end time

### 2. API Endpoint Performance Test

**Objective**: Validate all API endpoints respond within 3 seconds

**Endpoints to Test**:
```yaml
GET /health:
  target: < 100ms
  load: 1000 req/min

POST /v1/conversations:
  target: < 2s
  load: 100 req/min

POST /v1/conversations/{id}/messages:
  target: < 2s
  load: 500 req/min

POST /v1/offers:
  target: < 30s  # Special case - offer generation
  load: 10 req/min

GET /v1/offers/{id}:
  target: < 500ms
  load: 200 req/min

POST /v1/offers/{id}/download:
  target: < 5s  # PDF generation
  load: 50 req/min

GET /v1/admin/approvals/pending:
  target: < 1s
  load: 20 req/min
```

**Test Commands**:
```bash
# Individual endpoint tests with Apache Bench
ab -n 1000 -c 100 http://localhost:8000/health
ab -n 100 -c 10 -p conversation.json http://localhost:8000/v1/conversations

# Or use Locust for comprehensive testing
locust -f tests/load/api_performance.py --users 1000 --spawn-rate 50
```

**Success Criteria**:
- ✅ All endpoints meet target latency
- ✅ No timeout errors
- ✅ Graceful degradation under overload

### 3. Concurrent User Capacity Test

**Objective**: Support 1,000 concurrent active conversations

**Test Phases**:
```
Phase 1: Ramp-up
- 0-100 users: 2 minutes
- 100-500 users: 5 minutes
- 500-1000 users: 10 minutes

Phase 2: Steady State
- 1000 users: 30 minutes
- Monitor: CPU, memory, database connections

Phase 3: Spike Test
- Sudden increase to 1500 users
- Duration: 5 minutes
- Validate graceful degradation

Phase 4: Ramp-down
- 1000 → 0 users: 10 minutes
```

**Resource Monitoring**:
```bash
# Prometheus queries
rate(http_requests_total[1m])
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
process_resident_memory_bytes
postgresql_connections_active
redis_connected_clients
```

**Success Criteria**:
- ✅ System stable at 1000 concurrent users
- ✅ CPU usage < 80%
- ✅ Memory usage < 90%
- ✅ No connection pool exhaustion

### 4. Database Performance Test

**Objective**: Validate database can handle event sourcing load

**Test Queries**:
```sql
-- Event insertion performance
EXPLAIN ANALYZE
INSERT INTO events (aggregate_id, event_type, payload, occurred_at)
VALUES (uuid_generate_v4(), 'OfferCreated', '{}', NOW());

-- Event retrieval performance
EXPLAIN ANALYZE
SELECT * FROM events
WHERE aggregate_id = $1
ORDER BY occurred_at DESC;

-- CQRS projection query performance
EXPLAIN ANALYZE
SELECT * FROM offers_read_model
WHERE customer_id = $1
AND status = 'DRAFT'
ORDER BY created_at DESC
LIMIT 20;
```

**Success Criteria**:
- ✅ Event writes < 10ms
- ✅ Event reads < 50ms
- ✅ Projection queries < 100ms
- ✅ No lock contention

**pgBench Test**:
```bash
pgbench -i offer_agent  # Initialize
pgbench -c 100 -j 4 -t 1000 offer_agent  # Run test
```

### 5. Cache Performance Test

**Objective**: Validate Redis caching effectiveness

**Metrics to Measure**:
```python
# Cache hit rate
cache_hit_rate = cache_hits / (cache_hits + cache_misses)
# Target: > 80%

# Cache response time
# Target: < 5ms
```

**Test Scenarios**:
1. Frequently accessed offers (should hit cache)
2. Conversation context retrieval
3. Session data access
4. Translation cache performance

**Redis Monitoring**:
```bash
redis-cli INFO stats | grep hits
redis-cli --latency-history
redis-cli --bigkeys
```

**Success Criteria**:
- ✅ Hit rate > 80% after warmup
- ✅ Response time < 5ms
- ✅ No memory eviction under load

### 6. External API Performance Test

**Objective**: Measure and optimize GPT-4 API calls

**Metrics**:
```
OpenAI API Latency:
- Token generation: < 1s for first token
- Streaming: < 5s for complete response
- Error rate: < 0.1%

Circuit Breaker:
- Failure threshold: 5 in 60 seconds
- Recovery time: 30 seconds
```

**Test with Mocking**:
```python
# Mock GPT-4 responses to test system without API limits
@mock.patch('openai.ChatCompletion.create')
def test_conversation_performance(mock_gpt):
    mock_gpt.return_value = MockResponse()
    # Measure pure system performance
```

**Success Criteria**:
- ✅ Circuit breaker activates on failures
- ✅ Fallback to GPT-3.5 works
- ✅ Response caching reduces API calls

## Test Execution Plan

### Prerequisites
```bash
# 1. Ensure all services are running
docker-compose ps

# 2. Warm up caches
curl http://localhost:8000/health
curl http://localhost:8000/v1/offers?limit=10

# 3. Reset metrics
curl -X POST http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]={job="offer-agent"}
```

### Execution Steps

**Step 1: Baseline Performance**
```bash
# Run with minimal load
locust -f tests/load/locustfile.py \
  --headless \
  --users 10 \
  --spawn-rate 1 \
  --run-time 5m \
  --html baseline_report.html
```

**Step 2: Target Load Test**
```bash
# Run at target capacity
locust -f tests/load/locustfile.py \
  --headless \
  --users 1000 \
  --spawn-rate 50 \
  --run-time 30m \
  --html target_load_report.html
```

**Step 3: Stress Test**
```bash
# Exceed capacity to find breaking point
locust -f tests/load/locustfile.py \
  --headless \
  --users 2000 \
  --spawn-rate 100 \
  --run-time 10m \
  --html stress_test_report.html
```

**Step 4: Spike Test**
```bash
# Sudden load spike
locust -f tests/load/spike_test.py \
  --headless \
  --step-load \
  --html spike_test_report.html
```

**Step 5: Soak Test**
```bash
# Extended duration test
locust -f tests/load/locustfile.py \
  --headless \
  --users 500 \
  --spawn-rate 25 \
  --run-time 4h \
  --html soak_test_report.html
```

### Monitoring During Tests

**Grafana Dashboards**:
- http://localhost:3001 (admin/admin)
- Monitor:
  - Request rate
  - Response times (p50, p95, p99)
  - Error rates
  - Resource utilization

**Prometheus Queries**:
```promql
# Request rate
rate(http_requests_total[1m])

# Response time p95
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Error rate
rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m])
```

## Performance Optimization Checklist

### If Offer Generation > 30s:
- [ ] Enable GPT-4 response caching
- [ ] Optimize LangGraph workflow steps
- [ ] Parallelize independent operations
- [ ] Use GPT-3.5 for non-critical questions
- [ ] Implement background job processing

### If API Response > 3s:
- [ ] Add database query indexes
- [ ] Increase Redis cache TTL
- [ ] Enable connection pooling
- [ ] Optimize serialization (use orjson)
- [ ] Implement response compression

### If Concurrent Users < 1000:
- [ ] Scale horizontally (add instances)
- [ ] Increase database connection pool
- [ ] Optimize Redis memory usage
- [ ] Review async/await patterns
- [ ] Check for blocking operations

### If Database Slow:
- [ ] Add missing indexes
- [ ] Optimize event store partitioning
- [ ] Increase PostgreSQL work_mem
- [ ] Enable query result caching
- [ ] Consider read replicas

## Test Data Requirements

**Generate Test Data**:
```bash
# Create 1000 test customers
python scripts/generate_test_data.py --customers 1000

# Create 500 test offers
python scripts/generate_test_data.py --offers 500

# Create conversation templates
python scripts/generate_test_data.py --conversations 100
```

## Success Report Template

```markdown
# Performance Test Results

**Date**: YYYY-MM-DD
**Duration**: X hours
**Peak Users**: X concurrent

## Metrics Achieved

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Offer Generation (p95) | < 30s | Xs | ✅/❌ |
| API Response (p95) | < 3s | Xs | ✅/❌ |
| Concurrent Users | 1000 | X | ✅/❌ |
| Error Rate | < 1% | X% | ✅/❌ |
| Cache Hit Rate | > 80% | X% | ✅/❌ |

## Bottlenecks Identified
1. [Component]: [Issue]
2. [Component]: [Issue]

## Optimizations Applied
1. [Change]: [Impact]
2. [Change]: [Impact]

## Production Readiness
- ✅/❌ Meets all performance targets
- ✅/❌ No critical bottlenecks
- ✅/❌ Graceful degradation under load
- ✅/❌ Monitoring and alerting validated

## Recommendation
[READY / NOT READY] for production deployment
```

## Next Steps After Validation

1. **If Tests Pass**:
   - Document performance baselines
   - Set up production monitoring
   - Configure auto-scaling rules
   - Schedule regular performance testing

2. **If Tests Fail**:
   - Identify root causes
   - Apply optimizations
   - Re-test specific scenarios
   - Update architecture if needed

## Tools and Resources

**Load Testing**:
- Locust: https://locust.io
- Apache Bench (ab)
- Hey: https://github.com/rakyll/hey

**Monitoring**:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001
- Redis CLI: `redis-cli`
- PostgreSQL: `pgAdmin`

**Analysis**:
- Locust HTML reports
- Prometheus query browser
- Grafana explore mode
- PostgreSQL EXPLAIN ANALYZE

---

**Status**: Ready for execution
**Estimated Duration**: 8-12 hours
**Prerequisites**: All services running, test data generated

*Performance Validation Plan - Task T100*
