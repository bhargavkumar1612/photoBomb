#!/bin/bash
set -e

# 1. Run Migrations
echo "📦 Running Database Migrations..."
alembic upgrade head

# 2. Start Celery Worker (Background)
# We run in background with & and track the PID
echo "👷 Starting Celery Worker..."
celery -A app.celery_app worker -Q high,low -c 1 --loglevel=info &
CELERY_PID=$!

# 3. Start Web Server (Background)
# We also run Uvicorn in background so we can wait on both
echo "🚀 Starting Uvicorn Web Server..."
uvicorn app.main:app --host 0.0.0.0 --port $PORT &
UVICORN_PID=$!

# 4. Monitor Processes
# "wait -n" waits for the *first* background process to exit.
# If either Celery or Uvicorn crashes, this script will exit, causing the container to restart.
wait -n

# Exit with the status of the process that exited first
exit $?
