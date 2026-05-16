import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def _get_token() -> str:
    send = client.post("/auth/send-otp", json={"phone": "13900000099"})
    code = str(send.json()["otp_code"])
    res = client.post("/auth/verify-otp", json={"phone": "13900000099", "code": code})
    return res.json()["access_token"]


def _create_athlete_for_token(token: str) -> int:
    r = client.post(
        "/athletes",
        json={"name": "RevokeTest", "sport": "marathon", "level": "intermediate", "weekly_training_days": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _generate_and_confirm_plan(token: str, athlete_id: int) -> int:
    body = {
        "athlete_id": athlete_id,
        "target_time_sec": 14400,
        "plan_weeks": 16,
        "availability": {
            "weekly_training_days": 5,
            "preferred_long_run_weekday": 6,
            "unavailable_weekdays": [0],
            "max_weekday_duration_min": 90,
            "max_weekend_duration_min": 210,
            "strength_training_enabled": True,
        },
        "skill_slug": "marathon_st_default",
    }
    r = client.post("/marathon/plans/generate", json=body, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    plan_id = r.json()["id"]
    confirm = client.post(f"/plans/{plan_id}/confirm", headers={"Authorization": f"Bearer {token}"})
    assert confirm.status_code == 200, confirm.text
    return plan_id


class WorkoutByDateTestCase(unittest.TestCase):

    def setUp(self):
        from app.db import engine, Base
        Base.metadata.create_all(bind=engine)
        self.token = _get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        r = client.post("/athletes", json={
            "name": "BlockE", "sport": "marathon",
            "level": "intermediate", "weekly_training_days": 5,
        }, headers=self.headers)
        self.athlete_id = r.json()["id"]

    def test_no_plan_returns_200_with_null_workout(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/2099-06-15",
                       headers=self.headers)
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIsNone(body["workout"])
        self.assertIsNone(body["plan_id"])

    def test_invalid_date_returns_422(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/not-a-date",
                       headers=self.headers)
        self.assertEqual(r.status_code, 422)

    def test_requires_auth(self):
        r = client.get(f"/athletes/{self.athlete_id}/workout/2099-06-15")
        self.assertEqual(r.status_code, 401)

    def test_revoke_plan_resets_to_draft(self):
        """POST /marathon/plans/{id}/revoke sets status=draft and is_confirmed=False."""
        token = _get_token()
        athlete_id = _create_athlete_for_token(token)
        plan_id = _generate_and_confirm_plan(token, athlete_id)

        # Confirm it is active
        res = client.get(f"/marathon/plans/{plan_id}", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["is_confirmed"])

        # Revoke it
        res = client.post(f"/marathon/plans/{plan_id}/revoke", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["status"], "draft")
        self.assertFalse(body["is_confirmed"])


if __name__ == "__main__":
    unittest.main()
