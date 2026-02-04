#!/bin/bash
# Script to build and push the Base Image for Multiple Architectures (specifically AMD64 for GCE)

# 1. Be in the root directory (so we can copy requirements if needed)
cd "$(dirname "$0")/../.."

IMAGE_NAME="bhargavkumar1612/photobomb-base:v1"

echo "=================================================="
echo "🚀 Building Base Image: $IMAGE_NAME"
echo "   - Platform: linux/amd64 (Required for GCE)"
echo "   - Context: backend/"
echo "=================================================="

# 2. Build multi-arch image (or just amd64)
# We use --push immediately because multi-arch builds often require pushing to a registry
docker buildx build \
  --platform linux/amd64 \
  -f backend/Dockerfile.base \
  -t $IMAGE_NAME \
  --push \
  backend/

echo "=================================================="
echo "✅ Base Image Published Successfully!"
echo "   You can now run: ./backend/scripts/publish_worker.sh"
echo "=================================================="
