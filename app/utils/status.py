"""
Status normalization utilities for all sports.
"""

from datetime import datetime, timedelta


def normalize_status(status: str) -> str:
    """Convert ESPN/API status codes to user-friendly labels."""
    if not status:
        return "Scheduled"

    status_lower = status.lower()

    # Live game indicators
    if any(x in status_lower for x in ['in_progress', 'in progress', 'status_in_progress', 'live']):
        return "LIVE"
    if any(x in status_lower for x in ['end_period', 'halftime', 'intermission', 'end of']):
        return "LIVE"  # Between periods/halves is still live
    if any(x in status_lower for x in ['1st', '2nd', '3rd', '4th', 'ot', 'overtime', '1h', '2h']):
        return "LIVE"
    if 'paused' in status_lower:
        return "LIVE"

    # Final game indicators
    if any(x in status_lower for x in ['final', 'finished', 'status_final', 'complete', 'ft']):
        return "Final"

    # Scheduled
    if any(x in status_lower for x in ['scheduled', 'pre', 'status_scheduled', 'timed']):
        return "Scheduled"

    # If contains time, it's scheduled
    if 'pm' in status_lower or 'am' in status_lower or ':' in status:
        return status  # Keep the time display

    return status


def add_time_display(game_date_str: str) -> str:
    """Convert game date to EST display format."""
    if not game_date_str:
        return None
    try:
        dt = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
        est_dt = dt - timedelta(hours=5)
        return est_dt.strftime("%a, %b %d at %I:%M %p") + " EST"
    except:
        return None
