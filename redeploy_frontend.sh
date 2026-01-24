#!/bin/bash
set -e

echo "🧹 Cleaning previous build..."
rm -rf frontend/dist

echo "📦 Installing Frontend Dependencies..."
cd frontend
npm install

echo "🛠️  Building Frontend..."
npm run build

# Verify critical files exist
if [ ! -f "dist/registerSW.js" ]; then
    echo "❌ Error: registerSW.js missing from build output!"
    exit 1
fi
if [ ! -f "dist/manifest.webmanifest" ]; then
    echo "❌ Error: manifest.webmanifest missing from build output!"
    exit 1
fi

echo "✅ Build Successful."
ls -l dist/

cd ..

echo "🚀 Deploying to Cloudflare Workers..."
# Using npx to ensure we use the local wrangler version if available, or fetch it
npx wrangler deploy

echo "🎉 Deployment Complete!"
echo "👉 Please do a Hard Refresh (Cmd+Shift+R) on your site."
