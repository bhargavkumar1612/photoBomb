# Operational Runbook

## Common Operational Tasks

### 1. Restore from Backup

**When**: Database corruption, accidental data deletion

**Steps**:
```bash
# 1. Stop API (prevent new writes during restore)
gcloud run services update photobomb-api --region=us-central1 --no-traffic

# 2. List available backups
gcloud sql backups list --instance=photobomb-prod-db

# 3. Restore from specific backup
gcloud sql backups restore BACKUP_ID \
  --backup-instance=photobomb-prod-db \
  --backup-id=BACKUP_ID

# 4. Verify data (connect via Cloud SQL Proxy)
cloud_sql_proxy -instances=PROJECT:REGION:photobomb-prod-db=tcp:5432
psql -h 127.0.0.1 -U photobomb_app -d photobomb
# Run validation queries...

# 5. Resume traffic
gcloud run services update photobomb-api --region=us-central1 --traffic 100
```

**Estimated Time**: 30-60 minutes (depending on DB size)

**Rollback**: If restore fails, switch to read replica temporarily

---

### 2. Rotate Secrets & Keys

**When**: Security breach, quarterly rotation (best practice)

**Secrets to Rotate**:
- Database password
- JWT secret key
- B2 application key
- Cloudflare API token

**Steps**:
```bash
# 1. Generate new secrets
NEW_DB_PASSWORD=$(openssl rand -base64 32)
NEW_JWT_SECRET=$(openssl rand -base64 64)

# 2. Update Cloud SQL user password
gcloud sql users set-password photobomb_app \
  --instance=photobomb-prod-db \
  --password=$NEW_DB_PASSWORD

# 3. Update secrets in GCP Secret Manager
echo -n $NEW_DB_PASSWORD | gcloud secrets versions add database-password --data-file=-
echo -n $NEW_JWT_SECRET | gcloud secrets versions add jwt-secret --data-file=-

# 4. Update environment variables in Cloud Run
gcloud run services update photobomb-api \
  --update-secrets=DATABASE_PASSWORD=database-password:latest,JWT_SECRET=jwt-secret:latest

# 5. Rolling restart workers (to pick up new secrets)
kubectl rollout restart deployment/thumbnail-worker -n photobomb
kubectl rollout restart deployment/face-worker -n photobomb

# 6. Revoke old B2 key (via Backblaze web console)
# Create new key → update K8s secret → delete old key
```

**Downtime**: ~2 minutes (during Cloud Run deployment)

**Validation**: Test login with new JWT secret, verify workers can access DB

---

### 3. Scale Workers

**When**: Queue backlog growing, anticipated traffic spike

**Manual Scaling**:
```bash
# Scale up thumbnail workers
kubectl scale deployment thumbnail-worker --replicas=20 -n photobomb

# Scale down after spike
kubectl scale deployment thumbnail-worker --replicas=3 -n photobomb
```

**Auto-Scaling (verify HPA)**:
```bash
kubectl get hpa -n photobomb

# Should show:
# NAME                 REFERENCE                      TARGETS   MINPODS   MAXPODS   REPLICAS
# thumbnail-worker-hpa Deployment/thumbnail-worker   45%/70%   2         20        5
```

**Validation**: Check queue depth decreasing:
```bash
redis-cli -h $REDIS_HOST LLEN high_priority_queue
```

---

### 4. Handle Storage Outage (B2 Down)

**Symptoms**: Upload failures, 500 errors from B2 API

**Immediate Actions**:
1. **Check B2 status**: https://status.backblaze.com
2. **Enable circuit breaker** (if not auto-enabled):
   ```python
   # In app config
   CIRCUIT_BREAKER_THRESHOLD = 10  # Open after 10 failures
   CIRCUIT_BREAKER_TIMEOUT = 60    # Retry after 60s
   ```
3. **Show maintenance banner**:
   ```bash
   # Update Cloudflare Worker to inject banner
   wrangler publish --env=maintenance
   ```

