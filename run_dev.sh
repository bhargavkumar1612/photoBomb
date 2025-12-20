#!/bin/bash

# Function to kill processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping PhotoBomb servers..."
    if [ -n "$BE_PID" ]; then
        kill $BE_PID 2>/dev/null
    fi
    if [ -n "$FE_PID" ]; then
        kill $FE_PID 2>/dev/null
    fi
    exit
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT

echo "🚀 Starting PhotoBomb Development Environment..."

# Check if port 8000 is free (Backend)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is busy. Please free it first."
    exit 1
fi

# Check if port 3000 is free (Frontend)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 3000 is busy. Please free it first."
    exit 1
fi

# Start Backend
echo "🐍 Starting Backend (http://localhost:8000)..."
cd backend
# Check if venv exists and activate it if so, otherwise assume system python
if [ -d "venv" ]; then
    source venv/bin/activate
fi
uvicorn app.main:app --reload --port 8000 &
BE_PID=$!
cd ..

# Start Frontend
echo "⚛️  Starting Frontend (http://localhost:3000)..."
cd frontend
npm run dev -- --port 3000 &
FE_PID=$!
cd ..

echo "✅ Servers are running!"
echo "   Backend: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   Press Ctrl+C to stop both."

# Keep script running to capture Ctrl+C
wait
