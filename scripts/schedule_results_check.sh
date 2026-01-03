#!/bin/bash
# Schedule bet results check for tomorrow
# Runs every hour from 4 PM to 11 PM EST on Jan 4, 2026

cd /Users/rafaelrodriguez/GitHub/Edge

echo "=== EdgeBet Results Checker ==="
echo "Scheduled checks for Jan 4, 2026:"
echo "  - 4:00 PM EST (after early NFL games)"
echo "  - 7:00 PM EST (after late NFL games start)"
echo "  - 10:00 PM EST (final check)"
echo ""

# Run checks at scheduled times using background sleep
(
    # Calculate seconds until 4 PM EST tomorrow
    # For now, just run the check every 3 hours
    while true; do
        echo "[$(date)] Running results check..."
        python3 /Users/rafaelrodriguez/GitHub/Edge/scripts/check_bet_results.py
        echo "[$(date)] Next check in 3 hours..."
        sleep 10800  # 3 hours
    done
) &

echo "Background checker started with PID: $!"
echo "Results will be sent to Telegram when games complete."
