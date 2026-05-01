from __future__ import annotations

import base64
import hashlib
import hmac
import os


_VERSION = b"v1"
_NONCE_BYTES = 16
_MAC_BYTES = 32


def _secret_key() -> bytes:
    return os.environ.get("ST_SECRET_KEY", "st-local-personal-use-secret").encode("utf-8")


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    chunks: list[bytes] = []
    counter = 0
    while sum(len(chunk) for chunk in chunks) < length:
        counter_bytes = counter.to_bytes(4, "big")
        chunks.append(hashlib.sha256(key + nonce + counter_bytes).digest())
        counter += 1
    return b"".join(chunks)[:length]


def encrypt_secret(value: str) -> str:
    key = _secret_key()
    nonce = os.urandom(_NONCE_BYTES)
    plaintext = value.encode("utf-8")
    stream = _keystream(key=key, nonce=nonce, length=len(plaintext))
    ciphertext = bytes(left ^ right for left, right in zip(plaintext, stream, strict=False))
    mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(_VERSION + nonce + mac + ciphertext).decode("ascii")


def decrypt_secret(value: str) -> str:
    key = _secret_key()
    payload = base64.urlsafe_b64decode(value.encode("ascii"))
    if not payload.startswith(_VERSION):
        raise ValueError("Unsupported encrypted secret version")

    offset = len(_VERSION)
    nonce = payload[offset : offset + _NONCE_BYTES]
    offset += _NONCE_BYTES
    expected_mac = payload[offset : offset + _MAC_BYTES]
    offset += _MAC_BYTES
    ciphertext = payload[offset:]

    actual_mac = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_mac, actual_mac):
        raise ValueError("Encrypted secret failed integrity check")

    stream = _keystream(key=key, nonce=nonce, length=len(ciphertext))
    plaintext = bytes(left ^ right for left, right in zip(ciphertext, stream, strict=False))
    return plaintext.decode("utf-8")
