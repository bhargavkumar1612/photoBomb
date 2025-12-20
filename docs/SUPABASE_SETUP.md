# Supabase Setup Guide for PhotoBomb

Complete guide for setting up PhotoBomb with Supabase using a custom `photobomb` schema.

---

## 🎯 Overview

All PhotoBomb tables will be created in a dedicated `photobomb` schema in Supabase. This keeps your tables organized and separate from Supabase's system tables.

---

## 📝 Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Click **"New project"**
3. Fill in details:
   - **Name**: `photobomb`
   - **Database Password**: Generate strong password (**save this!**)
   - **Region**: Choose closest to you (e.g., us-east-1)
4. Click **"Create new project"** (takes ~2 minutes)

---

## 🔧 Step 2: Get Database Connection URL

1. In Supabase dashboard, go to **Project Settings** (gear icon) → **Database**
2. Scroll to **Connection string** section
3. Select **URI** tab
4. Copy the connection string (looks like):
   ```
   postgresql://postgres.[PROJECT-REF]:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

5. **Convert to async format** for FastAPI:
   ```bash
   # Original from Supabase:
   postgresql://postgres.[REF]:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   
   # Add +asyncpg for our app:
   postgresql+asyncpg://postgres.[REF]:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

6. **Add to `.env` file**:
   ```bash
   cd backend
   cp .env.example .env
   nano .env
   
   # Update this line:
   DATABASE_URL=postgresql+asyncpg://postgres.[REF]:YOUR_PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
   ```

---

## 🔌 Step 3: Enable Required Extensions

1. In Supabase dashboard, go to **Database** (left sidebar) → **Extensions**
2. Search and enable:
   - ✅ `pg_trgm` (for text search)
   - ✅ `btree_gin` (for composite indexes)

3. For **pgvector** (needed for face recognition):
   - Go to **SQL Editor** (left sidebar)
   - Click **"New query"**
   - Paste and run:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Click **"Run"** or press Cmd+Enter

---

## 📊 Step 4: Run Migrations to Create photobomb Schema

Our migration will automatically create the `photobomb` schema and all tables.

### Option A: Using Local Python (Recommended)

```bash
cd /Users/bhargavkumartatikonda/Desktop/learning/photoBomb/backend

# Install dependencies (if not already)
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Verify
alembic current
# Should show: 001 (head)
```

### Option B: Using Docker

```bash
# If using Docker for backend
docker-compose up -d api
docker-compose exec api alembic upgrade head
```

---

## ✅ Step 5: Verify Schema Created

