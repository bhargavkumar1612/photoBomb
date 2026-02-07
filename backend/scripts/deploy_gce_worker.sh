#!/bin/bash
# Script to update and restart the worker on GCE
# Run this script ON the GCE server (or via SSH)

CONTAINER_NAME="photo-worker"
IMAGE_NAME="bhargavkumar1612/photobomb-worker:latest"

echo "🚀 Starting Worker Deployment..."

# 1. Stop existing container
if [ "$(sudo docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "🛑 Stopping existing container..."
    sudo docker stop $CONTAINER_NAME
fi

# 2. Remove existing container
if [ "$(sudo docker ps -aq -f name=$CONTAINER_NAME)" ]; then
    echo "🗑️ Removing existing container..."
    sudo docker rm $CONTAINER_NAME
fi

# 3. Pull latest image
echo "⬇️ Pulling latest image..."
sudo docker pull $IMAGE_NAME

# 4. Run new container
echo "▶️ Starting new worker..."
# Ensure .env exists
if [ ! -f .env ]; then
    echo "⚠️ Warning: .env file not found in current directory!"
fi

# Ensure network exists
sudo docker network create photobomb_default || true

sudo docker run -d \
  --name $CONTAINER_NAME \
  --env-file .env \
  -e APP_ENV=production \
  --network photobomb_default \
  --restart unless-stopped \
  $IMAGE_NAME

# 5. Cleanup old images to save disk space (Critical for Free Tier)
echo "🧹 Cleaning up old images..."
sudo docker image prune -f

echo "✅ Deployment Complete!"
sudo docker logs --tail 20 $CONTAINER_NAME
