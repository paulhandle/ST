import unittest
import os

os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")
os.environ["COROS_AUTOMATION_MODE"] = "fake"
os.environ["OPENAI_API_KEY"] = ""  # empty string: setdefault in load_local_env won't overwrite  # force rule-based skill path; deterministic + fast

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_training_methods
from tests.helpers import get_test_token, auth


class CorosMarathonMvpWorkflowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)
        self.token = get_test_token(self.client)

    def test_coros_marathon_closed_loop(self) -> None:
        athlete_resp = self.client.post(
            "/athletes",
            json={
                "name": "Paul",
                "sport": "marathon",
                "level": "intermediate",
                "weekly_training_days": 5,
            },
            headers=auth(self.token),
        )
        self.assertEqual(200, athlete_resp.status_code)
        athlete_id = athlete_resp.json()["id"]

        connect_resp = self.client.post(
            "/coros/connect",
            json={
                "athlete_id": athlete_id,
                "username": "paul@example.com",
                "password": "secret",
            },
            headers=auth(self.token),
        )
        self.assertEqual(200, connect_resp.status_code)
        self.assertEqual("connected", connect_resp.json()["auth_status"])
        self.assertNotIn("password", connect_resp.text)

        import_resp = self.client.post(
            f"/coros/import?athlete_id={athlete_id}",
            json={"device_type": "coros"},
            headers=auth(self.token),
        )
        self.assertEqual(200, import_resp.status_code)
        self.assertGreater(import_resp.json()["imported_count"], 0)

        assessment_resp = self.client.post(
            f"/athletes/{athlete_id}/assessment/run"
            "?target_time_sec=14400&plan_weeks=16&weekly_training_days=5",
            headers=auth(self.token),
        )
        self.assertEqual(200, assessment_resp.status_code)
        assessment = assessment_resp.json()
        self.assertIn(assessment["goal_status"], ["accept", "accept_with_warning"])
        self.assertGreaterEqual(assessment["overall_score"], 50)

        plan_resp = self.client.post(
            "/marathon/plans/generate",
            json={
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
            },
            headers=auth(self.token),
        )
        self.assertEqual(200, plan_resp.status_code, plan_resp.text)
        plan = plan_resp.json()
        plan_id = plan["id"]
        self.assertEqual(16, plan["weeks"])
        self.assertGreater(len(plan["structured_workouts"]), 0)
        self.assertGreater(len(plan["structured_workouts"][0]["steps"]), 0)

        confirm_resp = self.client.post(f"/plans/{plan_id}/confirm", headers=auth(self.token))
        self.assertEqual(200, confirm_resp.status_code)
        self.assertTrue(confirm_resp.json()["confirmed"])

        sync_resp = self.client.post(f"/plans/{plan_id}/sync/coros", headers=auth(self.token))
        self.assertEqual(200, sync_resp.status_code, sync_resp.text)
        sync_data = sync_resp.json()
        self.assertGreater(sync_data["synced_count"], 0)
        self.assertEqual(0, sync_data["failed_count"])

        adjustment_resp = self.client.post(f"/plans/{plan_id}/adjustments/evaluate", headers=auth(self.token))
        self.assertEqual(200, adjustment_resp.status_code)
        adjustment = adjustment_resp.json()
        self.assertEqual("proposed", adjustment["status"])
        self.assertIn("recommendation", adjustment)


if __name__ == "__main__":
    unittest.main()
