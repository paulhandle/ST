import unittest
import os

os.environ["COROS_AUTOMATION_MODE"] = "fake"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_training_methods


class HistoryAssessmentWorkflowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_import_history_and_assessment_workflow(self) -> None:
        athlete_resp = self.client.post(
            "/athletes",
            json={
                "name": "Paul",
                "sport": "marathon",
                "level": "intermediate",
                "weekly_training_days": 5,
            },
        )
        self.assertEqual(200, athlete_resp.status_code)
        athlete_id = athlete_resp.json()["id"]

        connect_resp = self.client.post(
            "/devices/connect",
            json={
                "athlete_id": athlete_id,
                "device_type": "garmin",
                "external_user_id": "garmin_user_001",
            },
        )
        self.assertEqual(200, connect_resp.status_code)

        import_resp = self.client.post(
            f"/athletes/{athlete_id}/history/import",
            json={"device_type": "garmin"},
        )
        self.assertEqual(200, import_resp.status_code)
        self.assertGreater(import_resp.json()["imported_count"], 0)

        history_resp = self.client.get(f"/athletes/{athlete_id}/history")
        self.assertEqual(200, history_resp.status_code)
        self.assertGreater(len(history_resp.json()), 0)

        assessment_resp = self.client.get(f"/athletes/{athlete_id}/assessment")
        self.assertEqual(200, assessment_resp.status_code)
        assessment_data = assessment_resp.json()
        self.assertIn("overall_score", assessment_data)
        self.assertIn("summary", assessment_data)


if __name__ == "__main__":
    unittest.main()