**Long-Term Mitigation**:
- Implement fallback to Cloudflare R2
- Queue failed uploads for retry (don't return error to user)

**Rollback**: Remove maintenance banner when B2 recovers

---

### 5. Rollback Deployment

**When**: New version causes critical bugs, error rate spike

**Steps**:
```bash
# 1. List recent revisions
gcloud run revisions list --service=photobomb-api --region=us-central1

# 2. Route traffic to previous revision
gcloud run services update-traffic photobomb-api \
  --to-revisions=photobomb-api-abc123=100

# 3. Rollback workers (if needed)
kubectl rollout undo deployment/thumbnail-worker -n photobomb

# 4. Verify error rate decreased
# Check Grafana dashboard or:
curl https://api.photobomb.app/healthz
```

**Validation**: Monitor error logs for 15 minutes post-rollback

---

### 6. Increase Database Capacity

**When**: Connection pool exhaustion, slow queries due to resource limits

**Steps**:
```bash
# 1. Upsize Cloud SQL instance (requires downtime ~5 min)
gcloud sql instances patch photobomb-prod-db \
  --tier=db-custom-8-32768  # 8 vCPU, 32 GB RAM

# 2. Update max_connections (if needed)
gcloud sql instances patch photobomb-prod-db \
  --database-flags=max_connections=400

# 3. Verify instance is healthy
gcloud sql operations list --instance=photobomb-prod-db

# 4. Update PgBouncer config (if using)
# Increase pool_size to match new max_connections
```

**Downtime**: ~5 minutes for instance resize

**Cost Impact**: db-custom-4-16384 = $250/mo → db-custom-8-32768 = $500/mo

---

### 7. Purge CDN Cache (Force Refresh)

**When**: Thumbnails updated (e.g., reprocessing with better quality), stale content

**Steps**:
```bash
# Purge all thumbnails for a photo
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "files": [
      "https://cdn.photobomb.app/thumb/photo123/256.webp",
      "https://cdn.photobomb.app/thumb/photo123/512.webp",
      "https://cdn.photobomb.app/thumb/photo123/1024.webp"
    ]
  }'

# Purge everything (use sparingly, causes origin load spike)
curl -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{"purge_everything":true}'
```

**Validation**: Check cache headers:
```bash
curl -I https://cdn.photobomb.app/thumb/photo123/512.webp | grep X-Cache
# Should show HIT or MISS (MISS after purge)
```

---

### 8. Export User Data (GDPR Request)

**When**: User requests data export (right to portability)

**Steps**:
```bash
# 1. Trigger export job (API endpoint)
curl -X POST https://api.photobomb.app/api/v1/user/export \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"user_id": "uuid"}'

# Job runs async, creates ZIP with:
# - metadata.json (user info, photos, albums)
# - photos/ (all original files)

# 2. Download export from Cloud Storage
gsutil cp gs://photobomb-exports/user-uuid-export.zip .

# 3. Email to user with 7-day download link
# (Automated in API, no manual step)
```

**Expected Time**: 5-30 minutes (depending on photo count)

**Validation**: Unzip and verify metadata.json is valid JSON

---

### 9. Hard Delete User Account

**When**: User deletes account AND 30-day grace period expired

**Steps**:
```sql
-- 1. Verify soft-delete timestamp
SELECT user_id, email, deleted_at 
FROM users 
WHERE deleted_at < NOW() - INTERVAL '30 days';

-- 2. Delete all user data (cascades to photos, albums, etc.)
BEGIN;
DELETE FROM face_detections WHERE user_id = 'uuid';
DELETE FROM face_clusters WHERE user_id = 'uuid';
DELETE FROM photos WHERE user_id = 'uuid';
DELETE FROM albums WHERE user_id = 'uuid';
DELETE FROM users WHERE user_id = 'uuid';
COMMIT;
```

**B2 Object Deletion**:
```python
# In worker or cron job
b2_api = B2Api()
photos = db.query(PhotoFile).filter_by(user_id=user_id).all()
for photo in photos:
    b2_api.delete_file_version(photo.b2_key, photo.b2_file_id)
```

**Audit Log**:
```sql
INSERT INTO audit_logs (user_id, action, details)
VALUES ('uuid', 'account_deleted', '{"retention_period": "30 days"}');
```

---

### 10. Reprocess Photos (Storage Migration or Quality Improvement)

**When**: Switching from B2 to R2, upgrading thumbnail quality

**Steps**:
```bash
# 1. Create reprocessing job queue
psql -h $DB_HOST -U photobomb_app -d photobomb -c "
  INSERT INTO processing_jobs (upload_id, job_type, priority)
  SELECT upload_id, 'reprocess_thumbnails', 10
  FROM photos
  WHERE processed_at < '2024-01-01'  -- Old photos
  ON CONFLICT (idempotency_key) DO NOTHING;
"

# 2. Scale up workers for batch processing
kubectl scale deployment thumbnail-worker --replicas=50 -n photobomb

# 3. Monitor progress
watch -n 5 "redis-cli -h $REDIS_HOST LLEN batch_processing_queue"

# 4. Scale down after completion
kubectl scale deployment thumbnail-worker --replicas=3 -n photobomb
```

**Expected Time**: 10k photos @ 100 photos/min = ~2 hours

**Validation**: Verify new thumbnails exist in R2, delete old B2 objects

---

## Incident Response Procedures

### Severity Levels

| Severity | Definition | Response Time | Examples |
|----------|------------|---------------|----------|
| **SEV1** | Total outage, data loss | < 15 min | API down, DB inaccessible |
| **SEV2** | Partial outage, degraded | < 1 hour | Slow uploads, some 5xx errors |
| **SEV3** | Minor issue, workaround exists | < 4 hours | Non-critical endpoint slow |
| **SEV4** | Cosmetic, no user impact | Next sprint | UI alignment issue |

### SEV1 Response

1. **Alert**: PagerDuty pages on-call engineer
2. **Acknowledge**: Engineer confirms within 5 minutes
3. **Triage**: Check status.photobomb.app, update with "Investigating"
4. **Mitigate**: Rollback deployment, scale resources, enable circuit breaker
5. **Communicate**: Update status page every 30 min, post in #incidents Slack
6. **Resolve**: Issue fixed, monitor for 1 hour
7. **Post-Mortem**: Write incident report within 48 hours (blameless)

### Communication Templates

**Status Page Update**:
> **Investigating** - We are aware of an issue with photo uploads and are investigating the cause. We will provide an update within 30 minutes.

**Resolution**:
> **Resolved** - The issue with photo uploads has been resolved. Uploads are now processing normally. We apologize for the inconvenience.

---

## Maintenance Windows

**Schedule**: 2nd Sunday of each month, 2:00 AM - 4:00 AM PST

**Tasks**:
- PostgreSQL minor version upgrades
- OS security patches (GKE nodes)
- Certificate rotation
- Load test in production (simulated spike)

** ** **Announcement**: Email users 7 days in advance

---

## On-Call Rotation

**Schedule**: 24/7 coverage, 1-week rotations

**Responsibilities**:
- Respond to PagerDuty alerts
- Monitor #alerts Slack channel
- Perform weekly health checks (Runbook #11)

**Handoff Checklist**:
- [ ] Review open incidents
- [ ] Check upcoming maintenance windows
- [ ] Verify PagerDuty escalation policy
- [ ] Test pager (send test alert)

---

## Runbook Maintenance

**Review Frequency**: Quarterly

**Update Triggers**:
- New infrastructure changes (e.g., switch from B2 to R2)
- Incident root cause (add new runbook if recurring issue)
- Team feedback (outdated steps)

**Owner**: DevOps/SRE team lead
