#!/bin/bash
# Script to run the Celery Worker Locally in "Hybrid Mode"
# Connects to Production DB/Redis/storage but runs compute on your machine.

# 1. Be in the backend directory
cd "$(dirname "$0")/.."

# 2. Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found in backend directory!"
    echo "Please ensure you have a .env file with your PRODUCTION credentials (Supabase DB, Redis, B2)."
    exit 1
fi

# 3. Export variables from .env
echo "Loading environment variables..."
set -a
source .env
set +a

# 4. OVERRIDE variables for Hybrid Mode
# We want to behave like Production
export APP_ENV=production
# Force specific settings if needed (ensure these match your Render Dashboard!)
# export DB_SCHEMA=public  <-- Uncomment if your prod DB uses 'public' or ensure .env matches Render
# export STORAGE_PATH_PREFIX=uploads <-- Ensure this matches Render too

echo "=================================================="
echo "🚀 Starting Hybrid Worker"
echo "   - Connection: Production Database"
echo "   - Mode: $APP_ENV"
echo "   - Memory: Unbounded (System RAM)"
echo "=================================================="

# 5. Run Celery
# Note: Ensure you have installed requirements: pip install -r requirements.worker.txt
celery -A app.celery.celery_app worker --loglevel=info -P gevent -c 10
