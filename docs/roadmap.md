# MVP Roadmap & Sprint Plan

## Product Vision

Build a privacy-first photo service that rivals Google Photos in features while giving users full control over their data, at 1/10th the infrastructure cost through smart architecture choices.

## Milestones

### Milestone 1: MVP - Core Upload & View (Weeks 1-6)

**Goal**: Users can upload photos, view timeline, and share albums

**Features**:
- ✅ User registration & JWT auth
- ✅ Direct browser→R2 uploads via presigned URLs (S3-compatible)
- ✅ Thumbnail generation (256px, 512px, 1024px) in WebP/JPEG
- ✅ Timeline view (sorted by date taken)
- ✅ Albums (create, add photos, share link, contributors)
- ✅ PWA installable (manifest + service worker)

**Acceptance Criteria**:
1. User can register and login
2. Upload 10 MB photo → thumbnails ready within 30s
3. Timeline loads 20 thumbnails in < 1s (4G network)
4. Duplicate photo detected based on SHA256 (shows "Already uploaded")
5. Album shared via link → recipient can view (no login required)
6. PWA installs on Android Chrome (Add to Home Screen prompt)
7. Unit tests cover 80% of backend code
8. Load test: 500 concurrent uploads/min for 10 min without queue backlog growth

**Team**:
- 1 Backend Engineer (FastAPI, PostgreSQL, Celery)
- 1 Frontend Engineer (React PWA, service worker)
- 1 DevOps/SRE (GCP, Terraform, K8s)
- 0.5 QA Engineer (manual + automated tests)

**Person-Weeks**: 18 (6 weeks × 3 full-time engineers)

---

### Milestone 2: Search & EXIF (Weeks 7-9) ✅ Complete

**Goal**: Users can search photos by date, location, camera model

**Features**:
- ✅ EXIF extraction (date, GPS, camera metadata)
- ✅ Location reverse geocoding (GPS → city name)
- ✅ Text search (caption, location, camera model)
- ✅ Date range filter
- ✅ Location-based search (within radius)
- ✅ Favorites and archive

**Acceptance Criteria**:
1. EXIF data extracted and displayed in photo detail view
2. Search for "San Francisco" returns matching photos (GPS or caption)
3. Date filter: "Photos from 2024-06" works correctly
4. Location search: "Photos within 10km of lat/lng" returns results in < 500ms
5. Favorite/archive state persists and filters work

**Team**: Same as M1 (2.5 full-time engineers)

**Person-Weeks**: 7.5 (3 weeks × 2.5 engineers)

---

### Milestone 3: Face Grouping (Opt-In) (Weeks 10-13) ✅ Complete

**Goal**: Users can auto-group photos by people (explicit opt-in)

**Features**:
- ✅ Privacy UI: Explicit opt-in checkbox with clear explanation
- 🚧 Face detection (RetinaFace or MTCNN) - In Progress
- 🚧 Face embedding (InsightFace ArcFace, 512-dim) - In Progress
- 🚧 Clustering (DBSCAN, stored in pgvector) - Logic Complete
- 🚧 Name faces (user-assigned labels) - API Partial
- ⏳ Search by person ("Show all photos of Mom") - Planned

**Acceptance Criteria**:
1. User opts in → faces detected in uploaded photos
2. Faces grouped automatically (min 3 faces per cluster)
3. User can name clusters (e.g., "John")
4. Search "John" returns all photos with that face (cosine similarity > 0.6)
5. User opts out → all face data deleted within 24hr
6. Face detection completes within 2 min of upload (GPU worker)

**Team**: 
- 1 Backend Engineer (face ML pipeline)
- 1 Frontend Engineer (opt-in UI, face management)
- 0.5 ML Engineer (model evaluation, tuning)

**Person-Weeks**: 10 (4 weeks × 2.5 engineers)

---

### Milestone 4: Advanced Sharing & Permissions (Weeks 14-16)

**Goal**: Password-protected shares, download control, analytics

**Features**:
- 🚧 Password-protected share links (bcrypt) - DB Schema Ready
- 🚧 Download enable/disable toggle - Planned
- 🚧 Share analytics (view count, download count, visitor IPs) - DB Schema Ready
- ⏳ Expiry customization (1 day, 7 days, 30 days, never) - Planned
- ✅ Revoke share link - Implemented

