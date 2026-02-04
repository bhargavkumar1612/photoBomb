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
# Concurrency 1 and no-gossip/no-mingle to save memory
exec celery -A app.celery_app worker -Q high,low -c 1 --loglevel=info --without-gossip --without-mingle
