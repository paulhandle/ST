"""Block A backend endpoints (skills, today/week, feedback, regenerate, match)."""
import os
import unittest
from datetime import UTC, date, datetime, timedelta

os.environ["COROS_AUTOMATION_MODE"] = "fake"
os.environ.pop("OPENAI_API_KEY", None)  # force rule-based skill path; deterministic + fast

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AthleteActivity,
    PlanStatus,
    StructuredWorkout,
    TrainingPlan,
)
from app.seed import seed_training_methods


def _create_athlete(client: TestClient) -> int:
    r = client.post(
        "/athletes",
        json={
            "name": "Paul",
            "sport": "marathon",
            "level": "intermediate",
            "weekly_training_days": 5,
        },
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _generate_marathon_plan(
    client: TestClient,
    athlete_id: int,
    skill_slug: str = "marathon_st_default",
) -> dict:
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
        "skill_slug": skill_slug,
    }
    r = client.post("/marathon/plans/generate", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def _bootstrap_history(client: TestClient, athlete_id: int) -> None:
    """Run the COROS connect+import flow so the assessment has data."""
    r = client.post(
        "/coros/connect",
        json={"athlete_id": athlete_id, "username": "p@x.com", "password": "x"},
    )
    assert r.status_code == 200, r.text
    r = client.post(
        f"/coros/import?athlete_id={athlete_id}",
        json={"device_type": "coros"},
    )
    assert r.status_code == 200, r.text


class BlockASkillCatalogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_list_skills_returns_both_built_in_and_user_extracted(self) -> None:
        r = self.client.get("/skills")
        self.assertEqual(200, r.status_code, r.text)
        items = r.json()
        slugs = {item["slug"] for item in items}
        self.assertIn("marathon_st_default", slugs)
        self.assertIn("coach_zhao_unified", slugs)
        self.assertGreaterEqual(len(items), 2)
        # All entries have the manifest fields.
        for item in items:
            self.assertIn("name", item)
            self.assertIn("version", item)
            self.assertIn("sport", item)
            self.assertIn("supported_goals", item)
            self.assertIsInstance(item["tags"], list)

    def test_get_skill_detail_returns_methodology(self) -> None:
        r = self.client.get("/skills/marathon_st_default")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual("marathon_st_default", body["slug"])
        self.assertTrue(body["methodology_md"], "methodology_md should not be empty")
        self.assertGreater(len(body["methodology_md"]), 50)

    def test_get_unknown_skill_returns_404(self) -> None:
        r = self.client.get("/skills/this_does_not_exist")
        self.assertEqual(404, r.status_code)


class BlockAGenerateWithSkillSlugTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_generate_with_default_skill(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id, "marathon_st_default")
        self.assertEqual(16, plan["weeks"])
        self.assertGreater(len(plan["structured_workouts"]), 0)

    def test_generate_with_coach_zhao_skill(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id, "coach_zhao_unified")
        self.assertGreater(len(plan["structured_workouts"]), 0)
        # The plan should be persisted with the skill slug.
        with SessionLocal() as db:
            row = db.get(TrainingPlan, plan["id"])
            self.assertEqual("coach_zhao_unified", row.active_skill_slug)


class BlockATodayTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_today_no_plan_returns_404(self) -> None:
        athlete_id = _create_athlete(self.client)
        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(404, r.status_code)

    def test_today_rest_day_returns_null_workout(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        # Move all workouts away from today so we get the rest-day case.
        with SessionLocal() as db:
            tomorrow = date.today() + timedelta(days=1)
            workouts = db.execute(
                StructuredWorkout.__table__.select().where(
                    StructuredWorkout.plan_id == plan_id
                )
            ).fetchall()
            for row in workouts:
                w = db.get(StructuredWorkout, row.id)
                if w.scheduled_date == date.today():
                    w.scheduled_date = tomorrow
            db.commit()

        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(plan_id, body["plan_id"])
        self.assertIsNone(body["workout"])

    def test_today_with_workout_today(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        # Force one workout to be scheduled today so the route can return it.
        with SessionLocal() as db:
            w = db.execute(
                StructuredWorkout.__table__.select()
                .where(StructuredWorkout.plan_id == plan_id)
                .order_by(StructuredWorkout.id.asc())
                .limit(1)
            ).fetchone()
            workout = db.get(StructuredWorkout, w.id)
            workout.scheduled_date = date.today()
            db.commit()

        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(plan_id, body["plan_id"])
        self.assertIsNotNone(body["workout"])
        self.assertIsNotNone(body["week_index"])


class BlockAWeekViewTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_week_view_returns_expected_shape(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        r = self.client.get(f"/plans/{plan_id}/week", params={"week_index": 1})
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(plan_id, body["plan_id"])
        self.assertEqual(1, body["week_index"])
        self.assertIn(body["phase"], ("base", "block", "taper", "unknown"))
        self.assertIsInstance(body["is_recovery"], bool)
        self.assertIsInstance(body["total_distance_m"], (int, float))
        self.assertIsInstance(body["total_duration_min"], int)
        self.assertIsInstance(body["quality_count"], int)
        self.assertIsInstance(body["workouts"], list)
        self.assertGreater(len(body["workouts"]), 0)

    def test_week_view_missing_plan_returns_404(self) -> None:
        r = self.client.get("/plans/999999/week", params={"week_index": 1})
        self.assertEqual(404, r.status_code)


class BlockAFeedbackTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def _fresh_workout_id(self) -> int:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        return plan["structured_workouts"][0]["id"]

    def test_feedback_completed_updates_workout_status(self) -> None:
        wid = self._fresh_workout_id()
        r = self.client.post(
            f"/workouts/{wid}/feedback",
            json={"status": "completed", "rpe": 6, "note": "felt great"},
        )
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual("completed", body["status"])
        self.assertEqual(6, body["rpe"])
        with SessionLocal() as db:
            w = db.get(StructuredWorkout, wid)
            self.assertEqual("completed", w.status.value)

    def test_feedback_skipped_marks_missed(self) -> None:
        wid = self._fresh_workout_id()
        r = self.client.post(
            f"/workouts/{wid}/feedback",
            json={"status": "skipped", "rpe": None, "note": None},
        )
        self.assertEqual(200, r.status_code, r.text)
        with SessionLocal() as db:
            w = db.get(StructuredWorkout, wid)
            self.assertEqual("missed", w.status.value)

    def test_feedback_invalid_status_rejected(self) -> None:
        wid = self._fresh_workout_id()
        r = self.client.post(
            f"/workouts/{wid}/feedback",
            json={"status": "bogus", "rpe": 5, "note": None},
        )
        self.assertEqual(422, r.status_code)

    def test_feedback_invalid_rpe_rejected(self) -> None:
        wid = self._fresh_workout_id()
        r = self.client.post(
            f"/workouts/{wid}/feedback",
            json={"status": "completed", "rpe": 99, "note": None},
        )
        self.assertEqual(422, r.status_code)

    def test_feedback_long_note_rejected(self) -> None:
        wid = self._fresh_workout_id()
        r = self.client.post(
            f"/workouts/{wid}/feedback",
            json={"status": "completed", "rpe": 5, "note": "x" * 600},
        )
        self.assertEqual(422, r.status_code)


class BlockAMatchActivityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_imported_activity_is_matched_to_planned_workout(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]

        # Confirm the plan so it's ACTIVE — that's what match_activity_to_workout looks for.
        confirm = self.client.post(f"/plans/{plan_id}/confirm")
        self.assertEqual(200, confirm.status_code, confirm.text)

        # Pick a workout and force its date to today.
        with SessionLocal() as db:
            w = db.execute(
                StructuredWorkout.__table__.select()
                .where(StructuredWorkout.plan_id == plan_id)
                .order_by(StructuredWorkout.id.asc())
                .limit(1)
            ).fetchone()
            workout = db.get(StructuredWorkout, w.id)
            workout.scheduled_date = date.today()
            workout_id = workout.id
            db.commit()

        # Insert an activity for today — same discipline ("run") — through the
        # ingestion service so the auto-match path runs.
        from app.ingestion.service import import_provider_history
        from app.models import AthleteProfile

        with SessionLocal() as db:
            athlete = db.get(AthleteProfile, athlete_id)
            today_dt = datetime.combine(date.today(), datetime.min.time()).replace(hour=7)
            activity_payload = [
                {
                    "provider_activity_id": "test-activity-today",
                    "sport": "running",
                    "discipline": "run",
                    "started_at": today_dt,
                    "duration_sec": 3000,
                    "distance_m": 9000.0,
                    "avg_pace_sec_per_km": 333.0,
                }
            ]
            import_provider_history(
                db=db, athlete=athlete, provider="manual", activities=activity_payload
            )

        with SessionLocal() as db:
            activity = db.execute(
                AthleteActivity.__table__.select().where(
                    AthleteActivity.provider_activity_id == "test-activity-today"
                )
            ).fetchone()
            self.assertEqual(workout_id, activity.matched_workout_id)

        # Match-status endpoint reflects the same.
        r = self.client.get(f"/workouts/{workout_id}/match-status")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(workout_id, body["workout_id"])
        self.assertIsNotNone(body["matched_activity"])
        self.assertIsNotNone(body["diff"])

    def test_today_includes_matched_activity_id_when_present(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        confirm = self.client.post(f"/plans/{plan_id}/confirm")
        self.assertEqual(200, confirm.status_code, confirm.text)

        with SessionLocal() as db:
            w = db.execute(
                StructuredWorkout.__table__.select()
                .where(StructuredWorkout.plan_id == plan_id)
                .order_by(StructuredWorkout.id.asc())
                .limit(1)
            ).fetchone()
            workout = db.get(StructuredWorkout, w.id)
            workout.scheduled_date = date.today()
            workout_id = workout.id
            db.commit()

        from app.ingestion.service import import_provider_history
        from app.models import AthleteProfile

        with SessionLocal() as db:
            athlete = db.get(AthleteProfile, athlete_id)
            today_dt = datetime.combine(date.today(), datetime.min.time()).replace(hour=7)
            import_provider_history(
                db=db,
                athlete=athlete,
                provider="manual",
                activities=[
                    {
                        "provider_activity_id": "test-activity-today-2",
                        "sport": "running",
                        "discipline": "run",
                        "started_at": today_dt,
                        "duration_sec": 3000,
                        "distance_m": 9000.0,
                        "avg_pace_sec_per_km": 333.0,
                    }
                ],
            )

        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertIsNotNone(body["matched_activity_id"])


if __name__ == "__main__":
    unittest.main()