**Acceptance Criteria**:
1. Password-protected share: Visitor must enter correct password to view
2. Download disabled: Visitor sees thumbnails but can't download originals
3. Share analytics: Owner sees view/download counts per photo
4. Expired share: Visitor sees "This link has expired"
5. Revoked share: Link stops working immediately

**Team**: Same as M1 (2.5 full-time engineers)

**Person-Weeks**: 7.5 (3 weeks × 2.5 engineers)

---

### Milestone 5: Performance & Scale (Weeks 17-20) ✅ Complete

**Goal**: System handles 10k photos/day, 1k concurrent users

**Features**:
- ✅ CDN caching optimized (95%+ hit ratio)
- ✅ Read replicas for PostgreSQL (async replication)
- ✅ Horizontal autoscaling (HPA for workers, Cloud Run for API)
- ✅ Database Keep-Alive (Cron job every 2 hours)
- ✅ Database Indexes (Optimized for Visual Hashtags)
- ✅ Rate limiting (Cloudflare Workers)
- ✅ Monitoring dashboards (Grafana)
- ✅ Alerting (PagerDuty for critical, Slack for warnings)

**Acceptance Criteria**:
1. Load test: 1000 concurrent users → p95 latency < 500ms
2. Upload test: 10k photos in 24hr → all processed within 1hr
3. CDN cache hit ratio > 95% (checked via Cloudflare Analytics)
4. Auto-scaling: Workers scale from 2 → 20 pods under load, back to 2 when idle
5. Alert triggers when queue depth > 100 for 10 min
6. Database read replica lag < 1s (checked via monitoring)

**Team**:
- 1 Backend Engineer (optimization, caching)
- 1 DevOps/SRE (scaling, monitoring)
- 0.5 QA Engineer (load testing)

**Person-Weeks**: 10 (4 weeks × 2.5 engineers)

---

### Milestone 6: Mobile & Offline (Weeks 21-24)

**Goal**: Robust PWA with offline uploads, iOS support

**Features**:
- ✅ Service worker background sync (Android)
- ✅ Offline upload queue persists across app restarts
- ✅ iOS Add to Home Screen guidance
- ✅ iOS foreground sync workaround (Visibility Change event)
- ✅ Network status indicator
- ✅ Retry failed uploads

**Acceptance Criteria**:
1. Android: Upload while offline → auto-syncs when network returns
2. iOS: Upload queue shown on app open → user manually triggers sync
3. Failed upload: Retry button works, succeeds on subsequent attempt
4. Network indicator: Shows "Offline" banner when disconnected
5. IndexedDB persists 50 pending uploads without eviction

**Team**: 1 Frontend Engineer (PWA deep-dive)

**Person-Weeks**: 4 (4 weeks × 1 engineer)

---

## 9-Month Scale Plan (Post-MVP)

### Q2 (Months 4-6): Enhanced Features

**Goals**:
- Multi-user albums (collaborative)
- AI-powered search ("sunset", "beach")
- Video support (up to 4K, transcoded to H.265)
- Desktop app (Electron wrapper)

**Estimated Effort**: 36 person-weeks

---

### Q3 (Months 7-9): Enterprise & Monetization

**Goals**:
- Team accounts (shared storage quota)
- Storage tier upgrades (100GB → 1TB → Unlimited)
- Stripe integration (subscriptions)
- Admin dashboard (user management, analytics)

**Estimated Effort**: 48 person-weeks

---

## Sprint Plan (3-Month MVP)

### Sprint 1-2 (Weeks 1-4): Foundation

**Backend**:
- PostgreSQL schema setup (users, photos, albums, shares)
- FastAPI endpoints (auth, upload/presign, photos CRUD)
- Celery workers (thumbnail generation)
- JWT auth + refresh tokens

**Frontend**:
- React app setup (Vite + React Router)
- Login/register pages
- Upload UI (drag-and-drop)
- Timeline view (infinite scroll)

