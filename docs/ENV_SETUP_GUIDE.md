# Environment Variables Setup Guide

This guide shows you how to collect all required environment variables for PhotoBomb.

---

## 🗄️ Database (Supabase)

### Step 1: Create Supabase Project

1. Go to https://supabase.com
2. Click **"Start your project"** (free tier available)
3. Create new project:
   - **Name**: `photobomb`
   - **Database Password**: Generate strong password (save it!)
   - **Region**: Choose closest to you
   - Click **"Create new project"** (takes ~2 minutes)

### Step 2: Get Connection String

1. In Supabase dashboard, go to **Settings** → **Database**
2. Scroll to **Connection String** section
3. Select **"URI"** tab
4. Copy the connection string (looks like):
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```

5. **Convert to async format** for our app:
   ```bash
   # Change from:
   postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
   
   # To (add +asyncpg):
   postgresql+asyncpg://postgres:password@db.xxx.supabase.co:5432/postgres
   ```

6. In your `.env` file:
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@db.xxx.supabase.co:5432/postgres
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=10
   ```

### Step 3: Enable Required Extensions (Supabase)

1. In Supabase dashboard, go to **Database** → **Extensions**
2. Search and enable these extensions:
   - ✅ **pg_trgm** (text search)
   - ✅ **btree_gin** (composite indexes)
3. For **pgvector** (face recognition):
   - Go to SQL Editor
   - Run: `CREATE EXTENSION IF NOT EXISTS vector;`

---

## 🔴 Redis (Upstash - Free Tier)

Since you're using Supabase, you'll need a Redis service for Celery. **Upstash** offers free Redis.

### Step 1: Create Upstash Account

1. Go to https://upstash.com
2. Sign up (free tier: 10,000 commands/day)
3. Click **"Create Database"**
   - **Name**: `photobomb-redis`
   - **Type**: Regional
   - **Region**: Choose same as Supabase
   - Click **"Create"**

### Step 2: Get Connection URL

1. Click on your database
2. Scroll to **"REST API"** section
3. Copy **"UPSTASH_REDIS_REST_URL"** or use connection string format
4. In your `.env`:
   ```bash
   REDIS_URL=redis://default:YOUR_UPSTASH_PASSWORD@your-region.upstash.io:6379
   ```

**Alternative: Redis Labs (also free tier)**
- https://redis.com/try-free/
- Similar process, get connection URL

---

## 📦 Backblaze B2 (Object Storage)

### Step 1: Create B2 Account

1. Go to https://www.backblaze.com/b2/sign-up.html
2. Sign up (free: 10 GB storage, 1 GB download/day)
3. Verify email

### Step 2: Create Bucket

