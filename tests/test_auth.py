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
from app.models import AccountAlias, AthleteProfile, AuthChallenge, AuthChallengePurpose, AuthProvider, OTPCode, SportType, User, WebAuthnCredential


class AuthSetup(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)


class SendOTPTestCase(AuthSetup):
    def test_send_otp_valid_phone_returns_200(self):
        res = self.client.post("/auth/send-otp", json={"phone": "13800138000"})
        self.assertEqual(res.status_code, 200)

    def test_send_otp_country_fields_normalize_to_e164(self):
        res = self.client.post(
            "/auth/send-otp",
            json={"country_code": "+86", "national_number": "138 0013 8000"},
        )
        self.assertEqual(res.status_code, 200)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            otp = db.query(OTPCode).one()
            self.assertEqual(otp.phone, "+8613800138000")
        finally:
            db.close()

    def test_send_otp_accepts_us_country_code(self):
        res = self.client.post(
            "/auth/send-otp",
            json={"country_code": "+1", "national_number": "4155552671"},
        )
        self.assertEqual(res.status_code, 200)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            otp = db.query(OTPCode).one()
            self.assertEqual(otp.phone, "+14155552671")
        finally:
            db.close()

    def test_send_otp_returns_mock_code_in_dev(self):
        res = self.client.post("/auth/send-otp", json={"phone": "13800138000"})
        data = res.json()
        # In dev/mock mode, the OTP code is returned directly
        self.assertIn("otp_code", data)
        self.assertEqual(len(str(data["otp_code"])), 6)

    def test_send_otp_can_hide_mock_code_when_configured(self):
        os.environ["SMS_MOCK_RETURN_CODE"] = "false"
        try:
            res = self.client.post("/auth/send-otp", json={"phone": "13800138000"})
        finally:
            os.environ.pop("SMS_MOCK_RETURN_CODE", None)

        self.assertEqual(res.status_code, 200)
        self.assertNotIn("otp_code", res.json())

    def test_send_otp_dry_run_provider_does_not_return_code(self):
        os.environ["SMS_PROVIDER"] = "dry_run"
        try:
            res = self.client.post(
                "/auth/send-otp",
                json={"country_code": "+1", "national_number": "4155552671"},
            )
        finally:
            os.environ.pop("SMS_PROVIDER", None)

        self.assertEqual(res.status_code, 200)
        self.assertNotIn("otp_code", res.json())

    def test_send_otp_invalid_phone_returns_422(self):
        res = self.client.post("/auth/send-otp", json={"phone": "not-a-phone"})
        self.assertEqual(res.status_code, 422)

    def test_send_otp_unsupported_country_code_returns_422(self):
        res = self.client.post(
            "/auth/send-otp",
            json={"country_code": "+999", "national_number": "4155552671"},
        )
        self.assertEqual(res.status_code, 422)

    def test_send_otp_invalid_country_number_returns_422(self):
        res = self.client.post(
            "/auth/send-otp",
            json={"country_code": "+86", "national_number": "12345"},
        )
        self.assertEqual(res.status_code, 422)

    def test_send_otp_missing_phone_returns_422(self):
        res = self.client.post("/auth/send-otp", json={})
        self.assertEqual(res.status_code, 422)

    def test_send_otp_rate_limits_phone(self):
        phone = "13800138998"
        for _ in range(5):
            self.assertEqual(self.client.post("/auth/send-otp", json={"phone": phone}).status_code, 200)
        res = self.client.post("/auth/send-otp", json={"phone": phone})
        self.assertEqual(res.status_code, 429)


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

    def test_verify_otp_with_country_fields_creates_normalized_user(self):
        send = self.client.post(
            "/auth/send-otp",
            json={"country_code": "+1", "national_number": "4155552671"},
        )
        code = send.json()["otp_code"]

        res = self.client.post(
            "/auth/verify-otp",
            json={"country_code": "+1", "national_number": "4155552671", "code": str(code)},
        )

        self.assertEqual(res.status_code, 200)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            user = db.query(User).one()
            self.assertEqual(user.phone, "+14155552671")
            identity = db.query(AccountAlias).one()
            self.assertEqual(identity.provider, AuthProvider.PHONE)
            self.assertEqual(identity.provider_subject, "+14155552671")
        finally:
            db.close()

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
            otp = db.query(OTPCode).filter(OTPCode.phone == "+8613800138005").first()
            otp.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": str(code)})
        self.assertEqual(res.status_code, 401)

    def test_verify_otp_rate_limits_failed_attempts(self):
        phone = "13800138006"
        self._send(phone)
        for _ in range(5):
            self.assertEqual(self.client.post("/auth/verify-otp", json={"phone": phone, "code": "000000"}).status_code, 401)
        res = self.client.post("/auth/verify-otp", json={"phone": phone, "code": "000000"})
        self.assertEqual(res.status_code, 429)


