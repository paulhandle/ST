"""Auth endpoints: send-otp, verify-otp, me."""
import random
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user
from app.core.config import sms_mock_return_code
from app.db import get_db
from app.models import OTPCode, User
from app.schemas import SendOTPRequest, SendOTPResponse, VerifyOTPRequest, VerifyOTPResponse, UserOut
from app.tools.sms import get_sms_provider, normalize_phone_number

router = APIRouter(prefix="/auth", tags=["auth"])

_OTP_TTL_MINUTES = 10


@router.post("/send-otp", response_model=SendOTPResponse, response_model_exclude_none=True)
def send_otp(body: SendOTPRequest, db: Session = Depends(get_db)):
    phone = normalize_phone_number(
        phone=body.phone,
        country_code=body.country_code,
        national_number=body.national_number,
    )

    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=_OTP_TTL_MINUTES)

    provider = get_sms_provider()
    provider.send_otp(phone, code)

    otp = OTPCode(phone=phone, code=code, expires_at=expires_at)
    db.add(otp)
    db.commit()

    if provider.name == "mock" and sms_mock_return_code():
        return SendOTPResponse(message="Verification code sent", otp_code=int(code))
    return SendOTPResponse(message="Verification code sent")


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(body: VerifyOTPRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    phone = normalize_phone_number(
        phone=body.phone,
        country_code=body.country_code,
        national_number=body.national_number,
    )

    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.phone == phone,
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

    is_new_user = False
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = User(phone=phone)
        db.add(user)
        db.flush()
        is_new_user = True

    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return VerifyOTPResponse(access_token=token, token_type="bearer", user_id=user.id, is_new_user=is_new_user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut(id=current_user.id, phone=current_user.phone)