1. In Supabase dashboard, go to **Table Editor** → **Schema** dropdown
2. You should see:
   - `public` (Supabase's default)
   - `photobomb` ← **Your schema!**

3. Select `photobomb` schema
4. Verify these 3 tables exist:
   - ✅ `users`
   - ✅ `photos`
   - ✅ `photo_files`

---

## 🔍 Step 6: Inspect Tables (Optional)

### Via Supabase UI:

1. Select `photobomb` schema in dropdown
2. Click each table to see structure

### Via SQL Editor:

```sql
-- Set search path to photobomb schema
SET search_path TO photobomb;

-- List all tables
SELECT tablename FROM pg_tables WHERE schemaname = 'photobomb';

-- View users table structure
\d photobomb.users;

-- View photos table structure  
\d photobomb.photos;

-- View indexes
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE schemaname = 'photobomb';
```

---

## 🧪 Step 7: Test Connection

```bash
cd backend

# Test database connectivity
python3 << EOF
from app.core.config import settings
from app.core.database import engine
import asyncio

async def test_connection():
    async with engine.begin() as conn:
        result = await conn.execute("SELECT current_schema(), current_database()")
        row = result.first()
        print(f"✓ Connected to database: {row[1]}")
        print(f"✓ Current schema: {row[0]}")
        
        # Test photobomb schema exists
        result = await conn.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name = 'photobomb'
        """)
        if result.first():
            print("✓ photobomb schema exists")
        
        # Count tables
        result = await conn.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'photobomb'
        """)
        count = result.scalar()
        print(f"✓ Found {count} tables in photobomb schema")

asyncio.run(test_connection())
EOF
```

Expected output:
```
✓ Connected to database: postgres
✓ Current schema: public
✓ photobomb schema exists
✓ Found 3 tables in photobomb schema
```

---

## 📝 Complete .env Configuration

Your `backend/.env` should look like:

```bash
# Database (Supabase with photobomb schema)
DATABASE_URL=postgresql+asyncpg://postgres.[REF]:PASSWORD@aws-0-us-east-1.pooler.supabase.com:6543/postgres
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis (get from Upstash - see ENV_SETUP_GUIDE.md)
REDIS_URL=redis://default:PASSWORD@region.upstash.io:6379

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your_generated_secret_here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Backblaze B2 (see ENV_SETUP_GUIDE.md)
B2_APPLICATION_KEY_ID=your_key_id
B2_APPLICATION_KEY=your_application_key
B2_BUCKET_NAME=photobomb-prod-yourname
B2_BUCKET_ID=your_bucket_id

# OAuth (optional - can leave empty)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# App Config
APP_NAME=PhotoBomb
APP_ENV=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000

# Storage
DEFAULT_STORAGE_QUOTA_GB=100
MAX_FILE_SIZE_MB=50

# Face Recognition
FACE_RECOGNITION_ENABLED=false
```

---

## 🚨 Important Notes

### Schema Search Path

SQLAlchemy automatically handles the schema prefix. Our models specify `{'schema': 'photobomb'}` so queries like:

```python
select(User).where(User.email == "test@example.com")
```

Automatically become:
```sql
SELECT * FROM photobomb.users WHERE email = 'test@example.com'
```

### Supabase Dashboard

When using Table Editor or SQL Editor in Supabase:
- **Always select `photobomb` schema** from dropdown
- Default is `public` schema where Supabase system tables live

### Row Level Security (RLS)

Supabase enables RLS by default. For PhotoBomb, our backend handles authentication, so:

```sql
-- Disable RLS for photobomb schema (run in SQL Editor)
ALTER TABLE photobomb.users DISABLE ROW LEVEL SECURITY;
ALTER TABLE photobomb.photos DISABLE ROW LEVEL SECURITY;
ALTER TABLE photobomb.photo_files DISABLE ROW LEVEL SECURITY;
```

This allows our backend full access. Frontend never accesses DB directly.

---

## ✅ Verification Checklist

- [ ] Supabase project created
- [ ] Database password saved
- [ ] Connection URL copied and converted (+asyncpg)
- [ ] Extensions enabled (pg_trgm, btree_gin, vector)
- [ ] DATABASE_URL added to backend/.env
- [ ] Migrations run successfully (alembic upgrade head)
- [ ] photobomb schema visible in Supabase
- [ ] 3 tables created (users, photos, photo_files)
- [ ] RLS disabled for photobomb tables
- [ ] Connection test passed

---

## 🐛 Troubleshooting

**Migration fails with "relation already exists":**
```bash
# Drop schema and retry
# In Supabase SQL Editor:
DROP SCHEMA IF EXISTS photobomb CASCADE;

# Then re-run
alembic upgrade head
```

**Can't see photobomb schema in Supabase UI:**
- Refresh the page
- Check SQL Editor: `SELECT schema_name FROM information_schema.schemata;`

**Connection timeout:**
- Verify DATABASE_URL correctness
- Check if Supabase project is paused (free tier pauses after inactivity)
- Go to Supabase project dashboard to wake it up

**"peer authentication failed":**
- Ensure you're using the pooler connection string (port 6543)
- Password must be URL-encoded if it contains special characters

---

## 📊 Schema Diagram

```
photobomb (schema)
├── users
│   ├── user_id (PK)
│   ├── email (unique)
│   ├── password_hash
│   ├── storage_quota_bytes
│   └── storage_used_bytes
│
├── photos
│   ├── photo_id (PK)
│   ├── user_id (FK → photobomb.users)
│   ├── filename
│   ├── sha256 (for deduplication)
│   ├── exif data
│   └── gps coordinates
│
└── photo_files
    ├── file_id (PK)
    ├── photo_id (FK → photobomb.photos)
    ├── variant (original, thumb_256, etc)
    ├── b2_key (path in Backblaze)
    └── dimensions
```

---

## 🎉 Next Steps

Once schema is created:

1. **Start the backend**:
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Test registration**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{
       "email": "test@photobomb.app",
       "password": "SecurePass123!",
       "full_name": "Test User"
     }'
   ```

3. **Check Supabase**:
   - Go to Table Editor → photobomb → users
   - You should see your new user!

4. **Start frontend** and test full flow

---

**Got it working? Continue with [QUICKSTART.md](QUICKSTART.md) for frontend setup!**
