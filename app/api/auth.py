"""Auth endpoints: Google, passkey, and SMS fallback."""
import json
import random
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy import func
from sqlalchemy.orm import Session
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.auth import create_access_token, get_current_user
from app.core.config import (
    google_client_id,
    sms_mock_return_code,
    webauthn_allowed_origins,
    webauthn_rp_id,
    webauthn_rp_name,
)
from app.db import get_db
from app.models import (
    AuthChallenge,
    AuthChallengePurpose,
    AuthIdentity,
    AuthProvider,
    OTPCode,
    User,
    WebAuthnCredential,
)
from app.schemas import (
    GoogleLoginRequest,
    PasskeyAuthenticationFinishRequest,
    PasskeyAuthenticationStartRequest,
    PasskeyAuthenticationStartResponse,
    PasskeyRegistrationFinishRequest,
    PasskeyRegistrationStartResponse,
    PhoneLinkFinishRequest,
    PhoneLinkStartRequest,
    SendOTPRequest,
    SendOTPResponse,
    UserOut,
    VerifyOTPRequest,
    VerifyOTPResponse,
)
from app.tools.sms import get_sms_provider, normalize_phone_number

router = APIRouter(prefix="/auth", tags=["auth"])

_OTP_TTL_MINUTES = 10
_PASSKEY_TTL_MINUTES = 5
_MAX_OTP_SENDS_PER_PHONE_HOUR = 5
_MAX_OTP_SENDS_PER_IP_HOUR = 20
_MAX_OTP_VERIFY_FAILS_PER_PHONE_HOUR = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    return request.client.host if request.client else "unknown"


def _rate_count(db: Session, purpose: AuthChallengePurpose, *, subject: str | None = None, ip: str | None = None) -> int:
    cutoff = _now() - timedelta(hours=1)
    query = db.query(func.count(AuthChallenge.id)).filter(
        AuthChallenge.purpose == purpose,
        AuthChallenge.created_at >= cutoff,
    )
    if subject is not None:
        query = query.filter(AuthChallenge.subject == subject)
    if ip is not None:
        query = query.filter(AuthChallenge.ip_address == ip)
    return int(query.scalar() or 0)


def _record_challenge(
    db: Session,
    *,
    purpose: AuthChallengePurpose,
    subject: str,
    challenge: str | None,
    request: Request,
    ttl_minutes: int,
) -> AuthChallenge:
    row = AuthChallenge(
        purpose=purpose,
        subject=subject,
        challenge=challenge,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
        expires_at=_now() + timedelta(minutes=ttl_minutes),
    )
    db.add(row)
    db.flush()
    return row


def _latest_challenge(db: Session, purpose: AuthChallengePurpose, subject: str) -> AuthChallenge | None:
    return (
        db.query(AuthChallenge)
        .filter(
            AuthChallenge.purpose == purpose,
            AuthChallenge.subject == subject,
            AuthChallenge.consumed == False,  # noqa: E712
            AuthChallenge.expires_at > _now(),
        )
        .order_by(AuthChallenge.created_at.desc())
        .first()
    )


def _auth_response(user: User, is_new_user: bool) -> VerifyOTPResponse:
    return VerifyOTPResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        user_id=user.id,
        is_new_user=is_new_user,
    )


def _ensure_identity(
    db: Session,
    *,
    user: User,
    provider: AuthProvider,
    provider_subject: str,
    email: str | None = None,
) -> AuthIdentity:
    identity = (
        db.query(AuthIdentity)
        .filter(AuthIdentity.provider == provider, AuthIdentity.provider_subject == provider_subject)
        .first()
    )
    if identity is None:
        identity = AuthIdentity(
            user_id=user.id,
            provider=provider,
            provider_subject=provider_subject,
            email=email,
        )
        db.add(identity)
    else:
        identity.user_id = user.id
        identity.email = email or identity.email
    identity.last_login_at = _now()
    return identity


def _user_from_identity(db: Session, provider: AuthProvider, provider_subject: str) -> User | None:
    identity = (
        db.query(AuthIdentity)
        .filter(AuthIdentity.provider == provider, AuthIdentity.provider_subject == provider_subject)
        .first()
    )
    return identity.user if identity else None


def _create_or_get_google_user(db: Session, claims: dict) -> tuple[User, bool]:
    subject = str(claims["sub"])
    user = _user_from_identity(db, AuthProvider.GOOGLE, subject)
    is_new = False
    if user is None:
        email = claims.get("email")
        user = db.query(User).filter(User.email == email).first() if email else None
        if user is None:
            user = User(
                email=email,
                display_name=claims.get("name"),
                avatar_url=claims.get("picture"),
            )
            db.add(user)
            db.flush()
            is_new = True
    user.email = claims.get("email") or user.email
    user.display_name = claims.get("name") or user.display_name
    user.avatar_url = claims.get("picture") or user.avatar_url
    _ensure_identity(db, user=user, provider=AuthProvider.GOOGLE, provider_subject=subject, email=user.email)
    return user, is_new


