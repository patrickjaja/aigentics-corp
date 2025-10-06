# Monitoring Quick Start Guide

## 🚀 Getting Started (3 minutes)

### 1. Start Monitoring Stack

```bash
# From project root
docker-compose up -d prometheus grafana

# Verify services are running
docker-compose ps prometheus grafana
```

### 2. Access Dashboards

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **API Metrics** | http://localhost:8000/metrics | - |
| **Health Check** | http://localhost:8000/health | - |

### 3. Import Grafana Dashboard

1. Open Grafana: http://localhost:3001
2. Go to **Dashboards** → **Import**
3. Upload file: `backend/infrastructure/grafana/dashboards/ai-offer-agent.json`
4. Select **Prometheus** datasource
5. Click **Import**

You now have a complete monitoring dashboard! 🎉

---

## 📊 Key Metrics to Watch

### Performance SLAs

```bash
# Check if API is meeting <3s response time
curl -s http://localhost:8000/metrics | grep 'http_request_duration_seconds' | grep '0.95'

# Check if offer generation is <30s
curl -s http://localhost:8000/metrics | grep 'offer_generation_duration_seconds' | grep '0.95'
```

### Health Checks

```bash
# Quick health check
curl http://localhost:8000/health | jq '.status'

# Detailed health with DB pool, slow queries
curl http://localhost:8000/health/detailed | jq

# Kubernetes readiness
curl http://localhost:8000/ready

# Kubernetes liveness
curl http://localhost:8000/live
```

### Top Prometheus Queries

```promql
# 95th percentile API response time (target: <3s)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Offer generation time (target: <30s)
histogram_quantile(0.95, rate(offer_generation_duration_seconds_bucket[5m]))

# Requests per second
rate(http_requests_total[5m])

# Error rate
rate(http_errors_total[5m])

# LLM cost per hour
rate(llm_cost_euros[1h]) * 3600

# Database connection utilization
database_connections_active / (database_connections_active + database_connections_idle)

# Open circuit breakers (should be 0)
count(circuit_breaker_state == 2)
```

---

## 🧪 Running Load Tests

### Basic Load Test (100 users)

```bash
cd backend/tests/load

# Interactive mode (Web UI)
locust -f locustfile.py --host=http://localhost:8000
# Open http://localhost:8089 and configure users

# Headless mode
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Stress Test (1000 users)

```bash
locust -f locustfile.py --host=http://localhost:8000 \
  --users 1000 --spawn-rate 50 --run-time 10m --headless \
  --csv=results/stress_test --html=results/stress_test.html
```

### Watch Metrics During Load Test

```bash
# Terminal 1: Run load test
locust -f locustfile.py --host=http://localhost:8000 --users 500 --spawn-rate 25

# Terminal 2: Monitor health
watch -n 2 'curl -s http://localhost:8000/health | jq ".checks | {db: .database.status, redis: .redis.status, breakers: .circuit_breakers.open_breakers}"'

# Terminal 3: Monitor metrics
watch -n 2 'curl -s http://localhost:8000/metrics | grep -E "(http_requests_total|offer_generation_duration)" | tail -5'
```

---

## 🔍 Troubleshooting

### High Response Times

```bash
# Check database pool
curl http://localhost:8000/health/detailed | jq '.checks.database.pool_details'

# Check slow queries
curl http://localhost:8000/health/detailed | jq '.checks.database.slow_queries'

# Grafana: Go to "Database Query Duration" panel
```

### Circuit Breakers Opening

```bash
# Check circuit breaker states
curl http://localhost:8000/health | jq '.checks.circuit_breakers'

# Expected output:
# {
#   "status": "healthy",
#   "open_breakers": [],  # Should be empty
#   "total_breakers": 3
# }

# If open_breakers is not empty, check which services:
curl http://localhost:8000/health/detailed | jq '.checks.circuit_breakers.detailed_states'
```

### High Error Rates

```bash
# Check error metrics
curl -s http://localhost:8000/metrics | grep http_errors_total

# Check application logs
docker-compose logs -f backend | grep ERROR
```

### Missing Metrics in Grafana

```bash
# 1. Verify Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# 2. Check metrics endpoint
curl http://localhost:8000/metrics | head -50

# 3. Test Prometheus datasource in Grafana
# Grafana → Configuration → Data Sources → Prometheus → Test
```

---

## 📈 Understanding the Dashboard

### Top Row: HTTP Performance
- **HTTP Request Rate**: Requests/sec by endpoint
- **HTTP Request Duration**: Response time (95th percentile) - **Alert if >3s**

### Second Row: Business Metrics
- **Offer Generation Duration**: Generation time - **Alert if >30s**
- **Offers Generated**: Offers/hour, Downloads/hour

### Third Row: Conversations & LLM
- **Conversation Metrics**: Creation/completion rates
- **LLM Request Duration**: AI response times

### Fourth Row: LLM Usage
- **LLM Token Usage**: Tokens/sec by model
- **LLM Cost**: EUR/hour spending

### Fifth Row: Database
- **Connection Pool**: Active vs idle connections
- **Query Duration**: Database query performance

### Sixth Row: System Health
- **Circuit Breakers**: Service health (green=healthy, red=open)
- **Error Rate**: Errors/sec - **Alert if >10**

### Bottom Rows: Advanced Metrics
- Workflow execution times
- Redis performance
- Qdrant vector search
- System uptime

---

## 🎯 Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| API Response (95%ile) | < 3s | Check dashboard | ⏱️ |
| Offer Generation (95%ile) | < 30s | Check dashboard | ⏱️ |
| Concurrent Users | 1000 | Test with Locust | 🧪 |
| Rate Limit | 100/min | Working | ✅ |
| Error Rate | < 1% | Check dashboard | 📊 |

---

## 🔗 Useful Links

- **Load Testing Guide**: `backend/tests/load/README.md`
- **Monitoring Guide**: `backend/src/monitoring/README.md`
- **Implementation Summary**: `backend/PERFORMANCE_MONITORING.md`
- **Plan Requirements**: `specs/001-build-an-ai/plan.md`

---

## 💡 Quick Tips

1. **Always check health before load testing**
   ```bash
   curl http://localhost:8000/health | jq '.status'
   # Should be "healthy"
   ```

2. **Monitor during deployments**
   - Check `/ready` endpoint
   - Watch circuit breaker states
   - Review error rates

3. **Set up alerts**
   - Configure Grafana alert rules
   - Set up notification channels (Slack, email)
   - Test alert delivery

4. **Regular maintenance**
   - Review slow queries weekly
   - Analyze LLM costs monthly
   - Update dashboard as needed

5. **Load test before production**
   - Run 1000-user test
   - Verify all SLAs met
   - Check resource usage

---

**Need help?** See the detailed guides:
- `backend/src/monitoring/README.md` - Comprehensive monitoring guide
- `backend/tests/load/README.md` - Load testing details
- `backend/PERFORMANCE_MONITORING.md` - Implementation documentation
