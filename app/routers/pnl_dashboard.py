"""
P&L Dashboard Router

Comprehensive profit/loss tracking and analytics endpoints.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
import io

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.pnl_dashboard import (
    TimeFrame,
    get_pnl_summary,
    get_roi_by_market_type,
    get_roi_by_sport,
    get_roi_by_sportsbook,
    get_streak_analysis,
    get_unit_tracking,
    export_bets_csv,
    get_performance_by_odds_range,
    get_dashboard_summary,
)
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/pnl", tags=["P&L Dashboard"])


@router.get("/summary")
def get_summary(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get P&L summary for a time period.

    Includes:
    - Overall stats (bets, wins, losses, ROI)
    - Daily breakdown with cumulative profit
    - Comparison to previous period

    **Timeframes:**
    - today, yesterday
    - this_week, last_week
    - this_month, last_month
    - last_30_days, last_90_days
    - this_year, all_time
    """
    return get_pnl_summary(db, user.id, timeframe, currency)


@router.get("/dashboard")
def get_full_dashboard(
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get complete P&L dashboard in a single call.

    Returns comprehensive analytics including:
    - All-time and recent P&L summaries
    - ROI by sport, market type, and sportsbook
    - Performance by odds range
    - Streak analysis
    - Unit tracking

    Use this for dashboard views that need all data at once.
    """
    return get_dashboard_summary(db, user.id, currency)


@router.get("/roi/by-sport")
def get_sport_roi(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get ROI breakdown by sport.

    Shows performance for each sport you've bet on:
    - Win rate
    - ROI percentage
    - Total staked and profit
    """
    return get_roi_by_sport(db, user.id, timeframe, currency)


@router.get("/roi/by-market")
def get_market_roi(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get ROI breakdown by market/bet type.

    Shows performance for each bet type:
    - Spread, Moneyline, Totals, Props, etc.
    - Win rate and ROI for each type
    - Identify your most profitable markets
    """
    return get_roi_by_market_type(db, user.id, timeframe, currency)


@router.get("/roi/by-sportsbook")
def get_sportsbook_roi(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get ROI breakdown by sportsbook.

    Compare your performance across different sportsbooks.
    """
    return get_roi_by_sportsbook(db, user.id, timeframe, currency)


@router.get("/roi/by-odds")
def get_odds_performance(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get performance by odds range.

    Analyzes your success rate and ROI across different odds ranges:
    - Heavy Favorites (-500 to -200)
    - Moderate Favorites (-199 to -120)
    - Small Favorites (-119 to -100)
    - Pick 'em (-99 to +100)
    - Small Underdogs (+101 to +150)
    - Moderate Underdogs (+151 to +250)
    - Large Underdogs (+251 to +500)
    - Longshots (+501+)

    Helps identify which odds ranges are most profitable for you.
    """
    return get_performance_by_odds_range(db, user.id, timeframe, currency)


@router.get("/streaks")
def get_streaks(
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive streak analysis.

    Returns:
    - Current streak (winning or losing)
    - Best winning streak (length and profit)
    - Worst losing streak
    - Top 5 win/lose streaks
    - Hot periods (70%+ win rate over 10 bets)
    - Cold periods (30%- win rate over 10 bets)

    Use this to understand your betting patterns and momentum.
    """
    return get_streak_analysis(db, user.id, currency)


@router.get("/units")
def get_units(
    base_unit: float = Query(100.0, gt=0, description="Base unit amount"),
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    currency: str = Query("USD", description="Currency for amounts"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get unit-based tracking.

    Converts all bets to standardized units for easier comparison.
    Set your base unit (default $100) to see:
    - Total units wagered
    - Units won/lost
    - Net units
    - ROI in units
    - Recent bet history in units

    **Example:** With a $100 base unit, a $250 bet = 2.5 units.
    """
    return get_unit_tracking(db, user.id, base_unit, timeframe, currency)


@router.get("/export/csv")
def export_csv(
    timeframe: TimeFrame = Query(TimeFrame.ALL_TIME, description="Time period"),
    include_pending: bool = Query(False, description="Include pending bets"),
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Export betting history to CSV.

    Downloads a CSV file with all your bets including:
    - Date placed/settled
    - Sport, bet type, selection
    - Odds, stake, profit/loss
    - Sportsbook, notes

    Perfect for:
    - External analysis in Excel/Sheets
    - Record keeping
    - Tax documentation
    """
    csv_data = export_bets_csv(db, user.id, timeframe, include_pending)

    # Create streaming response for download
    output = io.StringIO(csv_data)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=betting_history_{timeframe.value}.csv"
        }
    )


@router.get("/timeframes")
def list_timeframes():
    """
    List available timeframes for P&L analysis.
    """
    return {
        "timeframes": [
            {"value": "today", "label": "Today"},
            {"value": "yesterday", "label": "Yesterday"},
            {"value": "this_week", "label": "This Week"},
            {"value": "last_week", "label": "Last Week"},
            {"value": "this_month", "label": "This Month"},
            {"value": "last_month", "label": "Last Month"},
            {"value": "last_30_days", "label": "Last 30 Days"},
            {"value": "last_90_days", "label": "Last 90 Days"},
            {"value": "this_year", "label": "This Year"},
            {"value": "all_time", "label": "All Time"}
        ]
    }
