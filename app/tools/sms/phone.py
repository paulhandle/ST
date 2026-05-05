from __future__ import annotations

import re

from fastapi import HTTPException

_DIGITS_RE = re.compile(r"\D+")

SUPPORTED_COUNTRY_CODES = {
    "+1",
    "+44",
    "+61",
    "+65",
    "+81",
    "+852",
    "+86",
    "+886",
}


def normalize_phone_number(
    *,
    phone: str | None = None,
    country_code: str | None = None,
    national_number: str | None = None,
) -> str:
    if phone:
        return _normalize_legacy_phone(phone)

    if not country_code or not national_number:
        raise HTTPException(status_code=422, detail="Phone number is required")

    code = _normalize_country_code(country_code)
    if code not in SUPPORTED_COUNTRY_CODES:
        raise HTTPException(status_code=422, detail="Unsupported country or region code")

    national = _DIGITS_RE.sub("", national_number)
    if national.startswith("0") and code not in {"+1", "+86"}:
        national = national.lstrip("0")

    e164 = f"{code}{national}"
    if not _is_supported_e164(e164):
        raise HTTPException(status_code=422, detail="Invalid phone number")
    return e164


def _normalize_legacy_phone(phone: str) -> str:
    raw = phone.strip()
    digits = _DIGITS_RE.sub("", raw)
    if raw.startswith("+"):
        e164 = f"+{digits}"
    elif digits.startswith("86") and len(digits) == 13:
        e164 = f"+{digits}"
    elif len(digits) == 11 and re.fullmatch(r"1[3-9]\d{9}", digits):
        e164 = f"+86{digits}"
    else:
        raise HTTPException(status_code=422, detail="Invalid phone number")

    if not _is_supported_e164(e164):
        raise HTTPException(status_code=422, detail="Invalid phone number")
    return e164


def _normalize_country_code(country_code: str) -> str:
    code = country_code.strip()
    digits = _DIGITS_RE.sub("", code)
    if not digits:
        raise HTTPException(status_code=422, detail="Invalid country or region code")
    return f"+{digits}"


def _is_supported_e164(phone: str) -> bool:
    if not re.fullmatch(r"\+[1-9]\d{7,14}", phone):
        return False

    if phone.startswith("+86"):
        return re.fullmatch(r"\+861[3-9]\d{9}", phone) is not None
    if phone.startswith("+1"):
        return re.fullmatch(r"\+1[2-9]\d{9}", phone) is not None
    if phone.startswith("+44"):
        return re.fullmatch(r"\+44\d{9,10}", phone) is not None
    if phone.startswith("+65"):
        return re.fullmatch(r"\+65[689]\d{7}", phone) is not None
    if phone.startswith("+852"):
        return re.fullmatch(r"\+852[456789]\d{7}", phone) is not None
    if phone.startswith("+886"):
        return re.fullmatch(r"\+8869\d{8}", phone) is not None
    if phone.startswith("+81"):
        return re.fullmatch(r"\+81\d{9,10}", phone) is not None
    if phone.startswith("+61"):
        return re.fullmatch(r"\+614\d{8}", phone) is not None
    return False
