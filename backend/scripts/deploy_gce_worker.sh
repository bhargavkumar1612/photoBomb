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

# Stop and remove backend if running (shouldn't be on GCE)
if [ "$(sudo docker ps -q -f name=photobomb-backend)" ]; then
    echo "🛑 Removing backend container (should only be on Render)..."
    sudo docker stop photobomb-backend
    sudo docker rm photobomb-backend
fi

echo "⬇️ Pulling latest images..."
# We explicitly pull to ensure we get the latest
sudo docker compose pull worker redis

echo "▶️ Restarting services..."
# up -d checks for changes and recreates containers if needed
# --remove-orphans cleans up old containers not in the compose file
sudo docker compose up -d --remove-orphans worker redis

echo "🧹 Aggressive cleanup to free disk space..."
# Remove unused containers
sudo docker container prune -f

# Remove unused images (keeps only images used by running containers)
sudo docker image prune -a -f

# Remove unused volumes
sudo docker volume prune -f

# Remove build cache (can save significant space)
sudo docker builder prune -a -f

# Show disk usage after cleanup
echo "📊 Docker disk usage after cleanup:"
sudo docker system df

echo "✅ Deployment Complete!"
sudo docker compose ps
echo "--- Worker Logs ---"
sudo docker compose logs --tail 20 worker
