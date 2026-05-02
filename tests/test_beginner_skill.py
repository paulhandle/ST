"""
running_beginner skill tests — TDD.
Tests should FAIL until the skill is implemented.
"""
import os
os.environ.setdefault("ST_DATABASE_URL", "sqlite:///st_test.db")

import unittest
from datetime import date

from app.skills import load_skill
from app.core.context import (
    SkillContext, AthleteSnapshot, HistoryView, GoalSpec, AvailabilityView,
)
from app.models import SportType


def _make_ctx(weekly_km=0.0, long_runs=None, weekly_days=3, goal="finish"):
    athlete = AthleteSnapshot(
        id=1, name="新手跑者", age=30,
        sex=None, height_cm=None, weight_kg=None,
        years_running=0, injury_history="",
        avg_sleep_hours=None, work_stress=None,
        resting_hr=None, last_race_distance=None,
        last_race_time=None, last_race_date=None,
        notes="", profile_block="",
    )
    history = HistoryView(
        recent_activities=[],
        weekly_km_last_8w=[weekly_km] * 8,
        recent_long_runs=long_runs or [],
        latest_metrics={},
    )
    goal_spec = GoalSpec(
        sport=SportType.MARATHON,
        distance_label="marathon",
        distance_m=42195,
        target_time_sec=None,
        race_date=date(2026, 11, 1),
        plan_weeks=26,
    )
    availability = AvailabilityView(
        weekly_training_days=weekly_days,
        selected_weekdays=[1, 3, 6],  # Mon, Wed, Sat
        preferred_long_run_weekday=6,
        unavailable_weekdays=[],
        max_weekday_duration_min=90,
        max_weekend_duration_min=120,
        strength_training_enabled=False,
    )
    return SkillContext(
        athlete=athlete,
        history=history,
        goal=goal_spec,
        availability=availability,
        assessment=None,
        today=date(2026, 5, 2),
        start_date=date(2026, 5, 6),
        llm_enabled=False,
    )


class BeginnerSkillLoadTestCase(unittest.TestCase):
    def test_load_skill_returns_beginner_skill(self):
        skill = load_skill("running_beginner")
        self.assertIsNotNone(skill)

    def test_manifest_slug_is_running_beginner(self):
        skill = load_skill("running_beginner")
        self.assertEqual(skill.manifest.slug, "running_beginner")

    def test_manifest_has_required_fields(self):
        skill = load_skill("running_beginner")
        m = skill.manifest
        self.assertTrue(m.name)
        self.assertTrue(m.version)
        self.assertIsNotNone(m.sport)  # sport is SportType enum


class BeginnerSkillApplicableTestCase(unittest.TestCase):
    def test_applicable_for_zero_history(self):
        skill = load_skill("running_beginner")
        ctx = _make_ctx(weekly_km=0.0)
        ok, _ = skill.applicable(ctx)
        self.assertTrue(ok)

    def test_applicable_for_low_mileage(self):
        skill = load_skill("running_beginner")
        ctx = _make_ctx(weekly_km=10.0)
        ok, _ = skill.applicable(ctx)
        self.assertTrue(ok)

    def test_not_applicable_for_high_mileage(self):
        """Users averaging >40 km/week should use a more advanced skill."""
        skill = load_skill("running_beginner")
        ctx = _make_ctx(weekly_km=45.0)
        ok, reason = skill.applicable(ctx)
        self.assertFalse(ok)
        self.assertTrue(len(reason) > 0)


class BeginnerSkillGenerateTestCase(unittest.TestCase):
    def setUp(self):
        self.skill = load_skill("running_beginner")
        self.ctx = _make_ctx(weekly_km=0.0, weekly_days=3)

    def test_generate_returns_plan_draft(self):
        from app.core.context import PlanDraft
        draft = self.skill.generate_plan(self.ctx)
        self.assertIsInstance(draft, PlanDraft)

    def test_plan_has_at_least_4_weeks(self):
        draft = self.skill.generate_plan(self.ctx)
        self.assertGreaterEqual(len(draft.weeks), 4)

    def test_plan_has_no_more_than_3_runs_per_week(self):
        draft = self.skill.generate_plan(self.ctx)
        for week in draft.weeks:
            run_days = [w for w in week if w.discipline == "run"]
            self.assertLessEqual(len(run_days), 3)

    def test_workouts_use_rpe_not_pace(self):
        """Beginner plan should use RPE intensity, not pace targets."""
        draft = self.skill.generate_plan(self.ctx)
        for week in draft.weeks:
            for w in week:
                self.assertEqual(w.target_intensity_type, "rpe",
                    f"Expected rpe intensity, got {w.target_intensity_type} for {w.title}")

    def test_first_week_is_short(self):
        """Week 1 should be gentle — total distance < 15 km."""
        draft = self.skill.generate_plan(self.ctx)
        week1_km = sum(
            (w.distance_m or 0) / 1000
            for w in draft.weeks[0]
        )
        self.assertLess(week1_km, 15.0, f"Week 1 total {week1_km:.1f} km is too high for beginners")

    def test_plan_title_is_set(self):
        draft = self.skill.generate_plan(self.ctx)
        self.assertTrue(draft.title)


if __name__ == "__main__":
    unittest.main()
