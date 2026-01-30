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
    if [ -n "$WORKER_PID" ]; then
        kill $WORKER_PID 2>/dev/null
    fi
    exit
}

# Trap Ctrl+C (SIGINT)
trap cleanup SIGINT

echo "🚀 Starting PhotoBomb Development Environment..."

# Check if port 8000 is free (Backend)
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 8000 is busy. Killing process..."
    PID=$(lsof -ti:8000)
    kill -9 $PID
    
    # Wait for port to be free
    while lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null; do
        sleep 0.1
    done
    echo "✅ Port 8000 freed."
fi

# Check if port 3000 is free (Frontend)
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 3000 is busy. Please free it first."
    kill $(lsof -ti:3000)
    # exit 1
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
 
# Start Celery Worker
echo "👷 Starting Celery Worker..."
cd backend
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
celery -A app.celery_app worker --loglevel=info --pool=solo -Q high,low,celery &
WORKER_PID=$!
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
