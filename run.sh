#!/bin/bash

# AI Planning Assistant - Startup Script
# This script starts both the backend and frontend servers

set -e

cd "$(dirname "$0")"

echo "🚀 Starting AI Planning Assistant..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
echo "📦 Checking Python dependencies..."
pip install -q -r requirements.txt

# Check if frontend dependencies are installed
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend
    npm install
    cd ..
fi

# Initialize database if needed
echo "🗄️  Initializing database..."
python -c "from backend.database import init_db; init_db()"

echo ""
echo "✅ Setup complete!"
echo ""
echo "Starting servers..."
echo ""

# Start backend in background
echo "🔧 Starting backend on http://localhost:8000"
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
echo "🎨 Starting frontend on http://localhost:5173"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AI Planning Assistant is running!"
echo ""
echo "  📱 Frontend: http://localhost:5173"
echo "  🔌 Backend:  http://localhost:8000"
echo "  📚 API Docs: http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop all servers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "Goodbye! 👋"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for processes
wait
