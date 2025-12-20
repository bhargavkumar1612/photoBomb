# Testing Plan

## Test Pyramid Strategy

```
        /\
       /E2E\ (10%)
      /------\
     /Integra\ (20%)
    /----------\
   /    Unit    \ (70%)
  /--------------\
```

## Unit Tests

### Backend (pytest)

**Coverage Target**: 80%

**Test Categories**:
1. **API Endpoints** (tests/test_api.py)
2. **Business Logic** (tests/test_services.py)
3. **Database Models** (tests/test_models.py)
4. **Utilities** (tests/test_utils.py)

**Example Test**:
```python
# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_presign_success(auth_headers):
    """Test presigned URL generation for new upload"""
    response = client.post(
        "/api/v1/upload/presign",
        json={
            "filename": "test.jpg",
            "size_bytes": 1024000,
            "mime_type": "image/jpeg",
            "sha256": "abc123..."
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "upload_id" in data
    assert "presigned_url" in data
    assert "b2" in data["presigned_url"]

def test_upload_presign_duplicate(auth_headers, existing_photo):
    """Test duplicate detection returns 409"""
    response = client.post(
        "/api/v1/upload/presign",
        json={
            "filename": "test.jpg",
            "size_bytes": 1024000,
            "mime_type": "image/jpeg",
            "sha256": existing_photo.sha256
        },
        headers=auth_headers
    )
    assert response.status_code == 409
    assert response.json()["photo_id"] == existing_photo.photo_id
```

**Run Command**:
```bash
pytest tests/ -v --cov=app --cov-report=html
```

### Frontend (Jest + React Testing Library)

**Coverage Target**: 70%

**Test Categories**:
1. **Components** (src/__tests__/components/)
2. **Hooks** (src/__tests__/hooks/)
3. **Utilities** (src/__tests__/utils/)
4. **Service Worker** (src/__tests__/serviceWorker/)

**Example Test**:
```javascript
// src/__tests__/components/PhotoGrid.test.jsx
import { render, screen, waitFor } from '@testing-library/react';
import { PhotoGrid } from '@/components/PhotoGrid';

test('renders photos in grid layout', async () => {
  const mockPhotos = [
    { photo_id: '1', thumb_urls: { thumb_512: '/img1.webp' } },
    { photo_id: '2', thumb_urls: { thumb_512: '/img2.webp' } },
  ];
  
  render(<PhotoGrid photos={mockPhotos} />);
  
  await waitFor(() => {
    expect(screen.getAllByRole('img')).toHaveLength(2);
  });
});

test('shows empty state when no photos', () => {
  render(<PhotoGrid photos={[]} />);
  expect(screen.getByText(/no photos yet/i)).toBeInTheDocument();
});
```

**Run Command**:
```bash
cd frontend && npm test -- --coverage
```

## Integration Tests

### API Integration Tests

**Scope**: Test full request flow (API → DB → response)

**Test Scenarios**:
1. **Upload Flow**: Presign → Confirm → Worker processes → Photo retrieved
2. **Album Flow**: Create album → Add photos → Share → Access via share link
3. **Search Flow**: Upload with EXIF → Search by location → Results returned

**Example Test**:
```python
# tests/integration/test_upload_flow.py
import pytest
from app.celery_app import celery_app
from tests.factories import UserFactory

@pytest.mark.integration
def test_full_upload_flow(client, db_session):
    """Test complete upload → process → retrieve flow"""
    # 1. Create user
    user = UserFactory()
    auth_token = create_jwt_token(user.user_id)
    
    # 2. Request presigned URL
    response = client.post(
        "/api/v1/upload/presign",
        json={"filename": "test.jpg", "size_bytes": 1000, "mime_type": "image/jpeg", "sha256": "abc123"},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    upload_id = response.json()["upload_id"]
    
    # 3. Simulate upload confirmation
    response = client.post(
        "/api/v1/upload/confirm",
        json={"upload_id": upload_id},
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 202
    photo_id = response.json()["photo_id"]
    
    # 4. Process job (synchronously in test)
    celery_app.conf.task_always_eager = True
    # Worker runs automatically in eager mode
    
    # 5. Verify photo is processed
    db_session.refresh()
    response = client.get(
        f"/api/v1/photos/{photo_id}",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["processed_at"] is not None
    assert "thumb_256" in data["thumb_urls"]
```

