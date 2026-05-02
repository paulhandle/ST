"""Activity ↔ Workout matching helpers.

A planned ``StructuredWorkout`` is matched against an imported ``AthleteActivity``
when they share athlete, scheduled date and discipline, and the plan is active.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AthleteActivity,
    PlanStatus,
    StructuredWorkout,
    TrainingPlan,
)


def match_activity_to_workout(db: Session, activity_id: int) -> StructuredWorkout | None:
    """Find the planned workout that lines up with the given activity, if any.

    Heuristic match: same athlete, same date (in the activity's own clock), same
    discipline, and the plan must currently be ACTIVE.
    """
    activity = db.get(AthleteActivity, activity_id)
    if activity is None:
        return None
    activity_date = activity.started_at.date()
    stmt = (
        select(StructuredWorkout)
        .join(TrainingPlan, StructuredWorkout.plan_id == TrainingPlan.id)
        .where(
            TrainingPlan.athlete_id == activity.athlete_id,
            TrainingPlan.status == PlanStatus.ACTIVE,
            StructuredWorkout.scheduled_date == activity_date,
            StructuredWorkout.discipline == activity.discipline,
        )
        .order_by(StructuredWorkout.id.asc())
    )
    return db.execute(stmt).scalars().first()


def match_workout_to_activity(db: Session, workout: StructuredWorkout) -> AthleteActivity | None:
    """Reverse lookup: find the activity that has been matched to this workout."""
    stmt = (
        select(AthleteActivity)
        .where(AthleteActivity.matched_workout_id == workout.id)
        .order_by(AthleteActivity.started_at.desc())
    )
    return db.execute(stmt).scalars().first()


def compute_match_diff(workout: StructuredWorkout, activity: AthleteActivity) -> dict:
    """Return percentage / absolute differences between planned and actual."""
    distance_pct: float | None = None
    if workout.distance_m and workout.distance_m > 0 and activity.distance_m is not None:
        distance_pct = round(
            (activity.distance_m - workout.distance_m) / workout.distance_m * 100.0, 1
        )

    duration_pct: float | None = None
    planned_duration_sec = (workout.duration_min or 0) * 60
    if planned_duration_sec > 0 and activity.duration_sec:
        duration_pct = round(
            (activity.duration_sec - planned_duration_sec) / planned_duration_sec * 100.0, 1
        )

    avg_pace_diff_sec_per_km: float | None = None
    if (
        activity.avg_pace_sec_per_km is not None
        and workout.target_pace_min_sec_per_km is not None
        and workout.target_pace_max_sec_per_km is not None
    ):
        planned_mid = (
            workout.target_pace_min_sec_per_km + workout.target_pace_max_sec_per_km
        ) / 2.0
        avg_pace_diff_sec_per_km = round(
            float(activity.avg_pace_sec_per_km) - planned_mid, 1
        )

    return {
        "distance_pct": distance_pct,
        "duration_pct": duration_pct,
        "avg_pace_diff_sec_per_km": avg_pace_diff_sec_per_km,
    }