def _credential_descriptors(credentials: list[WebAuthnCredential]) -> list[PublicKeyCredentialDescriptor]:
    return [PublicKeyCredentialDescriptor(id=base64url_to_bytes(c.credential_id)) for c in credentials]


def _json_options(options) -> dict:
    return json.loads(options_to_json(options))


@router.post("/send-otp", response_model=SendOTPResponse, response_model_exclude_none=True)
def send_otp(body: SendOTPRequest, request: Request, db: Session = Depends(get_db)):
    phone = normalize_phone_number(
        phone=body.phone,
        country_code=body.country_code,
        national_number=body.national_number,
    )
    ip = _client_ip(request)
    if _rate_count(db, AuthChallengePurpose.OTP_SEND, subject=phone) >= _MAX_OTP_SENDS_PER_PHONE_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification codes for this phone")
    if _rate_count(db, AuthChallengePurpose.OTP_SEND, ip=ip) >= _MAX_OTP_SENDS_PER_IP_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many verification code requests")

    code = str(random.randint(100000, 999999))
    expires_at = _now() + timedelta(minutes=_OTP_TTL_MINUTES)

    provider = get_sms_provider()
    provider.send_otp(phone, code)

    otp = OTPCode(phone=phone, code=code, expires_at=expires_at)
    db.add(otp)
    _record_challenge(
        db,
        purpose=AuthChallengePurpose.OTP_SEND,
        subject=phone,
        challenge=None,
        request=request,
        ttl_minutes=_OTP_TTL_MINUTES,
    )
    db.commit()

    if provider.name == "mock" and sms_mock_return_code():
        return SendOTPResponse(message="Verification code sent", otp_code=int(code))
    return SendOTPResponse(message="Verification code sent")


def _verify_phone_otp(body: VerifyOTPRequest | PhoneLinkFinishRequest, request: Request, db: Session) -> str:
    phone = normalize_phone_number(
        phone=body.phone,
        country_code=body.country_code,
        national_number=body.national_number,
    )
    if _rate_count(db, AuthChallengePurpose.OTP_VERIFY_FAIL, subject=phone) >= _MAX_OTP_VERIFY_FAILS_PER_PHONE_HOUR:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed verification attempts")

    otp = (
        db.query(OTPCode)
        .filter(
            OTPCode.phone == phone,
            OTPCode.code == body.code,
            OTPCode.used == False,  # noqa: E712
            OTPCode.expires_at > _now(),
        )
        .order_by(OTPCode.created_at.desc())
        .first()
    )

    if otp is None:
        _record_challenge(
            db,
            purpose=AuthChallengePurpose.OTP_VERIFY_FAIL,
            subject=phone,
            challenge=None,
            request=request,
            ttl_minutes=60,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="验证码无效或已过期")

    otp.used = True
    db.flush()
    return phone


@router.post("/verify-otp", response_model=VerifyOTPResponse)
def verify_otp(body: VerifyOTPRequest, request: Request, db: Session = Depends(get_db)):
    phone = _verify_phone_otp(body, request, db)

    is_new_user = False
    user = db.query(User).filter(User.phone == phone).first()
    if user is None:
        user = _user_from_identity(db, AuthProvider.PHONE, phone)
    if user is None:
        user = User(phone=phone)
        db.add(user)
        db.flush()
        is_new_user = True
    user.phone = phone
    _ensure_identity(db, user=user, provider=AuthProvider.PHONE, provider_subject=phone)

    db.commit()
    db.refresh(user)
    return _auth_response(user, is_new_user)


