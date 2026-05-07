import json
import os
import unittest
from datetime import UTC, datetime
from unittest.mock import patch

os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")
os.environ["COROS_AUTOMATION_MODE"] = "fake"
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AthleteProfile,
    AthleteActivity,
    ActivityDetailLap,
    ActivityDetailSample,
    DeviceAccount,
    DeviceType,
    ActivityDetailExport,
    ProviderRawRecord,
    ProviderSyncEvent,
    ProviderSyncJob,
    SportType,
)
from app.seed import seed_training_methods
from app.tools.coros.credentials import encrypt_secret
from app.tools.coros.full_sync import run_coros_full_sync_job
from app.tools.coros.automation import CorosLoginResult
from tests.helpers import auth, get_test_token


def _create_athlete() -> int:
    with SessionLocal() as db:
        athlete = AthleteProfile(
            name="Paul",
            sport=SportType.MARATHON,
            weekly_training_days=5,
        )
        db.add(athlete)
        db.commit()
        db.refresh(athlete)
        return athlete.id


class CapturingFullSyncClient:
    provider = "coros"

    def __init__(self) -> None:
        self.login_calls: list[tuple[str, str]] = []
        self.fit_export_calls: list[tuple[str, int]] = []

    def login(self, username: str, password: str) -> CorosLoginResult:
        self.login_calls.append((username, password))
        return CorosLoginResult(ok=True, message="ok")

    def fetch_full_history(self, username: str, progress=None) -> dict:
        if progress:
            progress("activity_list", "Read activity list", processed=1, total=1)
            progress("activity_details", "Read activity detail", processed=1, total=1)
        return {
            "activities": [
                {
                    "provider_activity_id": "act-1",
                    "sport": "running",
                    "discipline": "run",
                    "started_at": datetime(2026, 5, 1, 8, 0, tzinfo=UTC),
                    "timezone": "UTC+8",
                    "duration_sec": 3600,
                    "moving_duration_sec": 3500,
                    "distance_m": 10000,
                    "elevation_gain_m": 42,
                    "avg_pace_sec_per_km": 360,
                    "avg_hr": 145,
                    "max_hr": 168,
                    "avg_cadence": 174,
                    "avg_power": None,
                    "training_load": 80,
                    "perceived_effort": None,
                    "feedback_text": "Morning run",
                    "laps": [],
                    "raw_payload": {"labelId": "act-1", "detail": {"samples": [1, 2, 3]}},
                }
            ],
            "metrics": [
                {
                    "measured_at": datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
                    "metric_type": "lthr",
                    "value": 170,
                    "unit": "bpm",
                    "raw_payload": {"source": "dashboard"},
                }
            ],
            "raw_records": [
                {
                    "record_type": "activity_list_page",
                    "provider_record_id": "activity.query.page.1",
                    "endpoint": "/activity/query?pageNumber=1&size=20",
                    "payload": {"dataList": [{"labelId": "act-1"}], "totalPage": 1},
                },
                {
                    "record_type": "activity_detail",
                    "provider_record_id": "act-1",
                    "endpoint": "/activity/detail/filter",
                    "payload": {"labelId": "act-1", "samples": [1, 2, 3]},
                },
            ],
            "stats": {"failed_count": 0},
        }

    def download_activity_fit_export(self, label_id: str, sport_type: int) -> dict:
        self.fit_export_calls.append((label_id, sport_type))
        raise RuntimeError("sample FIT unavailable")


class CorosFullSyncTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)
        self.token = get_test_token(self.client)

    def test_start_sync_requires_connected_account(self) -> None:
        athlete_id = _create_athlete()
        response = self.client.post(
            "/coros/sync/start",
            json={"athlete_id": athlete_id},
            headers=auth(self.token),
        )

        self.assertEqual(400, response.status_code, response.text)
        self.assertIn("COROS account not connected", response.text)

    def test_start_sync_returns_existing_active_job(self) -> None:
        athlete_id = _create_athlete()
        with SessionLocal() as db:
            db.add(
                DeviceAccount(
                    athlete_id=athlete_id,
                    device_type=DeviceType.COROS,
                    external_user_id="runner@example.com",
                    username="runner@example.com",
                    encrypted_password=encrypt_secret("db-password"),
                    auth_status="connected",
                )
            )
            job = ProviderSyncJob(
                athlete_id=athlete_id,
                provider="coros",
                status="running",
                phase="activity_details",
                message="Already syncing",
            )
            db.add(job)
            db.commit()
            expected_job_id = job.id

        response = self.client.post(
            "/coros/sync/start",
            json={"athlete_id": athlete_id},
            headers=auth(self.token),
        )

        self.assertEqual(200, response.status_code, response.text)
        self.assertEqual(expected_job_id, response.json()["id"])
        self.assertEqual("running", response.json()["status"])

    def test_run_full_sync_uses_db_credentials_and_stores_raw_records(self) -> None:
        athlete_id = _create_athlete()
        with SessionLocal() as db:
            db.add(
                DeviceAccount(
                    athlete_id=athlete_id,
                    device_type=DeviceType.COROS,
                    external_user_id="runner@example.com",
                    username="runner@example.com",
                    encrypted_password=encrypt_secret("db-password"),
                    auth_status="connected",
                )
            )
            job = ProviderSyncJob(
                athlete_id=athlete_id,
                provider="coros",
                status="queued",
                phase="queued",
                message="Queued",
            )
            db.add(job)
            db.commit()
            job_id = job.id

        sync_client = CapturingFullSyncClient()
        with patch("app.tools.coros.full_sync.coros_automation_client", return_value=sync_client):
            run_coros_full_sync_job(job_id)

        self.assertEqual([("runner@example.com", "db-password")], sync_client.login_calls)
        self.assertEqual([("act-1", 100)], sync_client.fit_export_calls)
        with SessionLocal() as db:
            job = db.get(ProviderSyncJob, job_id)
            self.assertEqual("succeeded", job.status)
            self.assertEqual(1, job.imported_count)
            self.assertEqual(1, job.metric_count)
            self.assertEqual(2, job.raw_record_count)
            self.assertEqual(1, job.failed_count)
            raw_records = db.query(ProviderRawRecord).order_by(ProviderRawRecord.id.asc()).all()
            self.assertEqual(2, len(raw_records))
            detail = next(record for record in raw_records if record.record_type == "activity_detail")
            self.assertEqual("act-1", detail.provider_record_id)
            self.assertEqual([1, 2, 3], json.loads(detail.payload_json)["samples"])
            events = db.query(ProviderSyncEvent).filter(ProviderSyncEvent.job_id == job_id).all()
            self.assertGreaterEqual(len(events), 3)

    def test_activity_detail_api_returns_source_gps_laps_and_interpretation(self) -> None:
        athlete_id = _create_athlete()
        with SessionLocal() as db:
            activity = AthleteActivity(
                athlete_id=athlete_id,
                provider="coros",
                provider_activity_id="act-detail-1",
                sport="running",
                discipline="run",
                started_at=datetime(2026, 5, 5, 0, 45, tzinfo=UTC),
                timezone="UTC+8",
                duration_sec=120,
                moving_duration_sec=120,
                distance_m=400,
                avg_pace_sec_per_km=300,
                avg_hr=140,
                feedback_text="Beijing run",
            )
            db.add(activity)
            db.flush()
            db.add(
                ActivityDetailExport(
                    athlete_id=athlete_id,
                    activity_id=activity.id,
                    provider="coros",
                    provider_activity_id="act-detail-1",
                    source_format="fit",
                    file_size_bytes=100,
                    payload_hash="abc",
                    downloaded_at=datetime(2026, 5, 5, 1, 0, tzinfo=UTC),
                    parsed_at=datetime(2026, 5, 5, 1, 1, tzinfo=UTC),
                    sample_count=3,
                    lap_count=1,
                    warnings_json="[]",
                    raw_file_bytes=b"fit",
                )
            )
            for index in range(3):
                db.add(
                    ActivityDetailSample(
                        activity_id=activity.id,
                        sample_index=index,
                        timestamp=datetime(2026, 5, 5, 0, 45, index, tzinfo=UTC),
                        elapsed_sec=index,
                        distance_m=index * 100,
                        latitude=40.0 + index * 0.001,
                        longitude=116.0 + index * 0.001,
                        heart_rate=140 + index,
                        pace_sec_per_km=300 + index,
                    )
                )
            db.add(
                ActivityDetailLap(
                    activity_id=activity.id,
                    lap_index=0,
                    duration_sec=120,
                    distance_m=400,
                    avg_hr=141,
                )
            )
            db.commit()
            activity_id = activity.id

        response = self.client.get(
            f"/athletes/{athlete_id}/activities/{activity_id}?sample_limit=100",
            headers=auth(self.token),
        )

        self.assertEqual(200, response.status_code, response.text)
        payload = response.json()
        self.assertEqual("act-detail-1", payload["activity"]["provider_activity_id"])
        self.assertEqual("fit", payload["source"]["source_format"])
        self.assertEqual(3, payload["source"]["stored_sample_count"])
        self.assertEqual(3, len(payload["samples"]))
        self.assertEqual(1, len(payload["laps"]))
        self.assertAlmostEqual(40.0, payload["route_bounds"]["min_latitude"])
        self.assertIn("3 GPS points", payload["interpretation"]["data_quality"])


if __name__ == "__main__":
    unittest.main()
