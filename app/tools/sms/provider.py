from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import sms_provider_name


@dataclass(frozen=True)
class SMSDeliveryResult:
    provider: str
    message_id: str | None = None


class SMSProvider(Protocol):
    name: str

    def send_otp(self, phone: str, code: str) -> SMSDeliveryResult:
        raise NotImplementedError


class MockSMSProvider:
    name = "mock"

    def send_otp(self, phone: str, code: str) -> SMSDeliveryResult:
        return SMSDeliveryResult(provider=self.name, message_id=f"mock:{phone}:{code}")


class DryRunSMSProvider:
    name = "dry_run"

    def send_otp(self, phone: str, code: str) -> SMSDeliveryResult:
        return SMSDeliveryResult(provider=self.name, message_id=f"dry-run:{phone}")


def get_sms_provider() -> SMSProvider:
    provider = sms_provider_name()
    if provider == "dry_run":
        return DryRunSMSProvider()
    return MockSMSProvider()
