#!/bin/bash
# Monitor games and settle when they finish

cd /Users/rafaelrodriguez/GitHub/Edge

echo "Starting game monitor at $(date)"
echo "Will check every 2 minutes..."
echo ""

while true; do
    echo "=== Check at $(date) ==="
    python3 scripts/settle_tonight.py 2>&1
    
    # Check if all settled
    PENDING=$(python3 -c "
from app.db import engine
from sqlalchemy import text
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT COUNT(*) FROM tracked_picks 
        WHERE status = \"pending\" 
        AND pick_team IN (\"Cleveland Cavaliers\", \"Milwaukee Bucks\", \"New York Knicks\", \"Denver Nuggets\", \"Indiana Pacers\")
    '''))
    print(result.scalar())
" 2>/dev/null)
    
    if [ "$PENDING" = "0" ]; then
        echo ""
        echo "All picks settled! Exiting monitor."
        break
    fi
    
    echo ""
    echo "Waiting 2 minutes before next check..."
    sleep 120
done