class GoogleLoginTestCase(AuthSetup):
    def test_google_login_creates_user_and_identity(self):
        import app.api.auth as auth_module

        original_client_id = auth_module.google_client_id
        original_verify = auth_module.google_id_token.verify_oauth2_token
        auth_module.google_client_id = lambda: "client-id"
        auth_module.google_id_token.verify_oauth2_token = lambda token, request, audience: {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-1",
            "email": "runner@example.com",
            "name": "Runner One",
            "picture": "https://example.com/avatar.png",
        }
        try:
            res = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
        finally:
            auth_module.google_client_id = original_client_id
            auth_module.google_id_token.verify_oauth2_token = original_verify

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_new_user"])
        self.assertIn("access_token", data)
        self.assertFalse(data["has_athlete"])
        self.assertIsNone(data["athlete_id"])

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            user = db.query(User).one()
            self.assertIsNone(user.phone)
            self.assertEqual(user.email, "runner@example.com")
            aliases = db.query(AccountAlias).order_by(AccountAlias.provider).all()
            self.assertEqual(len(aliases), 2)
            google_alias = next(alias for alias in aliases if alias.provider == AuthProvider.GOOGLE)
            email_alias = next(alias for alias in aliases if alias.provider == AuthProvider.EMAIL)
            self.assertEqual(google_alias.provider_subject, "google-sub-1")
            self.assertEqual(google_alias.email, "runner@example.com")
            self.assertEqual(google_alias.display_name, "Runner One")
            self.assertEqual(google_alias.avatar_url, "https://example.com/avatar.png")
            self.assertEqual(email_alias.provider_subject, "runner@example.com")
        finally:
            db.close()

    def test_google_login_existing_user_without_athlete_still_requires_onboarding(self):
        import app.api.auth as auth_module

        original_client_id = auth_module.google_client_id
        original_verify = auth_module.google_id_token.verify_oauth2_token
        auth_module.google_client_id = lambda: "client-id"
        auth_module.google_id_token.verify_oauth2_token = lambda token, request, audience: {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-no-athlete",
            "email": "unfinished@example.com",
        }
        try:
            first = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
            second = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
        finally:
            auth_module.google_client_id = original_client_id
            auth_module.google_id_token.verify_oauth2_token = original_verify

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        data = second.json()
        self.assertFalse(data["is_new_user"])
        self.assertFalse(data["has_athlete"])
        self.assertIsNone(data["athlete_id"])

    def test_google_login_returns_default_athlete_when_onboarding_done(self):
        import app.api.auth as auth_module

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            user = User()
            db.add(user)
            db.flush()
            db.add(AccountAlias(
                user_id=user.id,
                provider=AuthProvider.GOOGLE,
                provider_subject="google-sub-with-athlete",
                email="runner@example.com",
            ))
            athlete = AthleteProfile(user_id=user.id, name="Runner", sport=SportType.MARATHON)
            db.add(athlete)
            db.commit()
            athlete_id = athlete.id
        finally:
            db.close()

        original_client_id = auth_module.google_client_id
        original_verify = auth_module.google_id_token.verify_oauth2_token
        auth_module.google_client_id = lambda: "client-id"
        auth_module.google_id_token.verify_oauth2_token = lambda token, request, audience: {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-with-athlete",
            "email": "runner@example.com",
        }
        try:
            res = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
        finally:
            auth_module.google_client_id = original_client_id
            auth_module.google_id_token.verify_oauth2_token = original_verify

        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["is_new_user"])
        self.assertTrue(data["has_athlete"])
        self.assertEqual(data["athlete_id"], athlete_id)

    def test_google_user_returns_athlete_after_authenticated_onboarding(self):
        import app.api.auth as auth_module

        original_client_id = auth_module.google_client_id
        original_verify = auth_module.google_id_token.verify_oauth2_token
        auth_module.google_client_id = lambda: "client-id"
        auth_module.google_id_token.verify_oauth2_token = lambda token, request, audience: {
            "iss": "https://accounts.google.com",
            "sub": "google-sub-onboarded",
            "email": "onboarded@example.com",
        }
        try:
            first = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
            token = first.json()["access_token"]
            athlete_res = self.client.post(
                "/athletes",
                json={"name": "Me", "sport": "marathon"},
                headers={"Authorization": f"Bearer {token}"},
            )
            second = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
        finally:
            auth_module.google_client_id = original_client_id
            auth_module.google_id_token.verify_oauth2_token = original_verify

        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["has_athlete"])
        self.assertEqual(athlete_res.status_code, 200)
        athlete_id = athlete_res.json()["id"]
        self.assertEqual(second.status_code, 200)
        data = second.json()
        self.assertFalse(data["is_new_user"])
        self.assertTrue(data["has_athlete"])
        self.assertEqual(data["athlete_id"], athlete_id)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            athlete = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).one()
            user = db.query(User).join(AccountAlias).filter(AccountAlias.provider_subject == "google-sub-onboarded").one()
            self.assertEqual(athlete.user_id, user.id)
        finally:
            db.close()

    def test_google_login_requires_configuration(self):
        import app.api.auth as auth_module

        original_client_id = auth_module.google_client_id
        auth_module.google_client_id = lambda: ""
        try:
            res = self.client.post("/auth/google", json={"id_token": "valid-google-token"})
        finally:
            auth_module.google_client_id = original_client_id
        self.assertEqual(res.status_code, 503)


