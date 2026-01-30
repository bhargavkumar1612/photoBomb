#!/bin/bash
set -e

# 1. Run Migrations
echo "📦 Running Database Migrations..."
echo "🔍 Debug: Listing migration files:"
ls -l alembic/versions/
alembic upgrade head

# 2. Start Celery Worker (Background)
# We use & to run it in the background so the script continues to Uvicorn
echo "👷 Starting Celery Worker..."
celery -A app.celery_app worker -Q high,low -c 2 --loglevel=info &

# 3. Start Web Server (Foreground)
# This processes web requests. If this crashes, the container restarts.
echo "🚀 Starting Uvicorn Web Server..."
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
