from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, Dict

from app.db import get_db, User
from app.services.auth import validate_session
from app.services.currency import (
    get_all_currencies, convert_currency, format_currency,
    get_currency_info, get_rate
)
from app.services.audit import log_action

router = APIRouter(prefix="/currency", tags=["currency"])


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ")[1]
    user = validate_session(db, token)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    return user


class CurrencyInfo(BaseModel):
    code: str
    name: str
    symbol: str
    type: str


class ConvertRequest(BaseModel):
    amount: float = Field(..., gt=0)
    from_currency: str
    to_currency: str


class ConvertResponse(BaseModel):
    original_amount: float
    from_currency: str
    converted_amount: float
    to_currency: str
    formatted: str


class SetPreferredCurrencyRequest(BaseModel):
    currency: str


@router.get("/list")
def list_currencies():
    currencies = get_all_currencies()
    return {
        code: CurrencyInfo(
            code=code,
            name=info["name"],
            symbol=info["symbol"],
            type=info["type"]
        )
        for code, info in currencies.items()
    }


@router.post("/convert", response_model=ConvertResponse)
def convert(
    data: ConvertRequest,
    db: Session = Depends(get_db)
):
    from_info = get_currency_info(data.from_currency)
    to_info = get_currency_info(data.to_currency)
    
    if not from_info:
        raise HTTPException(status_code=400, detail=f"Unknown currency: {data.from_currency}")
    if not to_info:
        raise HTTPException(status_code=400, detail=f"Unknown currency: {data.to_currency}")
    
    converted = convert_currency(
        amount=data.amount,
        from_currency=data.from_currency,
        to_currency=data.to_currency,
        db=db
    )
    
    formatted = format_currency(converted, data.to_currency)
    
    return ConvertResponse(
        original_amount=data.amount,
        from_currency=data.from_currency.upper(),
        converted_amount=round(converted, 8),
        to_currency=data.to_currency.upper(),
        formatted=formatted
    )


@router.get("/rates")
def get_rates(db: Session = Depends(get_db)):
    currencies = get_all_currencies()
    rates = {}
    
    for code in currencies:
        rates[code] = get_rate(code, db)
    
    return {"base": "USD", "rates": rates}


@router.post("/preference")
def set_preferred_currency(
    data: SetPreferredCurrencyRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    info = get_currency_info(data.currency)
    if not info:
        raise HTTPException(status_code=400, detail=f"Unknown currency: {data.currency}")
    
    old_currency = user.preferred_currency
    user.preferred_currency = data.currency.upper()
    db.commit()
    
    log_action(
        db, "currency_changed", user.id,
        ip_address=request.client.host if request.client else None,
        old_value={"currency": old_currency},
        new_value={"currency": user.preferred_currency}
    )
    
    return {"message": "Preferred currency updated", "currency": user.preferred_currency}


@router.get("/preference")
def get_preferred_currency(
    user: User = Depends(get_current_user)
):
    info = get_currency_info(user.preferred_currency)
    return {
        "currency": user.preferred_currency,
        "info": info
    }