**DevOps**:
- Terraform infrastructure (VPC, Cloud SQL, GKE, Cloud Run)
- CI/CD pipeline (GitHub Actions)
- Local dev environment (Docker Compose)

**Tests**:
- Backend unit tests (pytest, 70% coverage)
- Frontend tests (Jest, React Testing Library)

---

### Sprint 3-4 (Weeks 5-8): Core Features

**Backend**:
- Album management APIs
- Share link creation (public, password-protected)
- EXIF extraction (exiftool integration)
- Deduplication (SHA256 check before upload)

**Frontend**:
- Album create/edit UI
- Share dialog (copy link, set password)
- Photo detail view (EXIF data)
- Search bar (text search)

**DevOps**:
- Monitoring setup (Prometheus, Grafana)
- Alerting (PagerDuty, Slack)

**Tests**:
- Integration tests (upload → process → view flow)
- E2E tests (Playwright: login, upload, share)

---

### Sprint 5-6 (Weeks 9-12): Polish & Launch

**Backend**:
- Face recognition (opt-in, InsightFace)
- Performance optimization (query indexes, caching)
- Rate limiting (Cloudflare Workers)

**Frontend**:
- PWA polish (manifest, service worker, offline queue)
- iOS Add to Home instructions
- Face grouping UI (opt-in, name faces)

**DevOps**:
- Load testing (k6, target 500 uploads/min)
- Production deployment checklist
- Runbooks for common incidents

**Tests**:
- Load tests (k6 scripts)
- Security audit (OWASP checklist)
- UAT (user acceptance testing with beta users)

---

## Team Roles & Responsibilities

| Role | Responsibilities | FTE |
|------|------------------|-----|
| **Backend Engineer** | FastAPI, PostgreSQL, Celery, APIs | 1.0 (full-time) |
| **Frontend Engineer** | React PWA, service worker, UI/UX | 1.0 |
| **DevOps/SRE** | GCP, Terraform, K8s, monitoring, CI/CD | 1.0 |
| **ML Engineer** | Face detection, embedding models (M3 only) | 0.5 (part-time) |
| **QA Engineer** | Manual testing, automated tests, load testing | 0.5 |
| **Product Manager** | Requirements, roadmap, user feedback | 0.5 |

**Total**: 4.5 FTE for MVP (3 months)

---

## Dependencies & Risks

| Dependency | Risk | Mitigation |
|------------|------|------------|
| B2 API reliability | B2 outage blocks uploads | Circuit breaker, fallback to R2 |
| pgvector performance | Slow queries at scale (>10M embeddings) | Create HNSW index, consider Pinecone if needed |
| iOS PWA limitations | No Background Sync | Visibility Change workaround, educate users |
| Face recognition accuracy | False positives annoy users | Conservative clustering (eps=0.4), allow manual split/merge |
| Storage cost growth | Unexpected traffic spikes | Monitor closely, implement tiered storage (hot/cold) |

---

## Launch Checklist

### Pre-Launch (1 week before)
- [ ] Load test passed (500 concurrent uploads/min)
- [ ] Security audit complete (OWASP checklist)
- [ ] Privacy policy & ToS updated (GDPR-compliant)
- [ ] Monitoring dashboards validated
- [ ] Runbooks tested (rollback, incident response)
- [ ] Beta user feedback incorporated

### Launch Day
- [ ] DNS cutover to production
- [ ] CloudFlare CDN warmed (pre-cache common assets)
- [ ] PagerDuty on-call schedule set
- [ ] Status page live (status.photobomb.app)
- [ ] Marketing site updated (landing page, pricing)

### Post-Launch (1 week after)
- [ ] Monitor SLOs (99.9% uptime, p95 < 500ms)
- [ ] Review error logs for anomalies
- [ ] Gather user feedback (NPS survey)
- [ ] Plan hotfixes for critical bugs

---

## Success Metrics (3 Months Post-Launch)

| Metric | Target |
|--------|--------|
| Active Users | 1,000 |
| Photos Uploaded | 500,000 |
| Storage Used | 5 TB |
| Upload Success Rate | > 99% |
| API Uptime | 99.9% |
| p95 Latency | < 500ms |
| User Retention (30-day) | > 60% |
| NPS Score | > 50 |
