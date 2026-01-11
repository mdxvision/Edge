#!/bin/bash

# Kill any existing processes on ports 8080 and 5001 to avoid conflicts
lsof -ti:8080 | xargs kill -9 2>/dev/null
lsof -ti:5001 | xargs kill -9 2>/dev/null

echo "Starting Backend..."
# Start backend in background
cd /Users/rafaelrodriguez/GitHub/Edge
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload &
BACKEND_PID=$!

echo "Waiting for backend to initialize..."
sleep 5

echo "Starting Frontend..."
# Start frontend
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev

# When frontend stops, kill backend
kill $BACKEND_PID
