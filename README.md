# PhotoBomb - Production-Ready Photo Service

> A privacy-first, Google Photos alternative built with modern web technologies and cost-effective infrastructure.

## 🎯 Project Overview

PhotoBomb is a comprehensive production plan for building a full-featured photo service (PWA) with:

- **Configurable Storage** - Support for Backblaze B2, Cloudflare R2, or AWS S3 via pluggable storage architecture
- **Direct browser uploads** to cloud storage (S3-compatible presigned URLs)
- **Secure Image Serving** via AOT Presigned URLs (no public buckets)
- **Smart processing pipeline** (thumbnails, EXIF, deduplication)
- **Google Login** & standard JWT Auth
- **Albums** with collaborative features (contributors, sharing, viewer tracking)
- **Trash & Restore** functionality with soft delete
- **Face Recognition** with automatic clustering (DBSCAN, pgvector embeddings)
- **Visual Hashtags** via CLIP AI (automatic tagging for animals, documents, etc.)
- **Premium Gallery UI**: Glassmorphism aesthetics, responsive layouts, and optimistic interactions.
- **Place Recognition** with GPS extraction and reverse geocoding
- **PWA installable** on Android/iOS (offline uploads, service worker)
- **Privacy-first design** (GDPR/CCPA compliant, user data control)
- **Cost-optimized architecture** (~$15-60/month for 1-20TB storage)

## 📁 Repository Structure

```
photoBomb/
├── docs/
│   ├── architecture/
│   │   ├── system_architecture.md     # High-level design, component choices
│   │   ├── sequence_diagrams.md       # Upload, sync, sharing flows
│   │   └── processing_pipeline.md     # Thumbnail specs, deduplication, ML
│   ├── api/
│   │   └── openapi.yaml              # Complete REST API specification
│   ├── database/
│   │   └── schema.sql                # PostgreSQL + pgvector schema
│   ├── security/
│   │   └── security_privacy.md       # Threat model, auth, encryption
│   ├── operations/
│   │   ├── monitoring.md             # Metrics, SLOs, dashboards
│   │   └── runbook.md                # Common operational tasks
│   ├── cost_model.csv                # R2 vs S3 cost analysis
│   ├── pwa_spec.md                   # Manifest, service worker, offline
│   ├── roadmap.md                    # 3-month MVP + 9-month scale plan
│   ├── testing_plan.md               # Unit, integration, E2E, load tests
│   └── compliance.md                 # GDPR, CCPA, BIPA checklists
├── infrastructure/
│   ├── terraform/
│   │   └── main.tf                   # GCP infrastructure (Cloud SQL, GKE, Cloud Run)
│   ├── k8s/
│   │   └── workers.yaml              # Celery workers deployment
│   └── workers/                      # Cloudflare Workers (future)
├── tests/
│   ├── load/                         # k6 load test scripts
│   ├── integration/                  # API integration tests
│   └── e2e/                          # Playwright E2E tests
├── .github/
│   └── workflows/
│       └── ci-cd.yml                 # GitHub Actions pipeline
└── README.md                         # This file
```

## 🚀 Quick Start (Reviewing Artifacts)

### 1. Understand the Architecture

**Start here**: [docs/architecture/system_architecture.md](docs/architecture/system_architecture.md)
- Component diagram
- Data flows (upload, read, search)
- Failure points & mitigation

**Then**: [docs/architecture/sequence_diagrams.md](docs/architecture/sequence_diagrams.md)
- Detailed upload flow with presigned URLs
- Offline sync (PWA)
- Share link generation

### 2. Review API Design

**OpenAPI Spec**: [docs/api/openapi.yaml](docs/api/openapi.yaml)
- All endpoints (auth, upload, photos, albums, sharing)
- Request/response schemas
- Authentication (JWT + refresh tokens)

