from typing import Dict, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db import CurrencyRate

SUPPORTED_CURRENCIES = {
    "USD": {"name": "US Dollar", "symbol": "$", "type": "fiat"},
    "EUR": {"name": "Euro", "symbol": "€", "type": "fiat"},
    "GBP": {"name": "British Pound", "symbol": "£", "type": "fiat"},
    "CAD": {"name": "Canadian Dollar", "symbol": "C$", "type": "fiat"},
    "AUD": {"name": "Australian Dollar", "symbol": "A$", "type": "fiat"},
    "BTC": {"name": "Bitcoin", "symbol": "₿", "type": "crypto", "decimals": 8},
    "ETH": {"name": "Ethereum", "symbol": "Ξ", "type": "crypto", "decimals": 6},
}

DEFAULT_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "GBP": 0.79,
    "CAD": 1.36,
    "AUD": 1.53,
    "BTC": 0.000024,
    "ETH": 0.00028,
}


def get_currency_info(currency_code: str) -> Optional[Dict]:
    return SUPPORTED_CURRENCIES.get(currency_code.upper())


def get_all_currencies() -> Dict:
    return SUPPORTED_CURRENCIES


def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    db: Optional[Session] = None
) -> float:
    if from_currency.upper() == to_currency.upper():
        return amount
    
    from_rate = get_rate(from_currency, db)
    to_rate = get_rate(to_currency, db)
    
    usd_amount = amount / from_rate
    
    return usd_amount * to_rate


def get_rate(currency: str, db: Optional[Session] = None) -> float:
    currency = currency.upper()
    
    if currency == "USD":
        return 1.0
    
    if db:
        rate_record = db.query(CurrencyRate).filter(
            CurrencyRate.target_currency == currency
        ).first()
        
        if rate_record and rate_record.updated_at > datetime.utcnow() - timedelta(hours=1):
            return rate_record.rate
    
    return DEFAULT_RATES.get(currency, 1.0)


def update_rates(db: Session, rates: Dict[str, float]) -> None:
    for currency, rate in rates.items():
        currency = currency.upper()
        if currency == "USD":
            continue
        
        existing = db.query(CurrencyRate).filter(
            CurrencyRate.target_currency == currency
        ).first()
        
        if existing:
            existing.rate = rate
            existing.updated_at = datetime.utcnow()
        else:
            new_rate = CurrencyRate(
                target_currency=currency,
                rate=rate
            )
            db.add(new_rate)
    
    db.commit()


def format_currency(amount: float, currency: str) -> str:
    currency = currency.upper()
    info = SUPPORTED_CURRENCIES.get(currency, {"symbol": "$", "decimals": 2})
    symbol = info.get("symbol", "$")
    decimals = info.get("decimals", 2)
    
    if info.get("type") == "crypto":
        return f"{symbol}{amount:.{decimals}f}"
    else:
        return f"{symbol}{amount:,.2f}"


def seed_default_rates(db: Session) -> None:
    for currency, rate in DEFAULT_RATES.items():
        if currency == "USD":
            continue
        
        existing = db.query(CurrencyRate).filter(
            CurrencyRate.target_currency == currency
        ).first()
        
        if not existing:
            new_rate = CurrencyRate(
                target_currency=currency,
                rate=rate
            )
            db.add(new_rate)
    
    db.commit()
