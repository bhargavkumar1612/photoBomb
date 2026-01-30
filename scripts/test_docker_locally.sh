#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

echo "========================================================"
echo "🧪  PhotoBomb Local Docker Testing"
echo "========================================================"

# 1. Build the Base Image
# We tag it exactly as the production Dockerfile expects so it can find it.
echo ""
echo "🏗️  Step 1: Building Base Image..."
echo "    (This downloads ~2GB of ML libraries. It may take 5-10 mins the first time.)"
docker build -t bhargavkumar1612/photobomb-base:latest -f backend/Dockerfile.base backend

# 2. Build the App Image
echo ""
echo "🚀 Step 2: Building Application Image..."
docker build -t photobomb-local -f backend/Dockerfile backend

# 3. Run the Container
echo ""
echo "🏃 Step 3: Running Container..."
echo "    Mapping port 8000:8000"
echo "    Using env file: backend/.env"
echo "    Press Ctrl+C to stop."
echo "========================================================"

docker run --rm -it \
  --env-file backend/.env \
  -e PORT=8000 \
  -p 8000:8000 \
  photobomb-local
