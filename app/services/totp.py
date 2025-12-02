import pyotp
import secrets
import json
import io
import base64
from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import qrcode

from app.db import User
from app.config import SESSION_SECRET


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def generate_backup_codes(count: int = 10) -> List[str]:
    return [secrets.token_hex(4).upper() for _ in range(count)]


def get_totp_uri(user: User, secret: str, issuer: str = "EdgeBet") -> str:
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=user.email, issuer_name=issuer)


def generate_qr_code_base64(uri: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code, valid_window=1)


def verify_backup_code(stored_codes_json: str, code: str) -> Tuple[bool, str]:
    if not stored_codes_json:
        return False, stored_codes_json
    
    try:
        codes = json.loads(stored_codes_json)
    except json.JSONDecodeError:
        return False, stored_codes_json
    
    code_upper = code.upper().replace("-", "").replace(" ", "")
    
    for i, stored_code in enumerate(codes):
        if stored_code.upper() == code_upper:
            codes.pop(i)
            return True, json.dumps(codes)
    
    return False, stored_codes_json


def setup_2fa(db: Session, user: User) -> dict:
    secret = generate_totp_secret()
    backup_codes = generate_backup_codes()
    
    user.totp_secret = secret
    user.backup_codes = json.dumps(backup_codes)
    db.commit()
    
    uri = get_totp_uri(user, secret)
    qr_code = generate_qr_code_base64(uri)
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": backup_codes,
        "uri": uri
    }


def enable_2fa(db: Session, user: User, code: str) -> bool:
    if not user.totp_secret:
        return False
    
    if not verify_totp_code(user.totp_secret, code):
        return False
    
    user.totp_enabled = True
    user.totp_verified_at = datetime.utcnow()
    db.commit()
    
    return True


def disable_2fa(db: Session, user: User, code: str) -> bool:
    if not user.totp_enabled:
        return False
    
    if not verify_totp_code(user.totp_secret, code):
        return False
    
    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    user.totp_verified_at = None
    db.commit()
    
    return True


def verify_2fa(db: Session, user: User, code: str) -> bool:
    if not user.totp_enabled or not user.totp_secret:
        return True
    
    code_clean = code.replace(" ", "").replace("-", "")
    
    if len(code_clean) == 6 and code_clean.isdigit():
        return verify_totp_code(user.totp_secret, code_clean)
    
    if len(code_clean) == 8:
        is_valid, updated_codes = verify_backup_code(user.backup_codes, code_clean)
        if is_valid:
            user.backup_codes = updated_codes
            db.commit()
        return is_valid
    
    return False


def regenerate_backup_codes(db: Session, user: User, code: str) -> Optional[List[str]]:
    if not user.totp_enabled:
        return None
    
    if not verify_totp_code(user.totp_secret, code):
        return None
    
    new_codes = generate_backup_codes()
    user.backup_codes = json.dumps(new_codes)
    db.commit()
    
    return new_codes


def get_remaining_backup_codes(user: User) -> int:
    if not user.backup_codes:
        return 0
    
    try:
        codes = json.loads(user.backup_codes)
        return len(codes)
    except json.JSONDecodeError:
        return 0
