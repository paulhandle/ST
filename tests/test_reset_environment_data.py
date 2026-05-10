from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import (
    AccountAlias,
    AthleteActivity,
    AthleteLevel,
    AthleteProfile,
    AuthChallenge,
    AuthChallengePurpose,
    AuthProvider,
    CoachMessage,
    OTPCode,
    SportType,
    TrainingMethod,
    User,
)
from app.training.knowledge_base import TRAINING_METHOD_DEFINITIONS
from scripts.reset_environment_data import reset_environment_data


class ResetEnvironmentDataTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "reset-test.db"
        self.database_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(self.database_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self._seed_rows()

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_reports_rows_without_deleting(self):
        result = reset_environment_data(self.database_url, execute=False)

        self.assertTrue(result.dry_run)
        self.assertGreater(result.target_total, 0)
        self.assertEqual(result.preserved_tables["training_methods"], len(TRAINING_METHOD_DEFINITIONS))

        with self.Session() as db:
            self.assertEqual(db.query(User).count(), 1)
            self.assertEqual(db.query(AthleteProfile).count(), 1)
            self.assertEqual(db.query(TrainingMethod).count(), len(TRAINING_METHOD_DEFINITIONS))

    def test_execute_requires_confirmation(self):
        with self.assertRaises(ValueError):
            reset_environment_data(self.database_url, execute=True)

    def test_execute_deletes_environment_data_and_preserves_seed(self):
        result = reset_environment_data(self.database_url, execute=True, confirm_reset=True)

        self.assertFalse(result.dry_run)
        self.assertGreater(result.deleted_total, 0)

        with self.Session() as db:
            self.assertEqual(db.query(User).count(), 0)
            self.assertEqual(db.query(AccountAlias).count(), 0)
            self.assertEqual(db.query(AthleteProfile).count(), 0)
            self.assertEqual(db.query(AthleteActivity).count(), 0)
            self.assertEqual(db.query(CoachMessage).count(), 0)
            self.assertEqual(db.query(OTPCode).count(), 0)
            self.assertEqual(db.query(AuthChallenge).count(), 0)
            self.assertEqual(db.query(TrainingMethod).count(), len(TRAINING_METHOD_DEFINITIONS))

            next_user = User()
            db.add(next_user)
            db.commit()
            self.assertEqual(next_user.id, 1)

    def _seed_rows(self):
        from datetime import UTC, datetime, timedelta

        with self.Session() as db:
            for item in TRAINING_METHOD_DEFINITIONS:
                db.add(TrainingMethod(**item))
            user = User()
            db.add(user)
            db.flush()
            db.add(AccountAlias(
                user_id=user.id,
                provider=AuthProvider.EMAIL,
                provider_subject="runner@example.com",
                email="runner@example.com",
            ))
            athlete = AthleteProfile(
                user_id=user.id,
                name="Runner",
                sport=SportType.MARATHON,
                level=AthleteLevel.BEGINNER,
            )
            db.add(athlete)
            db.flush()
            activity = AthleteActivity(
                athlete_id=athlete.id,
                provider="coros",
                provider_activity_id="activity-1",
                sport="running",
                discipline="run",
                started_at=datetime.now(UTC),
                duration_sec=1800,
                distance_m=5000,
            )
            db.add(activity)
            db.add(CoachMessage(athlete_id=athlete.id, role="user", text="hello"))
            db.add(OTPCode(
                phone="+8613800138000",
                code="123456",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            ))
            db.add(AuthChallenge(
                purpose=AuthChallengePurpose.PASSKEY_LOGIN,
                subject="runner@example.com",
                challenge="challenge",
                expires_at=datetime.now(UTC) + timedelta(minutes=5),
            ))
            db.commit()


if __name__ == "__main__":
    unittest.main()