**Run Command**:
```bash
pytest tests/integration/ -v -m integration
```

## End-to-End Tests (Playwright)

### Critical User Flows

**Test Scenarios**:
1. **Registration & Login**
2. **Upload → Timeline → View**
3. **Create Album → Share → Access**
4. **Search Photos**
5. **Face Grouping (Opt-In)**

**Example Test**:
```javascript
// tests/e2e/upload.spec.js
import { test, expect } from '@playwright/test';

test('user can upload photo and view in timeline', async ({ page }) => {
  // 1. Login
  await page.goto('https://photobomb.app/login');
  await page.fill('[name=email]', 'test@example.com');
  await page.fill('[name=password]', 'password123');
  await page.click('button[type=submit]');
  await expect(page).toHaveURL('/');
  
  // 2. Upload photo
  await page.click('[aria-label="Upload"]');
  const fileChooserPromise = page.waitForEvent('filechooser');
  await page.click('button:has-text("Choose Files")');
  const fileChooser = await fileChooserPromise;
  await fileChooser.setFiles('./fixtures/test-photo.jpg');
  
  // 3. Wait for upload to complete
  await expect(page.locator('.upload-status:has-text("Completed")')).toBeVisible({ timeout: 60000 });
  
  // 4. Verify photo appears in timeline
  await page.goto('/');
  await expect(page.locator('img[alt*="test-photo"]')).toBeVisible();
});
```

**Run Command**:
```bash
npx playwright test --project=chromium
```

**Browser Matrix**:
- Chrome (Desktop & Android emulation)
- Firefox
- Safari
- Mobile Safari (iOS emulation)

## Load Tests (k6)

### Scenario 1: Normal Traffic

**Profile**:
- 500 virtual users
- 50 requests/sec sustained
- Duration: 10 minutes

**Script**:
```javascript
// tests/load/normal_traffic.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 500,
  duration: '10m',
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],   // Error rate < 1%
  },
};

export default function() {
  // Timeline request
  const res = http.get('https://api.photobomb.app/api/v1/photos', {
    headers: { 'Authorization': `Bearer ${__ENV.AUTH_TOKEN}` },
  });
  
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });
  
  sleep(1);
}
```

**Run Command**:
```bash
k6 run tests/load/normal_traffic.js
```

### Scenario 2: Upload Spike

**Profile**:
- 1000 virtual users
- 500 concurrent uploads/minute
- Duration: 10 minutes

**Script**:
```javascript
// tests/load/upload_spike.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 200 },  // Ramp up
    { duration: '6m', target: 1000 }, // Spike
    { duration: '2m', target: 0 },    // Ramp down
  ],
};

export default function() {
  // Request presigned URL
  const presignRes = http.post(
    'https://api.photobomb.app/api/v1/upload/presign',
    JSON.stringify({
      filename: 'test.jpg',
      size_bytes: 1024000,
      mime_type: 'image/jpeg',
      sha256: `${__VU}_${__ITER}` // Unique per request
    }),
    { headers: { 'Authorization': `Bearer ${__ENV.AUTH_TOKEN}`, 'Content-Type': 'application/json' } }
  );
  
  check(presignRes, {
    'presign status is 200': (r) => r.status === 200,
  });
}
```

**Acceptance**: Queue depth should not exceed 500 jobs; all uploads processed within 5 min of spike end.

**Run Command**:
```bash
k6 run tests/load/upload_spike.js
```

## Security Tests

### OWASP ZAP Automated Scan

```bash
docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://api.photobomb.app \
  -r zap-report.html
```

**Check For**:
- SQL Injection
- XSS
- Insecure headers
- Unencrypted cookies

### Manual Penetration Testing

**Scenarios**:
1. **Broken Access Control**: Try accessing other users' photos by guessing IDs
2. **Presigned URL Abuse**: Try reusing expired presigned URLs
3. **Rate Limit Bypass**: Try login brute-force with different IPs
4. **Session Hijacking**: Try stealing JWT tokens via XSS (should fail due to `HttpOnly`)

