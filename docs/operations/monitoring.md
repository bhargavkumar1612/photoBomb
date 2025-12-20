# Monitoring, Logging & SLOs

## Metrics to Collect

### Application Metrics (Prometheus/Datadog)

**API Latency**:
```promql
histogram_quantile(0.95, 
  rate(http_request_duration_seconds_bucket[5m])
) by (endpoint, method)
```
- **SLO**: p95 < 200ms for GET, p95 < 500ms for POST
- **Alert**: p95 > 500ms for 5 minutes

**Error Rate**:
```promql
rate(http_requests_total{status=~"5.."}[5m]) / 
rate(http_requests_total[5m])
```
- **SLO**: < 0.1% (99.9% success rate)
- **Alert**: > 1% for 5 minutes

**Queue Depth** (Redis/Celery):
```promql
celery_queue_length{queue="high"}
```
- **SLO**: < 50 jobs in high-priority queue
- **Alert**: > 100 for 10 minutes → trigger HPA

**Processing Duration**:
```promql
histogram_quantile(0.95,
  rate(worker_job_duration_seconds_bucket{job_type="thumbnail"}[5m])
)
```
- **SLO**: p95 < 30 seconds
- **Alert**: p95 > 60 seconds

**Database Connections**:
```promql
pg_stat_activity_count
```
- **SLO**: < 150 connections (out of 200 max)
- **Alert**: > 180 for 5 minutes

**Storage Usage** (per user):
```sql
SELECT user_id, SUM(size_bytes) as used_bytes
FROM photos
WHERE deleted_at IS NULL
GROUP BY user_id
HAVING SUM(size_bytes) > storage_quota_bytes;
```
- **Alert**: User within 10% of quota → email warning

### Infrastructure Metrics

**CPU Usage** (GKE):
```promql
avg(rate(container_cpu_usage_seconds_total{namespace="photobomb"}[5m])) * 100
```
- **Alert**: > 80% for 15 minutes

**Memory Usage**:
```promql
container_memory_working_set_bytes{namespace="photobomb"} / 
container_spec_memory_limit_bytes
```
- **Alert**: > 85%

**B2 API Errors**:
```promql
rate(b2_api_errors_total[5m])
```
- **Alert**: > 1% error rate

### Business Metrics

**Daily Active Users**:
```sql
SELECT COUNT(DISTINCT user_id) 
FROM audit_logs 
WHERE created_at > NOW() - INTERVAL '24 hours';
```

**Upload Success Rate**:
```sql
SELECT 
  COUNT(*) FILTER (WHERE status = 'completed') * 100.0 / COUNT(*) as success_rate
FROM upload_sessions
WHERE created_at > NOW() - INTERVAL '1 day';
```

**Storage Growth**:
```sql
SELECT DATE(uploaded_at) as day, SUM(size_bytes) / 1099511627776.0 as tb_uploaded
FROM photos
WHERE uploaded_at > NOW() - INTERVAL '30 days'
GROUP BY DATE(uploaded_at)
ORDER BY day;
```

## Logging Strategy

**Log Levels**:
- ERROR: Unhandled exceptions, critical failures
- WARN: Retryable errors, deprecated API usage
- INFO: Request logs, job completion
- DEBUG: Detailed execution flow (disabled in prod)

**Structured Logging (JSON)**:
```python
import structlog

logger = structlog.get_logger()

@app.get('/api/v1/photos/{photo_id}')
async def get_photo(photo_id: str):
    logger.info('photo_request', photo_id=photo_id, user_id=user_id)
    # ...
```

**Example Log**:
```json
{
  "timestamp": "2024-12-10T22:00:00Z",
  "level": "info",
  "event": "photo_request",
  "photo_id": "uuid",
  "user_id": "uuid",
  "latency_ms": 45,
  "status_code": 200
}
```

**Centralized Logging**:
- **Cloud Logging** (GCP native) or **Datadog Logs**
- **Retention**: 30 days (hot), 1 year (archive in Cloud Storage)

**Log Sampling**:
- INFO logs: 10% sampling in production (to reduce cost)
- ERROR/WARN: 100% (never sample errors)

## Dashboards

### API Health Dashboard (Grafana)

**Panels**:
1. Request Rate (req/sec) - Time series
2. Latency (p50, p95, p99) - Time series
3. Error Rate (5xx, 4xx) - Time series
4. Top Endpoints by Volume - Bar chart
5. Slowest Endpoints (p95 latency) - Table

### Worker Dashboard

**Panels**:
1. Queue Depth by Priority - Stacked area
2. Job Processing Rate (jobs/min) - Time series
3. Job Success/Failure Rate - Pie chart
4. Worker CPU/Memory - Heatmap
5. Processing Duration (p95) by Job Type - Time series

### Database Dashboard