1. Login to B2 dashboard
2. Click **"Buckets"** → **"Create a Bucket"**
3. Settings:
   - **Bucket Unique Name**: `photobomb-production-YOUR-GCE_USERNAME` (must be globally unique)
   - **Files in Bucket**: **Private** ✅ (important for security)
   - **Default Encryption**: Disabled (we'll handle encryption)
   - **Object Lock**: Disabled
4. Click **"Create a Bucket"**
5. **Save the Bucket ID** (shows after creation)

### Step 3: Generate Application Key

1. Go to **"App Keys"** in left sidebar
2. Click **"Add a New Application Key"**
3. Settings:
   - **Name of Key**: `photobomb-production-key`
   - **Allow access to Bucket(s)**: Select your bucket only
   - **Type of Access**: **Read and Write** ✅
   - **Allow List All Bucket Names**: Yes
   - **File name prefix**: Leave empty
   - **Duration**: Leave empty (no expiration)
4. Click **"Create New Key"**

5. **IMPORTANT**: Copy these values immediately (you won't see them again!):
   - `keyID` → This is your `B2_APPLICATION_KEY_ID`
   - `applicationKey` → This is your `B2_APPLICATION_KEY`

6. In your `.env`:
   ```bash
   B2_APPLICATION_KEY_ID=001234567890abcdef000000001
   B2_APPLICATION_KEY=K001aBcDeFgHiJkLmNoPqRsTuVwXyZ
   B2_BUCKET_NAME=photobomb-production-yourname
   B2_BUCKET_ID=abcdef1234567890
   ```

---

## 🔐 JWT Secret Key

Generate a secure random key for JWT tokens.

### Method 1: Using OpenSSL (Mac/Linux)
```bash
openssl rand -hex 32
```

### Method 2: Using Python
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### Method 3: Using Node.js
```bash
node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"
```

Copy the output and add to `.env`:
```bash
JWT_SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

**CRITICAL**: Keep this secret! Don't commit to git, don't share publicly.

---

## 🔑 OAuth (Optional - Can Skip for MVP)

Only needed if you want Google/Apple login.

### Google OAuth (Optional)

1. Go to https://console.cloud.google.com
2. Create new project: **"PhotoBomb"**
3. Enable Google+ API
4. Go to **Credentials** → **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure consent screen (choose External)
6. Application type: **Web application**
7. Add authorized redirect URI: `http://localhost:8000/api/v1/auth/google/callback`
8. Copy Client ID and Client Secret

```bash
GOOGLE_CLIENT_ID=123456789012-abcdefghijklmnop.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-aBcDeFgHiJkLmNoPqRsTuVwXyZ
```

### Apple OAuth (Optional)

Skip for now unless you need it - more complex setup.

---

## ⚙️ App Configuration

These are straightforward settings:

```bash
# App Config
APP_NAME=PhotoBomb
APP_ENV=development  # Change to 'production' when deploying
DEBUG=true           # Change to 'false' in production
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Storage limits
DEFAULT_STORAGE_QUOTA_GB=100  # Per user storage limit
MAX_FILE_SIZE_MB=50           # Max single file size

# Face Recognition (can disable for MVP)
FACE_RECOGNITION_ENABLED=false  # Set to false initially
FACE_MODEL_PATH=./models/arcface_r100_v1.onnx
```

---

## 📝 Complete .env File Template (with Supabase & Upstash)

Copy this and fill in your values:

```bash
# Database (Supabase)
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_SUPABASE_PASSWORD@db.YOUR_PROJECT.supabase.co:5432/postgres
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis (Upstash)
REDIS_URL=redis://default:YOUR_UPSTASH_PASSWORD@YOUR_REGION.upstash.io:6379

# JWT (Generate with: openssl rand -hex 32)
JWT_SECRET_KEY=YOUR_GENERATED_SECRET_HERE
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Backblaze B2
B2_APPLICATION_KEY_ID=YOUR_B2_KEY_ID
B2_APPLICATION_KEY=YOUR_B2_APPLICATION_KEY
B2_BUCKET_NAME=photobomb-production-yourname
B2_BUCKET_ID=YOUR_BUCKET_ID

# OAuth (Optional - can leave empty)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
APPLE_CLIENT_ID=
APPLE_CLIENT_SECRET=

# App Config
APP_NAME=PhotoBomb
APP_ENV=development
DEBUG=true
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Storage
DEFAULT_STORAGE_QUOTA_GB=100
MAX_FILE_SIZE_MB=50

# Face Recognition (disable for now)
FACE_RECOGNITION_ENABLED=false
FACE_MODEL_PATH=./models/arcface_r100_v1.onnx
```

---

## ✅ Checklist

- [ ] Supabase project created
- [ ] Supabase connection URL copied (with `+asyncpg`)
- [ ] pgvector extension enabled in Supabase
- [ ] Upstash Redis created
- [ ] Redis URL copied
- [ ] B2 account created
- [ ] B2 bucket created (private)
- [ ] B2 application key generated
- [ ] B2 credentials saved
- [ ] JWT secret generated (openssl rand -hex 32)
- [ ] All values added to `backend/.env`
- [ ] `.env` file NOT committed to git (check `.gitignore`)

---

## 🧪 Testing Your Configuration

After setting up `.env`:

```bash
# 1. Test database connection
cd backend
python3 -c "from app.core.config import settings; print(settings.DATABASE_URL)"
# Should print your Supabase URL

# 2. Test B2 credentials
python3 -c "from app.services.b2_service import b2_service; b2_service.authorize(); print('✓ B2 connected')"
# Should print: ✓ B2 connected

# 3. Start app and check health
docker-compose up -d api
curl http://localhost:8000/healthz
# Should return: {"status":"healthy"}
```

---

## 🚨 Security Notes

1. **Never commit `.env` file** - it's in `.gitignore`
2. **Use different secrets** for development vs production
3. **Rotate secrets regularly** (every 90 days recommended)
4. **Keep B2 bucket private** - never make it public
5. **Use strong passwords** for Supabase

---

## 💰 Cost Breakdown (Free Tiers)

| Service | Free Tier | Paid Starts At |
|---------|-----------|----------------|
| **Supabase** | 500 MB DB, 1 GB storage | $25/mo (8 GB DB) |
| **Upstash Redis** | 10k commands/day | $0.20 per 100k commands |
| **Backblaze B2** | 10 GB storage, 1 GB egress/day | $5/TB/month |

**Estimated MVP cost**: $0 - $10/month (within free tiers)

---

## 🔄 Migration to Supabase

Since you're using Supabase instead of Docker PostgreSQL:

```bash
# Don't use docker-compose for database
# Instead, run migrations directly against Supabase:

cd backend

# Install dependencies locally (if not using Docker for API)
pip install -r requirements.txt

# Run migrations against Supabase
alembic upgrade head

# Verify
alembic current
```

---

## 📞 Need Help?

**Supabase Issues:**
- Dashboard: https://app.supabase.com
- Docs: https://supabase.com/docs
- Support: https://supabase.com/support

**B2 Issues:**
- Dashboard: https://secure.backblaze.com/b2_buckets.htm
- Docs: https://www.backblaze.com/b2/docs/
- Support: help@backblaze.com

**Upstash Issues:**
- Dashboard: https://console.upstash.com
- Docs: https://docs.upstash.com
- Support: support@upstash.com
