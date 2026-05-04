import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def _get_token() -> str:
    send = client.post("/auth/send-otp", json={"phone": "13900000077"})
    code = str(send.json()["otp_code"])
    res = client.post("/auth/verify-otp", json={"phone": "13900000077", "code": code})
    return res.json()["access_token"]


class CalendarEndpointTestCase(unittest.TestCase):

    def setUp(self):
        from app.db import engine, Base
        Base.metadata.create_all(bind=engine)
        self.token = _get_token()
        self.headers = {"Authorization": f"Bearer {self.token}"}
        r = client.post("/athletes", json={
            "name": "CalTest", "sport": "marathon",
            "level": "intermediate", "weekly_training_days": 5,
        }, headers=self.headers)
        self.athlete_id = r.json()["id"]

    def test_empty_range_returns_empty_list(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "2099-01-01", "to_date": "2099-01-31"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json(), [])

    def test_invalid_date_returns_422(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "not-a-date", "to_date": "2099-01-31"},
            headers=self.headers,
        )
        self.assertEqual(r.status_code, 422)

    def test_requires_auth(self):
        r = client.get(
            f"/athletes/{self.athlete_id}/calendar",
            params={"from_date": "2099-01-01", "to_date": "2099-01-31"},
        )
        self.assertEqual(r.status_code, 401)


if __name__ == "__main__":
    unittest.main()