**Panels**:
1. Connection Count - Time series
2. Query Duration (p95) - Time series
3. Cache Hit Ratio - Gauge
4. Deadlocks/Slow Queries - Counter
5. Replication Lag (if read replica) - Time series

### Business Dashboard

**Panels**:
1. Daily Active Users - Time series
2. New Sign-ups - Time series
3. Photos Uploaded (per day) - Bar chart
4. Storage Used (total TB) - Gauge
5. Share Links Created - Time series

## Alerts & Notification Channels

### Critical Alerts (PagerDuty)

| Alert | Condition | Action |
|-------|-----------|--------|
| API Down | 0 healthy instances for 2 min | Page on-call engineer |
| Database Down | Connection failures > 50% for 2 min | Page on-call + DB admin |
| Storage Full | > 95% disk usage | Page on-call |
| Error Spike | Error rate > 5% for 5 min | Page on-call |

### Warning Alerts (Slack #alerts)

| Alert | Condition |
|-------|-----------|
| High Queue Depth | > 100 jobs for 10 min |
| Slow Queries | p95 query time > 1s for 5 min |
| Certificate Expiry | TLS cert expires within 7 days |
| Low Quota | User within 10% of storage quota |

### Info Alerts (Slack #monitoring)

| Alert | Condition |
|-------|-----------|
| Deployment Complete | New version deployed |
| Auto-scaling Event | GKE nodes scaled up/down |
| Backup Complete | Daily backup succeeded |

## SLOs (Service Level Objectives)

### Availability SLO

**Target**: 99.9% uptime (43.8 minutes downtime/month)

**Measurement**:
```promql
(sum(http_requests_total{status!~"5.."}) / sum(http_requests_total)) * 100
```

**Error Budget**: 0.1% (if breached, freeze feature releases until fixed)

### Latency SLO

**Target**: 95% of API requests < 500ms

**Measurement**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Processing SLO

**Target**: 95% of photos processed within 60 seconds of upload

**Measurement**:
```sql
SELECT 
  COUNT(*) FILTER (WHERE processed_at - uploaded_at < INTERVAL '60 seconds') * 100.0 / COUNT(*)
FROM photos
WHERE uploaded_at > NOW() - INTERVAL '1 day';
```

### Data Durability SLO

**Target**: 99.999999999% (11 nines, same as B2)

**Measurement**: Track object loss incidents (should be zero)

## Runbook Templates

### API High Error Rate

**Symptoms**: Spike in 5xx errors, users report failures

**Investigation**:
1. Check API dashboard for affected endpoints
2. View recent logs: `gcloud logging read "severity>=ERROR" --limit=100`
3. Check database connection pool: `SELECT count(*) FROM pg_stat_activity;`
4. Check B2 API status: https://status.backblaze.com

**Mitigation**:
- If DB connection pool exhausted: Scale API instances (more PgBouncer capacity)
- If B2 outage: Enable circuit breaker, show maintenance page
- If code bug: Rollback deployment, investigate

### Queue Backlog Growing

**Symptoms**: Queue depth > 100 and increasing

**Investigation**:
1. Check worker dashboard: Are workers processing jobs?
2. Check worker logs for errors: `kubectl logs -n photobomb deployment/thumbnail-worker`
3. Check B2 API rate limits (429 errors)

**Mitigation**:
- Scale workers: `kubectl scale deployment thumbnail-worker --replicas=10`
- If B2 rate limit: Implement exponential backoff, reduce concurrency
- If worker error: Fix bug, re-deploy workers

### Database Slow Queries

**Symptoms**: p95 query time > 1s, users report slow page loads

**Investigation**:
1. Check slow query log:
   ```sql
   SELECT query, mean_exec_time, calls
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC LIMIT 10;
   ```
2. Look for missing indexes or sequential scans

**Mitigation**:
- Add missing index (if safe to do online): `CREATE INDEX CONCURRENTLY ...`
- Increase connection pool size if bottleneck
- Consider read replica for heavy SELECT queries

## Implementation Notes

**Why Prometheus + Grafana?**
- Open-source, widely supported
- Rich query language (PromQL)
- Easy integration with GKE (node_exporter, kube-state-metrics)

**Alternative**: Datadog (all-in-one, easier setup but $$$)

**Why structured logging (JSON)?**
- Machine-parseable for aggregation
- Easy to filter by fields (e.g., all logs for user_id=X)
- Works well with Cloud Logging / Datadog

**Tradeoff: Log sampling**
- Pro: Reduces cost (Cloud Logging charges per GB)
- Con: May miss context for debugging
- **Mitigation**: Always log ERROR/WARN, sample INFO only

**SLO Error Budget**:
- If SLO breached (e.g., 99.5% instead of 99.9%), freeze new features
- Focus on reliability: Fix bugs, improve monitoring, add tests
- Resume features only when SLO is met for 1 week
