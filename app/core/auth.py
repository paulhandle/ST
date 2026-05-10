"""JWT auth utilities — stateless 30-day tokens, no refresh."""
import hmac
import hashlib
import json
import base64
import logging
import os
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User

_SECRET = os.environ.get("ST_SECRET_KEY", "dev-secret-change-in-prod")
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 30
_LOG = logging.getLogger("app.auth")

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class TokenDecodeResult:
    user_id: Optional[int]
    reason: Optional[str] = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    padding = 4 - len(s) % 4
    return base64.urlsafe_b64decode(s + "=" * (padding % 4))


def create_access_token(user_id: int) -> str:
    header = _b64url(json.dumps({"alg": _ALGORITHM, "typ": "JWT"}).encode())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=_EXPIRE_DAYS)).timestamp()),
    }
    body = _b64url(json.dumps(payload).encode())
    sig_input = f"{header}.{body}".encode()
    sig = _b64url(hmac.new(_SECRET.encode(), sig_input, hashlib.sha256).digest())
    return f"{header}.{body}.{sig}"


def decode_token_details(token: str) -> TokenDecodeResult:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return TokenDecodeResult(None, "invalid_format")
        header, body, sig = parts
        sig_input = f"{header}.{body}".encode()
        expected = _b64url(hmac.new(_SECRET.encode(), sig_input, hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            return TokenDecodeResult(None, "invalid_signature")
        payload = json.loads(_b64url_decode(body))
        if payload.get("exp", 0) < datetime.now(timezone.utc).timestamp():
            return TokenDecodeResult(None, "expired")
        return TokenDecodeResult(int(payload["sub"]))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return TokenDecodeResult(None, "invalid_payload")
    except Exception:
        return TokenDecodeResult(None, "decode_error")


def decode_token(token: str) -> Optional[int]:
    return decode_token_details(token).user_id


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def _auth_failure_detail(reason: str) -> dict[str, str]:
    messages = {
        "missing_credentials": "Missing bearer token",
        "invalid_format": "Invalid token format",
        "invalid_signature": "Invalid token signature",
        "expired": "Token expired",
        "invalid_payload": "Invalid token payload",
        "decode_error": "Token decode failed",
        "user_not_found": "Token user not found",
    }
    return {
        "code": "auth_unauthorized",
        "reason": reason,
        "message": messages.get(reason, "Unauthorized"),
    }


def _log_auth_failure(
    request: Optional[Request],
    reason: str,
    credentials: Optional[HTTPAuthorizationCredentials],
    user_id: Optional[int] = None,
) -> None:
    token = credentials.credentials if credentials else ""
    _LOG.warning(
        "auth_failure method=%s path=%s reason=%s scheme=%s token_fp=%s user_id=%s",
        request.method if request else "-",
        request.url.path if request else "-",
        reason,
        credentials.scheme if credentials else "-",
        _token_fingerprint(token) if token else "-",
        user_id if user_id is not None else "-",
    )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        reason = "missing_credentials"
        _log_auth_failure(request, reason, credentials)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_auth_failure_detail(reason))
    decoded = decode_token_details(credentials.credentials)
    if decoded.user_id is None:
        reason = decoded.reason or "decode_error"
        _log_auth_failure(request, reason, credentials)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_auth_failure_detail(reason))
    user_id = decoded.user_id
    user = db.get(User, user_id)
    if user is None:
        reason = "user_not_found"
        _log_auth_failure(request, reason, credentials, user_id=user_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_auth_failure_detail(reason))
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising — for routes that work with or without auth."""
    if not credentials:
        return None
    user_id = decode_token(credentials.credentials)
    if user_id is None:
        return None
    return db.get(User, user_id)
