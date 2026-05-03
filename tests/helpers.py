"""Shared test utilities."""
from fastapi.testclient import TestClient


def get_test_token(client: TestClient, phone: str = "18800000001") -> str:
    """Create a user via OTP flow and return a valid Bearer token."""
    code = client.post("/auth/send-otp", json={"phone": phone}).json()["otp_code"]
    res = client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
    return res.json()["access_token"]


def auth(token: str) -> dict:
    """Return Authorization header dict for use in test requests."""
    return {"Authorization": f"Bearer {token}"}
