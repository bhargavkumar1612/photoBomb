#!/bin/bash
# Script to update and restart the worker + redis on GCE
# This script assumes docker-compose.yml and .env are present in the current directory

echo "🚀 Starting Deployment (Redis + Worker)..."

# Ensure .env exists
if [ ! -f .env ]; then
    echo "⚠️ Warning: .env file not found in current directory!"
fi

# Check if docker-compose.yml exists
if [ ! -f docker-compose.yml ]; then
    echo "❌ Error: docker-compose.yml not found!"
    exit 1
fi

# Stop legacy container if running (from old deployment method)
if [ "$(sudo docker ps -q -f name=photo-worker)" ]; then
    echo "🛑 Stopping legacy 'photo-worker' container..."
    sudo docker stop photo-worker
    sudo docker rm photo-worker
fi

echo "⬇️ Pulling latest images..."
# We explicitly pull to ensure we get the latest
sudo docker compose pull worker redis

echo "▶️ Restarting services..."
# up -d checks for changes and recreates containers if needed
# --remove-orphans cleans up old containers not in the compose file
sudo docker compose up -d --remove-orphans worker redis

echo "🧹 Cleaning up old images..."
sudo docker image prune -f

echo "✅ Deployment Complete!"
sudo docker compose ps
echo "--- Worker Logs ---"
sudo docker compose logs --tail 20 worker