**Visualize**: Import into Swagger Editor (https://editor.swagger.io)

### 3. Examine Database Schema

**SQL DDL**: [docs/database/schema.sql](docs/database/schema.sql)
- Complete schema with indexes
- pgvector for face embeddings
- Example queries (timeline, search, dedupe)

**Visualize**: Use dbdiagram.io or similar tool

### 4. Cost Analysis

**Cost Model**: [docs/cost_model.csv](docs/cost_model.csv)
- R2 vs S3 comparison
- 1TB, 5TB, 20TB scenarios
- Growth projections (3-18 months)

**Key Takeaway**: Cloudflare R2 is preferred for high-bandwidth apps due to **zero egress fees**, despite slightly higher storage costs ($15/TB vs B2's $5/TB) compared to B2, but significantly cheaper than AWS S3.

### 5. Security & Privacy

**Security Design**: [docs/security/security_privacy.md](docs/security/security_privacy.md)
- Threat model (SQL injection, XSS, CSRF, etc.)
- JWT + refresh token flow
- Row-level security (PostgreSQL RLS)
- Face recognition privacy (opt-in enforcement)

### 6. Deployment Plan

**Infrastructure**: [infrastructure/terraform/main.tf](infrastructure/terraform/main.tf)
- VPC, Cloud SQL (PostgreSQL), GKE cluster
- Cloud Run (FastAPI), Redis (Celery broker)
- Cloudflare CDN configuration

**CI/CD**: [.github/workflows/deploy.yml](.github/workflows/deploy.yml) & [.github/workflows/deploy-frontend.yml](.github/workflows/deploy-frontend.yml)
- Test → Build → Deploy pipeline
- E2E tests post-deployment

### 7. MVP Roadmap

**Roadmap**: [docs/roadmap.md](docs/roadmap.md)
- 6 milestones (3-month MVP)
- Team structure (4.5 FTE)
- Acceptance criteria per milestone
- Person-week estimates (total: ~58 weeks)

**Key Milestones**:
1. Core Upload & View (Weeks 1-6)
2. Search & EXIF (Weeks 7-9)
3. Face Grouping (Weeks 10-13)
4. Advanced Sharing (Weeks 14-16)
5. Performance & Scale (Weeks 17-20)
6. Mobile & Offline (Weeks 21-24)

## 🧪 Running Tests (Hypothetical Dev Environment)

### Backend Unit Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Frontend Tests

```bash
cd frontend
npm install
npm test -- --coverage
```

### E2E Tests (Playwright)

```bash
cd tests/e2e
npm install
npx playwright test --project=chromium
```

### Load Tests (k6)

```bash
# Install k6: https://k6.io/docs/getting-started/installation/

# Run normal traffic simulation
k6 run tests/load/normal_traffic.js

# Run upload spike test
k6 run tests/load/upload_spike.js
```

## 📊 Key Design Decisions & Tradeoffs

### Why Cloudflare R2 over AWS S3 or Backblaze B2?
- **Zero Egress Fees**: Unlike S3 ($0.09/GB) or B2 ($0.01/GB after limit), R2 has $0 egress. This is critical for a media-heavy app.
- **S3 Compatibility**: Drop-in replacement for S3 SDKs (boto3, etc.).
- **Cost**: $15/TB/month storage is higher than B2 ($5/TB) but the free egress saves money for read-heavy workloads.
- **Performance**: Edge-native performance.

### Why libvips over ImageMagick?
- **Performance**: 4-8x faster for batch thumbnail generation
- **Memory**: 10x lower memory usage (streaming architecture)
- **Tradeoff**: Less mature ecosystem, fewer online examples
- **Verdict**: Worth it for cost savings (smaller workers)

### Why PostgreSQL + pgvector over dedicated vector DB?
- **Simplicity**: One database instead of two (Postgres + Pinecone)
- **Cost**: Free (included in Cloud SQL) vs. $70+/month for Pinecone
- **Tradeoff**: pgvector limited to ~10M vectors; Pinecone scales to billions
- **Verdict**: Perfect for MVP (<1M users); revisit at scale

### Why PWA instead of native apps?
- **Development Cost**: 1 codebase (React) vs. 3 (iOS, Android, Web)
- **Tradeoff**: No App Store presence, limited iOS features (Background Sync)
- **Mitigation**: iOS workaround (Visibility Change event for sync)
- **Verdict**: Launch as PWA, consider native if traction

### Why Celery over Cloud Functions?
- **Control**: Full control over worker lifecycle, GPU support
- **Cost**: GKE nodes cheaper than Cloud Functions for sustained loads
- **Tradeoff**: More operational complexity (K8s management)
- **Alternative**: Use Cloud Functions for MVP, migrate to Celery at scale

## 🔐 Security Highlights

- **TLS everywhere**: Cloudflare enforces HTTPS, Cloud SQL requires TLS
- **JWT + refresh tokens**: Short-lived access tokens (1hr), HttpOnly cookies
- **Row-level security**: PostgreSQL RLS ensures users can't access others' photos
- **Rate limiting**: Cloudflare Workers (5 login attempts per 15 min)
- **Security headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options
- **OWASP Top 10**: Checklist covered in security doc

## 📈 Scalability Plan

### Horizontal Scaling

- **API**: Cloud Run auto-scales (2-100 instances)
- **Workers**: GKE HPA (2-20 pods based on queue depth)
- **Database**: PgBouncer connection pooling, read replicas for search

### Vertical Scaling

- **Database**: Scale from db-custom-4-16 (4 vCPU, 16GB) to db-custom-16-64 at scale
- **Workers**: n2-standard-4 (4 vCPU) → n2-standard-8 (8 vCPU) if needed

### Multi-Region (Future)

- **Storage**: Replicate R2 buckets to EU region (if EU users > 30%)
- **CDN**: Cloudflare already multi-region (auto-optimized)
- **Database**: Use Cloud SQL read replicas in EU region (async replication)

## 📝 Compliance

**GDPR** (EU):
- ✅ Right to access (export data)
- ✅ Right to deletion (30-day soft delete, then purge)
- ✅ Right to portability (JSON export)
- ✅ Data breach notification (72-hour timeline)

**CCPA** (California):
- ✅ Right to know (Privacy Policy disclosure)
- ✅ Right to delete (same as GDPR)
- N/A: No data selling

**BIPA** (Illinois biometric data):
- ✅ Explicit consent for face recognition
- ✅ Written retention policy
- ✅ Deletion within 24 hours of opt-out

See [docs/compliance.md](docs/compliance.md) for full checklist.

## 🎯 Success Metrics (3 Months Post-Launch)

| Metric | Target |
|--------|--------|
| Active Users | 1,000 |
| Photos Uploaded | 500,000 |
| Storage Used | 5 TB |
| Upload Success Rate | > 99% |
| API Uptime | 99.9% (SLO) |
| p95 API Latency | < 500ms |
| User Retention (30-day) | > 60% |
| NPS Score | > 50 |

## 🛠 Tech Stack Summary

### Frontend
- **Framework**: React 18.2+ with Vite
- **PWA**: Workbox 7.0+ (service worker)
- **State**: React Query + Zustand
- **Styling**: CSS Modules or Tailwind (TBD)

### Backend
- **API**: FastAPI 0.104+ (Python 3.11+)
- **GraphQL**: Strawberry 0.209+ (for complex queries)
- **Workers**: Celery 5.3+ with Redis 7.2+
- **Auth**: JWT (PyJWT), bcrypt (cost 12)

### Database
- **Primary**: PostgreSQL 16 with pgvector 0.5+
- **Extensions**: pg_trgm (fuzzy search), btree_gin (composite indexes)
- **Connection Pool**: PgBouncer (transaction mode)

### Storage
- **Primary**: Configurable (Backblaze B2, Cloudflare R2, or AWS S3)
- **Architecture**: Pluggable storage factory pattern with per-photo provider tracking
- **Bucket Type**: Private (all access via signed URLs)
- **CDN**: Cloudflare (integrated)
- **Hybrid Support**: Multiple storage providers can be used simultaneously

### Processing
- **Image Library**: libvips 8.14+ (pyvips for Python)
- **Face Detection**: InsightFace ArcFace (ONNX)
- **Hashing**: imagehash (pHash), hashlib (SHA256)

### Infrastructure
- **Cloud**: Google Cloud Platform (GCP)
- **IaC**: Terraform 1.6+
- **Container Orchestration**: GKE (Kubernetes 1.28+)
- **Serverless API**: Cloud Run (Knative)

## 📞 Support & Contact

**For Questions**:
- Technical Lead: [your-email@example.com]
- Product Manager: [pm-email@example.com]

**Issue Tracking**:
- GitHub Issues (if open-sourced)
- Jira (if internal project)

## 📄 License

[Choose License: MIT, Apache 2.0, or Proprietary if commercial]

---

## 🔍 Next Steps

### For Technical Leads
1. Review architecture ([docs/architecture/system_architecture.md](docs/architecture/system_architecture.md))
2. Review security design ([docs/security/security_privacy.md](docs/security/security_privacy.md))
3. Validate cost model ([docs/cost_model.csv](docs/cost_model.csv))
4. Approve roadmap ([docs/roadmap.md](docs/roadmap.md))

### For Backend Engineers
1. Study OpenAPI spec ([docs/api/openapi.yaml](docs/api/openapi.yaml))
2. Review database schema ([docs/database/schema.sql](docs/database/schema.sql))
3. Understand processing pipeline ([docs/architecture/processing_pipeline.md](docs/architecture/processing_pipeline.md))

### For Frontend Engineers
1. Review PWA spec ([docs/pwa_spec.md](docs/pwa_spec.md))
2. Study sequence diagrams ([docs/architecture/sequence_diagrams.md](docs/architecture/sequence_diagrams.md))
3. Plan offline upload queue (IndexedDB + service worker)

### For DevOps/SRE
1. Review Terraform code ([infrastructure/terraform/main.tf](infrastructure/terraform/main.tf))
2. Study monitoring plan ([docs/operations/monitoring.md](docs/operations/monitoring.md))
3. Familiarize with runbook ([docs/operations/runbook.md](docs/operations/runbook.md))

### For QA Engineers
1. Review testing plan ([docs/testing_plan.md](docs/testing_plan.md))
2. Set up Playwright for E2E tests
3. Plan load testing scenarios (k6)

---

**Built with ruthless attention to detail by [Your Team Name]**

*Last Updated: January 2026*
