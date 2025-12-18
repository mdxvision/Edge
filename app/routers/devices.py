"""
Devices Router

Manages device registration for push notifications.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.db import get_db, User
from app.routers.auth import require_auth
from app.services.push_notifications import (
    register_device,
    unregister_device,
    get_user_devices
)

router = APIRouter(prefix="/devices", tags=["devices"])


class RegisterDeviceRequest(BaseModel):
    device_token: str
    device_type: str  # ios, android, web
    device_name: Optional[str] = None


class DeviceResponse(BaseModel):
    id: int
    device_type: str
    device_name: Optional[str]
    last_used: Optional[str]
    created_at: str


@router.post("/register", response_model=DeviceResponse)
async def register_push_device(
    request: RegisterDeviceRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Register a device for push notifications.

    Device types: ios, android, web
    """
    if request.device_type not in ["ios", "android", "web"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid device type. Must be 'ios', 'android', or 'web'"
        )

    device = await register_device(
        db=db,
        user_id=user.id,
        device_token=request.device_token,
        device_type=request.device_type,
        device_name=request.device_name
    )

    return DeviceResponse(
        id=device.id,
        device_type=device.device_type,
        device_name=device.device_name,
        last_used=device.last_used.isoformat() if device.last_used else None,
        created_at=device.created_at.isoformat()
    )


@router.delete("/{device_token}")
async def unregister_push_device(
    device_token: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """Unregister a device from push notifications."""
    success = await unregister_device(db, user.id, device_token)

    if not success:
        raise HTTPException(status_code=404, detail="Device not found")

    return {"message": "Device unregistered successfully"}


@router.get("", response_model=List[DeviceResponse])
async def list_devices(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """List all registered devices for the current user."""
    devices = await get_user_devices(db, user.id)

    return [
        DeviceResponse(
            id=d["id"],
            device_type=d["device_type"],
            device_name=d["device_name"],
            last_used=d["last_used"],
            created_at=d["created_at"]
        )
        for d in devices
    ]
