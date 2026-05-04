"""
Auth endpoint tests — written before implementation (TDD).
All tests should FAIL until auth routes and models are implemented.
"""
import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine


class AuthSetup(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)


class SendOTPTestCase(AuthSetup):
    def test_send_otp_valid_phone_returns_200(self):
        res = self.client.post("/auth/send-otp", json={"phone": "13800138000"})
        self.assertEqual(res.status_code, 200)

    def test_send_otp_returns_mock_code_in_dev(self):
        res = self.client.post("/auth/send-otp", json={"phone": "13800138000"})
        data = res.json()
        # In dev/mock mode, the OTP code is returned directly
        self.assertIn("otp_code", data)
        self.assertEqual(len(str(data["otp_code"])), 6)

    def test_send_otp_invalid_phone_returns_422(self):
        res = self.client.post("/auth/send-otp", json={"phone": "not-a-phone"})
        self.assertEqual(res.status_code, 422)

    def test_send_otp_missing_phone_returns_422(self):
        res = self.client.post("/auth/send-otp", json={})
        self.assertEqual(res.status_code, 422)


class VerifyOTPTestCase(AuthSetup):
    def _send(self, phone="13800138000"):
        res = self.client.post("/auth/send-otp", json={"phone": phone})
        return res.json()["otp_code"]

    def test_verify_correct_otp_returns_token(self):
        phone = "13800138001"
        code = self._send(phone)
        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")

    def test_verify_wrong_otp_returns_401(self):
        phone = "13800138002"
        self._send(phone)
        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": "000000"})
        self.assertEqual(res.status_code, 401)

    def test_verify_otp_creates_user_on_first_login(self):
        phone = "13800138003"
        code = self._send(phone)
        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("user_id", data)
        self.assertIsNotNone(data["user_id"])

    def test_verify_otp_is_single_use(self):
        phone = "13800138004"
        code = self._send(phone)
        # First use succeeds
        self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        # Second use fails
        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        self.assertEqual(res.status_code, 401)

    def test_verify_expired_otp_returns_401(self):
        """OTP older than 10 minutes should be rejected."""
        from app.models import OTPCode
        from app.db import SessionLocal
        from datetime import datetime, timezone, timedelta

        phone = "13800138005"
        code = self._send(phone)

        # Manually expire the OTP
        db = SessionLocal()
        try:
            otp = db.query(OTPCode).filter(OTPCode.phone == phone).first()
            otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        self.assertEqual(res.status_code, 401)


class MeEndpointTestCase(AuthSetup):
    def _login(self, phone="13900139000"):
        code = self.client.post("/auth/send-otp", json={"phone": phone}).json()["otp_code"]
        return self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)}).json()["access_token"]

    def test_me_with_valid_token_returns_user(self):
        token = self._login()
        res = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("id", data)
        self.assertIn("phone", data)

    def test_me_without_token_returns_401(self):
        res = self.client.get("/auth/me")
        self.assertEqual(res.status_code, 401)

    def test_me_with_invalid_token_returns_401(self):
        res = self.client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        self.assertEqual(res.status_code, 401)


if __name__ == "__main__":
    unittest.main()


class ProtectedRoutesTestCase(AuthSetup):
    """Verify that key routes return 401 without a valid token."""

    def _get_token(self, phone="19900001234"):
        code = self.client.post("/auth/send-otp", json={"phone": phone}).json()["otp_code"]
        return self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)}).json()["access_token"]

    def test_create_athlete_requires_auth(self):
        res = self.client.post("/athletes", json={"name": "T", "sport": "marathon"})
        self.assertEqual(res.status_code, 401)

    def test_create_athlete_accepts_valid_token(self):
        token = self._get_token()
        res = self.client.post(
            "/athletes",
            json={"name": "테스트", "sport": "marathon"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertIn(res.status_code, (200, 201, 422))

    def test_today_endpoint_requires_auth(self):
        res = self.client.get("/athletes/1/today")
        self.assertEqual(res.status_code, 401)

    def test_dashboard_endpoint_requires_auth(self):
        res = self.client.get("/athletes/1/dashboard")
        self.assertEqual(res.status_code, 401)

    def test_history_endpoint_requires_auth(self):
        res = self.client.get("/athletes/1/history")
        self.assertEqual(res.status_code, 401)

    def test_coach_message_requires_auth(self):
        res = self.client.post("/coach/message", json={"athlete_id": 1, "message": "hello"})
        self.assertEqual(res.status_code, 401)
