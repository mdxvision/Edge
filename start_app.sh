#!/bin/bash

# Kill any existing processes on ports 8080 and 5001 to avoid conflicts
lsof -ti:8080 | xargs kill -9 2>/dev/null
lsof -ti:5001 | xargs kill -9 2>/dev/null

cd /Users/rafaelrodriguez/GitHub/Edge

echo "=========================================="
echo "  EdgeBet Starting..."
echo "=========================================="
echo ""
echo "Backend: http://localhost:8080"
echo "Frontend: http://localhost:5001"
echo "API Docs: http://localhost:8080/docs"
echo ""
echo "Log file: $(pwd)/app.log"
echo "Watch logs in another terminal with:"
echo "  tail -f app.log"
echo ""
echo "=========================================="

# Start backend in background, output to both console and log file
./venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload 2>&1 | tee -a backend.log &
BACKEND_PID=$!

echo "Waiting for backend to initialize..."
sleep 5

echo "Starting Frontend..."
# Start frontend
cd /Users/rafaelrodriguez/GitHub/Edge/client
npm run dev

# When frontend stops, kill backend
kill $BACKEND_PID