@router.post("/google", response_model=VerifyOTPResponse)
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)):
    client_id = google_client_id()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google login is not configured")
    try:
        claims = google_id_token.verify_oauth2_token(body.id_token, google_requests.Request(), client_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token") from exc
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google issuer")
    if not claims.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google subject")

    user, is_new = _create_or_get_google_user(db, claims)
    db.commit()
    db.refresh(user)
    return _auth_response(user, is_new)


@router.post("/passkeys/register/options", response_model=PasskeyRegistrationStartResponse)
def passkey_register_options(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    credentials = db.query(WebAuthnCredential).filter(WebAuthnCredential.user_id == current_user.id).all()
    user_name = current_user.email or current_user.phone or f"user-{current_user.id}"
    options = generate_registration_options(
        rp_id=webauthn_rp_id(),
        rp_name=webauthn_rp_name(),
        user_id=str(current_user.id).encode(),
        user_name=user_name,
        user_display_name=current_user.display_name or user_name,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=_credential_descriptors(credentials),
    )
    _record_challenge(
        db,
        purpose=AuthChallengePurpose.PASSKEY_REGISTER,
        subject=str(current_user.id),
        challenge=bytes_to_base64url(options.challenge),
        request=request,
        ttl_minutes=_PASSKEY_TTL_MINUTES,
    )
    db.commit()
    return PasskeyRegistrationStartResponse(options=_json_options(options))


@router.post("/passkeys/register/verify")
def passkey_register_verify(
    body: PasskeyRegistrationFinishRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    challenge = _latest_challenge(db, AuthChallengePurpose.PASSKEY_REGISTER, str(current_user.id))
    if challenge is None or not challenge.challenge:
        raise HTTPException(status_code=400, detail="Passkey registration challenge expired")
    try:
        verified = verify_registration_response(
            credential=body.credential,
            expected_challenge=base64url_to_bytes(challenge.challenge),
            expected_rp_id=webauthn_rp_id(),
            expected_origin=webauthn_allowed_origins(),
            require_user_verification=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passkey registration") from exc

    credential_id = bytes_to_base64url(verified.credential_id)
    existing = db.query(WebAuthnCredential).filter(WebAuthnCredential.credential_id == credential_id).first()
    if existing is not None:
        raise HTTPException(status_code=409, detail="Passkey already registered")
    db.add(WebAuthnCredential(
        user_id=current_user.id,
        credential_id=credential_id,
        public_key=verified.credential_public_key,
        sign_count=verified.sign_count,
        transports_json=json.dumps(body.credential.get("response", {}).get("transports", [])),
        name=body.name,
    ))
    _ensure_identity(db, user=current_user, provider=AuthProvider.PASSKEY, provider_subject=credential_id)
    challenge.consumed = True
    db.commit()
    return {"registered": True}


@router.post("/passkeys/login/options", response_model=PasskeyAuthenticationStartResponse)
def passkey_login_options(body: PasskeyAuthenticationStartRequest, request: Request, db: Session = Depends(get_db)):
    credentials_query = db.query(WebAuthnCredential)
    subject = "discoverable"
    if body.email:
        user = db.query(User).filter(User.email == body.email).first()
        credentials_query = credentials_query.filter(WebAuthnCredential.user_id == (user.id if user else -1))
        subject = body.email
    credentials = credentials_query.all()
    options = generate_authentication_options(
        rp_id=webauthn_rp_id(),
        allow_credentials=_credential_descriptors(credentials),
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    _record_challenge(
        db,
        purpose=AuthChallengePurpose.PASSKEY_LOGIN,
        subject=subject,
        challenge=bytes_to_base64url(options.challenge),
        request=request,
        ttl_minutes=_PASSKEY_TTL_MINUTES,
    )
    db.commit()
    return PasskeyAuthenticationStartResponse(options=_json_options(options))


@router.post("/passkeys/login/verify", response_model=VerifyOTPResponse)
def passkey_login_verify(body: PasskeyAuthenticationFinishRequest, db: Session = Depends(get_db)):
    raw_id = body.credential.get("rawId") or body.credential.get("id")
    if not raw_id:
        raise HTTPException(status_code=400, detail="Missing credential id")
    stored = db.query(WebAuthnCredential).filter(WebAuthnCredential.credential_id == raw_id).first()
    if stored is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown passkey")
    challenge = _latest_challenge(db, AuthChallengePurpose.PASSKEY_LOGIN, stored.user.email or "discoverable")
    if challenge is None:
        challenge = _latest_challenge(db, AuthChallengePurpose.PASSKEY_LOGIN, "discoverable")
    if challenge is None or not challenge.challenge:
        raise HTTPException(status_code=400, detail="Passkey login challenge expired")
    try:
        verified = verify_authentication_response(
            credential=body.credential,
            expected_challenge=base64url_to_bytes(challenge.challenge),
            expected_rp_id=webauthn_rp_id(),
            expected_origin=webauthn_allowed_origins(),
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid passkey") from exc

    stored.sign_count = verified.new_sign_count
    stored.last_used_at = _now()
    challenge.consumed = True
    _ensure_identity(db, user=stored.user, provider=AuthProvider.PASSKEY, provider_subject=stored.credential_id)
    db.commit()
    db.refresh(stored.user)
    return _auth_response(stored.user, False)


@router.post("/phone/link/start", response_model=SendOTPResponse, response_model_exclude_none=True)
def start_phone_link(
    body: PhoneLinkStartRequest,
    request: Request,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return send_otp(body, request, db)


@router.post("/phone/link/verify", response_model=UserOut)
def verify_phone_link(
    body: PhoneLinkFinishRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone = _verify_phone_otp(body, request, db)
    owner = db.query(User).filter(User.phone == phone, User.id != current_user.id).first()
    if owner is not None:
        raise HTTPException(status_code=409, detail="Phone is already linked")
    current_user.phone = phone
    _ensure_identity(db, user=current_user, provider=AuthProvider.PHONE, provider_subject=phone)
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return UserOut.model_validate(current_user)
