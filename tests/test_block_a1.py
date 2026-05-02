"""Block A1 backend endpoints (dashboard, volume curve, regenerate preview,
adjustment apply, coach chat, history/today enrichments)."""
import json
import os
import unittest
from datetime import UTC, date, datetime, timedelta

os.environ["COROS_AUTOMATION_MODE"] = "fake"
# Ensure the LLM path is disabled in tests. We must set this BEFORE importing
# app.main, which transitively loads .env via app.core.config.load_local_env()
# (which uses os.environ.setdefault — so a pre-existing empty value sticks).
os.environ["OPENAI_API_KEY"] = ""

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AdjustmentStatus,
    AthleteActivity,
    AthleteMetricSnapshot,
    AthleteProfile,
    CoachMessage,
    PlanAdjustment,
    PlanStatus,
    StructuredWorkout,
    TrainingPlan,
    WorkoutFeedback,
    WorkoutStatus,
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


def _force_workout_today(plan_id: int) -> int:
    """Force the first workout of the plan onto today and return its id."""
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
        return workout.id


class BlockA1DashboardNoPlanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_dashboard_no_plan_returns_valid_payload(self) -> None:
        athlete_id = _create_athlete(self.client)
        r = self.client.get(f"/athletes/{athlete_id}/dashboard")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(athlete_id, body["athlete"]["id"])
        self.assertIsNone(body["athlete"]["current_skill"])
        self.assertIn(body["greeting"]["time_of_day"], ("morning", "afternoon", "evening"))
        self.assertIsNone(body["today"]["plan_id"])
        self.assertIsNone(body["today"]["workout"])
        self.assertEqual([], body["this_week"]["days"])
        self.assertEqual([], body["volume_history"])
        self.assertEqual([], body["recent_activities"])
        self.assertEqual([], body["goal"]["prediction_history"])
        self.assertIsNone(body["pending_adjustment"])
        self.assertEqual("never", body["meta"]["last_sync_status"])


