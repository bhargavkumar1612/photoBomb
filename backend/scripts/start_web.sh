#!/bin/bash
set -e

# 1. Run Migrations
echo "📦 Running Database Migrations..."
alembic upgrade head

# 2. Start Web Server
echo "🚀 Starting Uvicorn Web Server..."
# Exec replaces the shell process, ensuring signals are passed correctly
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT
