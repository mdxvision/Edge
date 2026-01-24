#!/bin/bash
# Watch application logs in real-time
# Usage: ./watch_logs.sh [filter]
# Examples:
#   ./watch_logs.sh           # Show all logs
#   ./watch_logs.sh ERROR     # Only show errors
#   ./watch_logs.sh auth      # Filter for auth-related logs

cd /Users/rafaelrodriguez/GitHub/Edge

if [ -z "$1" ]; then
    echo "Watching all logs... (Ctrl+C to stop)"
    tail -f app.log
else
    echo "Watching logs filtered by: $1 (Ctrl+C to stop)"
    tail -f app.log | grep --line-buffered -i "$1"
fi