class BlockA1DashboardWithPlanTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_dashboard_with_plan_no_activities_today(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        _force_workout_today(plan_id)

        r = self.client.get(f"/athletes/{athlete_id}/dashboard")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual(plan_id, body["today"]["plan_id"])
        self.assertIsNotNone(body["today"]["workout"])
        self.assertEqual(plan_id, body["this_week"]["plan_id"])
        self.assertEqual(plan["weeks"], body["this_week"]["total_weeks"])
        self.assertGreater(len(body["this_week"]["days"]), 0)
        # volume history non-empty when there's a current week
        self.assertGreater(len(body["volume_history"]), 0)
        # current week flag set
        currents = [v for v in body["volume_history"] if v["is_current"]]
        self.assertEqual(1, len(currents))

    def test_dashboard_with_imports_volume_history_has_executed_and_predictions(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        _force_workout_today(plan_id)

        # Insert some activities that fall inside the current week.
        with SessionLocal() as db:
            athlete = db.get(AthleteProfile, athlete_id)
            today_dt = datetime.combine(date.today(), datetime.min.time()).replace(hour=7)
            from app.ingestion.service import import_provider_history
            import_provider_history(
                db=db,
                athlete=athlete,
                provider="manual",
                activities=[
                    {
                        "provider_activity_id": "a1-today",
                        "sport": "running",
                        "discipline": "run",
                        "started_at": today_dt,
                        "duration_sec": 3000,
                        "distance_m": 10000.0,
                        "avg_pace_sec_per_km": 300.0,
                    }
                ],
            )
            # Insert race predictor snapshots ~1 month apart for delta calc.
            # The bootstrap fake also inserts one at today 07:00 with 14400, so
            # the new "latest" snapshot must be truly later than that.
            now = datetime.now(UTC).replace(tzinfo=None)
            future = now.replace(hour=23, minute=59, second=0, microsecond=0)
            db.add(AthleteMetricSnapshot(
                athlete_id=athlete_id,
                provider="coros",
                measured_at=future - timedelta(days=40),
                metric_type="race_predictor_marathon",
                value=14400.0,
                unit="sec",
            ))
            db.add(AthleteMetricSnapshot(
                athlete_id=athlete_id,
                provider="coros",
                measured_at=future,
                metric_type="race_predictor_marathon",
                value=14100.0,
                unit="sec",
            ))
            db.commit()

        r = self.client.get(f"/athletes/{athlete_id}/dashboard")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        # At least one volume_history week has executed_km > 0
        any_executed = any(v["executed_km"] > 0 for v in body["volume_history"])
        self.assertTrue(any_executed)
        # Prediction history non-empty and monthly_delta_sec negative (faster).
        self.assertGreaterEqual(len(body["goal"]["prediction_history"]), 2)
        self.assertIsNotNone(body["goal"]["monthly_delta_sec"])
        self.assertLess(body["goal"]["monthly_delta_sec"], 0)


class BlockA1VolumeCurveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_volume_curve_returns_all_weeks(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        r = self.client.get(f"/plans/{plan_id}/volume-curve")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        # Expect roughly 16 weeks (the plan was generated for plan_weeks=16).
        self.assertGreater(len(body["weeks"]), 10)
        for w in body["weeks"]:
            self.assertIn(w["phase"], ("base", "block", "taper", "unknown"))
            self.assertIsInstance(w["planned_km"], (int, float))
            self.assertIsInstance(w["executed_km"], (int, float))
            self.assertIsInstance(w["longest_run_km"], (int, float))
        # Peak planned should equal max planned across weeks.
        max_planned = max(w["planned_km"] for w in body["weeks"])
        self.assertEqual(round(max_planned, 2), round(body["peak_planned_km"], 2))


class BlockA1RegeneratePreviewTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_regenerate_preview_applicable(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id, "marathon_st_default")
        plan_id = plan["id"]
        r = self.client.get(
            f"/plans/{plan_id}/regenerate-preview",
            params={"skill_slug": "coach_zhao_unified"},
        )
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertTrue(body["applicable"])
        self.assertGreaterEqual(body["weeks_affected"], 0)
        self.assertEqual("coach_zhao_unified", body["new_skill_slug"])

    def test_regenerate_preview_not_applicable_due_to_short_plan(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id, "marathon_st_default")
        plan_id = plan["id"]
        # Force most workouts before today so derived plan_weeks is too small for coach_zhao_unified (requires 12-24).
        with SessionLocal() as db:
            workouts = db.execute(
                StructuredWorkout.__table__.select().where(StructuredWorkout.plan_id == plan_id)
            ).fetchall()
            past = date.today() - timedelta(days=30)
            # Make all but the last 2 weeks fall in the past so frozen_week_count is high.
            for row in workouts:
                w = db.get(StructuredWorkout, row.id)
                if w.week_index <= 14:
                    w.scheduled_date = past
            db.commit()
        r = self.client.get(
            f"/plans/{plan_id}/regenerate-preview",
            params={"skill_slug": "coach_zhao_unified"},
        )
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertFalse(body["applicable"])
        self.assertIn("Plan weeks", body["applicability_reason"])


class BlockA1AdjustmentApplyTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def _make_plan_and_workout(self) -> tuple[int, int, int]:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        wid = plan["structured_workouts"][0]["id"]
        return athlete_id, plan_id, wid

    def _make_adjustment_with_diff(
        self, athlete_id: int, plan_id: int, affected: list[dict]
    ) -> int:
        with SessionLocal() as db:
            adj = PlanAdjustment(
                athlete_id=athlete_id,
                plan_id=plan_id,
                status=AdjustmentStatus.PROPOSED,
                reason="Test reason",
                recommendation="Apply diff",
                affected_workouts_json=json.dumps(affected),
            )
            db.add(adj)
            db.commit()
            db.refresh(adj)
            return adj.id

    def test_apply_distance_diff_updates_workout(self) -> None:
        athlete_id, plan_id, wid = self._make_plan_and_workout()
        affected = [
            {
                "workout_id": wid,
                "date": date.today().isoformat(),
                "title": "Test long run",
                "field": "distance_m",
                "before": "16 km",
                "after": "12 km",
                "note": None,
            }
        ]
        adj_id = self._make_adjustment_with_diff(athlete_id, plan_id, affected)

        r = self.client.post(
            f"/plan-adjustments/{adj_id}/apply", json={"selected_workout_ids": None}
        )
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual("confirmed", body["status"])

        with SessionLocal() as db:
            w = db.get(StructuredWorkout, wid)
            self.assertEqual(12000.0, w.distance_m)

    def test_apply_skip_marks_workout_missed(self) -> None:
        athlete_id, plan_id, wid = self._make_plan_and_workout()
        affected = [
            {
                "workout_id": wid,
                "date": date.today().isoformat(),
                "title": "Test long run",
                "field": "skip",
                "before": "16 km",
                "after": "skipped",
                "note": "fatigue",
            }
        ]
        adj_id = self._make_adjustment_with_diff(athlete_id, plan_id, affected)

        r = self.client.post(
            f"/plan-adjustments/{adj_id}/apply", json={"selected_workout_ids": None}
        )
        self.assertEqual(200, r.status_code, r.text)
        with SessionLocal() as db:
            w = db.get(StructuredWorkout, wid)
            self.assertEqual(WorkoutStatus.MISSED, w.status)
            self.assertEqual(0, w.distance_m)

    def test_apply_invalid_workout_id_returns_422(self) -> None:
        athlete_id, plan_id, _wid = self._make_plan_and_workout()
        affected = [
            {
                "workout_id": 999999,
                "date": date.today().isoformat(),
                "title": "Bogus",
                "field": "distance_m",
                "before": "16 km",
                "after": "12 km",
                "note": None,
            }
        ]
        adj_id = self._make_adjustment_with_diff(athlete_id, plan_id, affected)

        r = self.client.post(
            f"/plan-adjustments/{adj_id}/apply", json={"selected_workout_ids": None}
        )
        self.assertEqual(422, r.status_code)


class BlockA1CoachTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)
        os.environ["OPENAI_API_KEY"] = ""

    def test_coach_message_persists_user_and_stub_coach_reply(self) -> None:
        athlete_id = _create_athlete(self.client)
        r = self.client.post(
            "/coach/message",
            json={"athlete_id": athlete_id, "message": "我今天腿很酸"},
        )
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertEqual("user", body["user_message"]["role"])
        self.assertEqual("我今天腿很酸", body["user_message"]["text"])
        self.assertEqual("coach", body["coach_message"]["role"])
        self.assertIn("AI 教练", body["coach_message"]["text"])

        with SessionLocal() as db:
            rows = db.query(CoachMessage).all()
            self.assertEqual(2, len(rows))

    def test_coach_conversations_returns_recent_first_with_limit(self) -> None:
        athlete_id = _create_athlete(self.client)
        for msg in ["第一", "第二", "第三"]:
            r = self.client.post(
                "/coach/message",
                json={"athlete_id": athlete_id, "message": msg},
            )
            self.assertEqual(200, r.status_code, r.text)

        r = self.client.get(f"/coach/conversations/{athlete_id}", params={"limit": 4})
        self.assertEqual(200, r.status_code, r.text)
        rows = r.json()
        # Should have 6 messages (3 user + 3 coach), capped to 4.
        self.assertEqual(4, len(rows))
        # Ordered desc by created_at.
        timestamps = [r["created_at"] for r in rows]
        self.assertEqual(timestamps, sorted(timestamps, reverse=True))


class BlockA1HistoryEnrichmentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_history_includes_match_status_and_delta_summary(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        confirm = self.client.post(f"/plans/{plan_id}/confirm")
        self.assertEqual(200, confirm.status_code, confirm.text)

        # Match an activity to a workout today so we get an enriched row.
        wid = _force_workout_today(plan_id)
        with SessionLocal() as db:
            athlete = db.get(AthleteProfile, athlete_id)
            today_dt = datetime.combine(date.today(), datetime.min.time()).replace(hour=7)
            from app.ingestion.service import import_provider_history
            import_provider_history(
                db=db,
                athlete=athlete,
                provider="manual",
                activities=[
                    {
                        "provider_activity_id": "delta-test-1",
                        "sport": "running",
                        "discipline": "run",
                        "started_at": today_dt,
                        "duration_sec": 3000,
                        "distance_m": 9000.0,
                        "avg_pace_sec_per_km": 333.0,
                    }
                ],
            )

        r = self.client.get(f"/athletes/{athlete_id}/history")
        self.assertEqual(200, r.status_code, r.text)
        rows = r.json()
        self.assertGreater(len(rows), 0)

        matched = [r for r in rows if r["matched_workout_id"] is not None]
        self.assertGreaterEqual(len(matched), 1)
        for m in matched:
            self.assertIn(m["match_status"], ("completed", "partial", "miss"))
            self.assertIsNotNone(m["matched_workout_title"])

        unmatched = [r for r in rows if r["matched_workout_id"] is None]
        # Most COROS fake activities won't have a matched workout (different dates)
        # so we should generally have at least one unmatched.
        if unmatched:
            self.assertEqual("unmatched", unmatched[0]["match_status"])
            self.assertIsNone(unmatched[0]["delta_summary"])


class BlockA1TodayEnrichmentTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_training_methods(db)

    def test_today_recovery_recommendation_when_many_missed(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        _force_workout_today(plan_id)

        # Mark 4 of the past-7-day workouts as MISSED.
        with SessionLocal() as db:
            today = date.today()
            workouts = db.execute(
                StructuredWorkout.__table__.select().where(StructuredWorkout.plan_id == plan_id)
            ).fetchall()
            count = 0
            for row in workouts:
                if count >= 4:
                    break
                w = db.get(StructuredWorkout, row.id)
                if w.scheduled_date >= today:
                    continue
                w.scheduled_date = today - timedelta(days=count + 1)
                w.status = WorkoutStatus.MISSED
                count += 1
            # Force-create extra missed entries if not enough past workouts.
            while count < 4:
                from app.models import StructuredWorkout as SW
                db.add(SW(
                    plan_id=plan_id,
                    scheduled_date=today - timedelta(days=count + 1),
                    week_index=1,
                    day_index=count + 1,
                    discipline="run",
                    workout_type="easy",
                    title="Filler missed",
                    purpose="filler",
                    duration_min=30,
                    distance_m=5000.0,
                    target_intensity_type="pace",
                    status=WorkoutStatus.MISSED,
                ))
                count += 1
            db.commit()

        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertIsNotNone(body["recovery_recommendation"])
        self.assertEqual("缺训不补", body["recovery_recommendation"]["ethos_quote"])

    def test_today_yesterday_workout_and_activity_surfaced(self) -> None:
        athlete_id = _create_athlete(self.client)
        _bootstrap_history(self.client, athlete_id)
        plan = _generate_marathon_plan(self.client, athlete_id)
        plan_id = plan["id"]
        confirm = self.client.post(f"/plans/{plan_id}/confirm")
        self.assertEqual(200, confirm.status_code, confirm.text)
        # Force one workout to today (so the route returns 200) and another to yesterday.
        with SessionLocal() as db:
            workouts = db.execute(
                StructuredWorkout.__table__.select()
                .where(StructuredWorkout.plan_id == plan_id)
                .order_by(StructuredWorkout.id.asc())
                .limit(2)
            ).fetchall()
            self.assertEqual(2, len(workouts))
            w0 = db.get(StructuredWorkout, workouts[0].id)
            w0.scheduled_date = date.today()
            w1 = db.get(StructuredWorkout, workouts[1].id)
            w1.scheduled_date = date.today() - timedelta(days=1)
            yesterday_wid = w1.id
            db.commit()

        # Insert an activity that matches yesterday's workout via ingestion.
        with SessionLocal() as db:
            athlete = db.get(AthleteProfile, athlete_id)
            yesterday_dt = datetime.combine(
                date.today() - timedelta(days=1), datetime.min.time()
            ).replace(hour=7)
            from app.ingestion.service import import_provider_history
            import_provider_history(
                db=db,
                athlete=athlete,
                provider="manual",
                activities=[
                    {
                        "provider_activity_id": "yest-act-1",
                        "sport": "running",
                        "discipline": "run",
                        "started_at": yesterday_dt,
                        "duration_sec": 2400,
                        "distance_m": 8000.0,
                        "avg_pace_sec_per_km": 300.0,
                    }
                ],
            )

        r = self.client.get(f"/athletes/{athlete_id}/today")
        self.assertEqual(200, r.status_code, r.text)
        body = r.json()
        self.assertIsNotNone(body["yesterday_workout"])
        self.assertEqual(yesterday_wid, body["yesterday_workout"]["id"])
        self.assertIsNotNone(body["yesterday_activity"])
        # delta_summary may be None or string depending on diff size; just assert key present.
        self.assertIn("delta_summary", body["yesterday_activity"])


if __name__ == "__main__":
    unittest.main()