## Performance Benchmarks

### Database Query Performance

**Target**: p95 < 100ms for common queries

**Test**:
```sql
EXPLAIN ANALYZE
SELECT * FROM photos 
WHERE user_id = 'uuid' AND deleted_at IS NULL 
ORDER BY taken_at DESC NULLS LAST 
LIMIT 50;
```

**Acceptance**: Execution time < 10ms (should use `idx_photos_user_taken`)

### Thumbnail Generation Benchmark

**Target**: 3 thumbnails × 3 formats = 9 outputs in < 500ms per photo

**Test**:
```bash
time python -m app.workers.thumbnail_worker \
  --input test-image-10mp.jpg \
  --sizes 256,512,1024 \
  --formats webp,avif,jpeg
```

**Acceptance**: Real time < 500ms on 4-core CPU

## Test Data Management

### Fixtures

**Backend**:
```python
# tests/conftest.py
import pytest
from tests.factories import UserFactory, PhotoFactory

@pytest.fixture
def user(db_session):
    return UserFactory()

@pytest.fixture
def auth_headers(user):
    token = create_jwt_token(user.user_id)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def existing_photo(user, db_session):
    return PhotoFactory(user_id=user.user_id, sha256="duplicate123")
```

**Frontend**:
```javascript
// tests/fixtures/photos.js
export const mockPhotos = [
  {
    photo_id: '1',
    filename: 'sunset.jpg',
    thumb_urls: { thumb_512: '/fixtures/sunset.webp' },
    taken_at: '2024-01-15T18:30:00Z',
  },
  // ... more
];
```

### Test Database Reset

**Before Each Test**:
```python
@pytest.fixture(autouse=True)
def reset_db(db_session):
    """Rollback DB after each test"""
    yield
    db_session.rollback()
```

## CI/CD Integration

**GitHub Actions Workflow** (already created):
- Unit tests run on every PR
- Integration tests run on merge to `main`
- E2E tests run post-deployment (staging)
- Load tests run weekly (scheduled)

**Coverage Requirements**:
- Backend: 80% (enforced by Codecov)
- Frontend: 70% (enforced by Jest)
- PRs blocked if coverage drops by > 5%

## Manual Testing Checklist

### Pre-Release QA

- [ ] Upload 10 MB photo → thumbnails appear within 30s
- [ ] Upload duplicate photo → shows "Already uploaded"
- [ ] Create album → add 20 photos → share link works
- [ ] Search by "San Francisco" → returns correct photos
- [ ] Face grouping: Enable → upload 10 photos → faces grouped
- [ ] PWA install on Android → works standalone
- [ ] iOS Add to Home → app launches, icon correct
- [ ] Offline upload → network returns → photo syncs
- [ ] Password-protected share → visitor enters password → granted access
- [ ] Expired share link → shows "Link expired"

### Browser Testing Matrix

| Browser | Desktop | Mobile |
|---------|---------|--------|
| Chrome | ✅ | ✅ (Android emulation) |
| Firefox | ✅ | ❌ (low priority) |
| Safari | ✅ | ✅ (iOS emulation) |
| Edge | ✅ | ❌ (Chromium-based, covered by Chrome) |

## Implementation Notes

**Why Playwright over Selenium?**
- Faster execution (auto-wait for elements)
- Better mobile emulation
- Built-in video recording for failed tests
- Modern API (async/await VS callback hell)

**Why k6 over JMeter?**
- Scripting in JavaScript (same language as frontend)
- Better cloud integration (k6 Cloud for distributed load tests)
- Smaller resource footprint

**Tradeoff: Unit test coverage**
- 80% backend coverage is strict but achievable
- Some edge cases (B2 API timeouts) hard to test → use integration tests

**Alternative**: Use testcontainers for integration tests (spin up real Postgres/Redis in Docker)
- Pro: Tests against real DB (not mocks)
- Con: Slower CI (Docker startup overhead)
- **Verdict**: Use for critical flows only (e.g., upload flow test)
