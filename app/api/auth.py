"""Auth endpoints: send-otp, verify-otp, me."""
import random
import re
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user
from app.db import get_db
from app.models import OTPCode, User
from app.schemas import SendOTPRequest, SendOTPResponse, VerifyOTPRequest, VerifyOTPResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

_PHONE_RE = re.compile(r"^1[3-9]\d{9}$")
_OTP_TTL_MINUTES = 10


@router.post("/send-otp", response_model=SendOTPResponse)
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    if not _PHONE_RE.match(body.phone):
        raise HTTPException(status_code=422, detail="Invalid phone number")

    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES)

    otp = OTPCode(phone=body.phone, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()

    # Mock mode: return OTP code in response (replace with SMS in prod)
    return SendOTPResponse(message="验证码已发送", otp_code=int(code))


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.phone == body.phone,
            OTPCode.code == body.code,
            OTPCode.used == False,  # noqa: E712
            OTPCode.expires_at > now,
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if otp is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="验证码无效或已过期")

    otp.used = True
    db.flush()

    user = db.query(User).filter(User.phone == body.phone).first()
    if user is None:
        user = User(phone=body.phone)
        db.add(user)
        db.flush()

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return VerifyOTPResponse(access_token=token, token_type="bearer", user_id=user.id)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, phone=current_user.phone)
