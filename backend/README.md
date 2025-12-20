# PhotoBomb Backend

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development without Docker)

### Running with Docker Compose

1. **Copy environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your B2 credentials
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

3. **Verify services are running**:
   ```bash
   docker-compose ps
   ```

4. **Test API**:
   ```bash
   curl http://localhost:8000/healthz
   ```

5. **View logs**:
   ```bash
   docker-compose logs -f api
   ```

### API Endpoints

- **Health Check**: `GET /healthz`
- **Register**: `POST /api/v1/auth/register`
- **Login**: `POST /api/v1/auth/login`
- **Refresh Token**: `POST /api/v1/auth/refresh`
- **Current User**: `GET /api/v1/auth/me`

### Testing Login Flow

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "full_name": "Test User"
  }'

# 2. Login (returns access_token)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123!"
  }'

# 3. Get current user (use access_token from step 2)
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Development

**Hot Reload**: Code changes auto-reload (FastAPI watches `/app` volume)

**Database Migrations**:
```bash
# Create migration
docker-compose exec api alembic revision --autogenerate -m "your message"

# Apply migrations
docker-compose exec api alembic upgrade head
```

**Run Tests**:
```bash
docker-compose exec api pytest tests/ -v
```

### Database Access

```bash
# psql into PostgreSQL
docker-compose exec postgres psql -U photobomb -d photobomb

# Example queries
SELECT * FROM users;
SELECT * FROM photos;
```

## Project Structure

```
backend/
├── app/
│   ├── api/           # API endpoints
│   │   ├── auth.py    # Authentication (register, login, refresh)
│   │   ├── upload.py  # Upload presign, confirm
│   │   └── photos.py  # Photos CRUD
│   ├── core/          # Core utilities
│   │   ├── config.py  # Settings
│   │   ├── database.py # DB connection
│   │   └── security.py # JWT, password hashing
│   ├── models/        # SQLAlchemy models
│   │   ├── user.py
│   │   └── photo.py
│   ├── services/      # Business logic
│   ├── workers/       # Celery tasks
│   └── main.py        # FastAPI app
├── tests/             # Test suite
├── Dockerfile
└── requirements.txt
```

## Next Steps

✅ Backend foundation created
🔄 Next: Upload API endpoints (presigned URLs)
🔄 Next: Photos CRUD endpoints
🔄 Next: Celery worker setup for thumbnail generation
