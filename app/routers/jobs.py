"""
Background jobs router for monitoring and controlling background tasks.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from app.db import User
from app.routers.auth import require_auth
from app.services.background_jobs import (
    get_jobs_status,
    start_all_jobs,
    stop_all_jobs,
    alert_scheduler,
    auto_settlement,
    notification_queue,
    odds_refresh_job
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobStatusResponse(BaseModel):
    alert_scheduler: Dict[str, Any]
    auto_settlement: Dict[str, Any]
    notification_queue: Dict[str, Any]
    odds_refresh: Dict[str, Any]


@router.get("/status", response_model=JobStatusResponse)
def get_status():
    """Get status of all background jobs."""
    return get_jobs_status()


@router.post("/start-all")
async def start_all_background_jobs(user: User = Depends(require_auth)):
    """Start all background jobs (admin only)."""
    # In production, add admin check
    await start_all_jobs()
    return {"message": "All background jobs started", "status": get_jobs_status()}


@router.post("/stop-all")
async def stop_all_background_jobs(user: User = Depends(require_auth)):
    """Stop all background jobs (admin only)."""
    # In production, add admin check
    await stop_all_jobs()
    return {"message": "All background jobs stopped", "status": get_jobs_status()}


@router.post("/alerts/start")
async def start_alert_scheduler(user: User = Depends(require_auth)):
    """Start the alert scheduler."""
    await alert_scheduler.start()
    return {"message": "Alert scheduler started"}


@router.post("/alerts/stop")
async def stop_alert_scheduler(user: User = Depends(require_auth)):
    """Stop the alert scheduler."""
    await alert_scheduler.stop()
    return {"message": "Alert scheduler stopped"}


@router.post("/settlement/start")
async def start_settlement_checker(user: User = Depends(require_auth)):
    """Start the auto-settlement checker."""
    await auto_settlement.start()
    return {"message": "Auto-settlement checker started"}


@router.post("/settlement/stop")
async def stop_settlement_checker(user: User = Depends(require_auth)):
    """Stop the auto-settlement checker."""
    await auto_settlement.stop()
    return {"message": "Auto-settlement checker stopped"}


@router.post("/odds/start")
async def start_odds_refresh(user: User = Depends(require_auth)):
    """Start the odds refresh job."""
    await odds_refresh_job.start()
    return {"message": "Odds refresh job started"}


@router.post("/odds/stop")
async def stop_odds_refresh(user: User = Depends(require_auth)):
    """Stop the odds refresh job."""
    await odds_refresh_job.stop()
    return {"message": "Odds refresh job stopped"}
