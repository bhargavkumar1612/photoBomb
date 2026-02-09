#!/bin/bash
set -e

# 1. Start Dummy Server (Background) to satisfy Render Web Service requirement
echo "🔌 Starting Dummy Server on port $PORT..."
python3 scripts/dummy_server.py &
SERVER_PID=$!

# 2. Start Celery Worker (Foreground)
# We run Celery in foreground so if it crashes, the container restarts.
# The dummy server is just a sidecar.
echo "👷 Starting Celery Worker..."
# Preload models (Separate process, no timeouts)
echo "📥 Preloading AI Models..."
python3 -m app.workers.model_loader || echo "⚠️ Model preload failed, worker will try to load on demand."

# Concurrency 1 and no-gossip/no-mingle to save memory
export DATABASE_POOL_SIZE=0
exec celery -A app.celery_app worker -Q high,low -c 1 --loglevel=info --without-gossip --without-mingle
