from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AdjustmentStatus,
    AthleteActivity,
    PlanAdjustment,
    StructuredWorkout,
    TrainingPlan,
    WorkoutStatus,
)


def evaluate_plan_adjustment(db: Session, plan: TrainingPlan) -> PlanAdjustment:
    today = date.today()
    since = datetime.now(UTC) - timedelta(days=7)
    recent_activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == plan.athlete_id)
        .where(AthleteActivity.started_at >= since)
    ).scalars().all()
    past_workouts = db.execute(
        select(StructuredWorkout)
        .where(StructuredWorkout.plan_id == plan.id)
        .where(StructuredWorkout.scheduled_date < today)
        .where(StructuredWorkout.status.in_([WorkoutStatus.CONFIRMED, WorkoutStatus.SYNCED]))
    ).scalars().all()

    pain_feedback = [
        activity.feedback_text
        for activity in recent_activities
        if activity.feedback_text and ("pain" in activity.feedback_text.lower() or "疼" in activity.feedback_text)
    ]
    high_load = sum(activity.training_load or 0 for activity in recent_activities) > 650
    missed_count = len(past_workouts)

    if pain_feedback:
        reason = "Recent COROS feedback mentions pain."
        recommendation = "Reduce the next 7 days by 20%, replace quality work with easy running, and keep the long run conversational."
    elif high_load:
        reason = "Recent training load is high relative to the MVP safety threshold."
        recommendation = "Keep the next key session but reduce easy-run duration by 10-15% and monitor fatigue."
    elif missed_count >= 2:
        reason = "There are multiple confirmed workouts without matched completion records."
        recommendation = "Rebuild the next 7-14 days around one quality session and one long run rather than stacking missed work."
    else:
        reason = "Weekly review found no severe risk signal."
        recommendation = "Keep the current plan and continue importing COROS history after each completed workout."

    adjustment = PlanAdjustment(
        athlete_id=plan.athlete_id,
        plan_id=plan.id,
        status=AdjustmentStatus.PROPOSED,
        reason=reason,
        recommendation=recommendation,
        effective_start_date=today,
        effective_end_date=today + timedelta(days=14),
    )
    db.add(adjustment)
    db.commit()
    db.refresh(adjustment)
    return adjustment


def confirm_adjustment(db: Session, adjustment: PlanAdjustment) -> PlanAdjustment:
    adjustment.status = AdjustmentStatus.CONFIRMED
    adjustment.confirmed_at = datetime.now(UTC)
    db.commit()
    db.refresh(adjustment)
    return adjustment
