#!/bin/bash
# Build and Push Worker Image to Docker Hub

# 1. Be in the backend directory
cd "$(dirname "$0")/.."

# Load env to get username if possible, else default
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# FORCE CORRECT USERNAME based on your successful login
USERNAME="bhargavkumar1612"
IMAGE="photobomb-worker"
TAG="latest"

FULL_IMAGE_NAME="$USERNAME/$IMAGE:$TAG"

echo "=================================================="
echo "🐳 Building Docker Image: $FULL_IMAGE_NAME"
echo "=================================================="

# Check if base image exists locally, if not warn
# (assuming base is built or pulled)

# Build for AMD64 (Standard Cloud Servers like GCE/DigitalOcean)
echo "🏗️ Building for Platform: Linux/AMD64"
# Using --load to ensure it is available locally if push fails, or --push to push directly
# We will use --push which builds and pushes in one step (requires buildx driver)
# If using default driver, we should build then push.
# Let's try standard build -t then push for maximum compatibility if buildx isn't fully set up with drivers
docker buildx build --platform linux/amd64 -f Dockerfile.worker -t $FULL_IMAGE_NAME --push .

if [ $? -eq 0 ]; then
    echo "✅ Build & Push Successful!"
else
    echo "❌ Build/Push Failed. Retrying with standard build..."
    # Fallback for standard docker 
    docker build -f Dockerfile.worker -t $FULL_IMAGE_NAME .
    docker push $FULL_IMAGE_NAME
fi

echo "=================================================="
echo "🚀 Pushing Only: $FULL_IMAGE_NAME"
echo "=================================================="
docker push $FULL_IMAGE_NAME

if [ $? -eq 0 ]; then
    echo "✅ Push Successful!"
    echo ""
    echo "💻 ON YOUR OTHER LAPTOP:"
    echo "1. Copy your .env file to the other laptop."
    echo "2. Run this command:"
    echo "   docker run -d --name photo-worker \\"
    echo "     --env-file .env \\"
    echo "     -e APP_ENV=production \\"
    echo "     --restart unless-stopped \\"
    echo "     $FULL_IMAGE_NAME"
else
    echo "❌ Push Failed. (Did you run 'docker login'?)"
    # exit 1
fi
