#!/bin/bash
cd "/Users/hunterdonia/Documents/untitled folder/planner_app"

# Activate virtual environment
source .venv/bin/activate

# Start backend in background
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait a moment then open browser
sleep 3
open http://localhost:5173

# Keep running until user closes
echo ""
echo "================================"
echo "  Planner App is running!"
echo "  Browser should open automatically"
echo "  Press Ctrl+C to stop"
echo "================================"
echo ""

wait