class PasskeyAuthTestCase(AuthSetup):
    def _token(self):
        code = self.client.post("/auth/send-otp", json={"phone": "13800139999"}).json()["otp_code"]
        return self.client.post("/auth/verify-otp", json={"phone": "13800139999", "code": str(code)}).json()["access_token"]

    def test_register_options_requires_auth(self):
        res = self.client.post("/auth/passkeys/register/options")
        self.assertEqual(res.status_code, 401)

    def test_register_options_returns_public_key_options_and_stores_challenge(self):
        token = self._token()
        res = self.client.post("/auth/passkeys/register/options", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        options = res.json()["options"]
        self.assertEqual(options["rp"]["name"], "PerformanceProtocol")
        self.assertIn("challenge", options)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            challenge = db.query(AuthChallenge).filter(AuthChallenge.purpose == AuthChallengePurpose.PASSKEY_REGISTER).one()
            self.assertFalse(challenge.consumed)
            self.assertEqual(challenge.subject, "1")
        finally:
            db.close()

    def test_login_options_returns_allow_credentials_when_email_known(self):
        from app.db import SessionLocal

        db = SessionLocal()
        try:
            user = User()
            db.add(user)
            db.flush()
            db.add(AccountAlias(
                user_id=user.id,
                provider=AuthProvider.EMAIL,
                provider_subject="runner@example.com",
                email="runner@example.com",
            ))
            db.add(WebAuthnCredential(user_id=user.id, credential_id="YWJj", public_key=b"public", sign_count=0))
            db.commit()
        finally:
            db.close()

        res = self.client.post("/auth/passkeys/login/options", json={"email": "runner@example.com"})
        self.assertEqual(res.status_code, 200)
        options = res.json()["options"]
        self.assertEqual(options["rpId"], "localhost")
        self.assertEqual(options["allowCredentials"][0]["id"], "YWJj")


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
        self.assertEqual(res.status_code, 200)

        from app.db import SessionLocal

        db = SessionLocal()
        try:
            athlete = db.query(AthleteProfile).filter(AthleteProfile.id == res.json()["id"]).one()
            user = db.query(User).one()
            self.assertEqual(athlete.user_id, user.id)
        finally:
            db.close()

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
