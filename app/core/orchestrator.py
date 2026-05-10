"""Plan generation orchestrator.

Owns the boundary between the platform (DB, services, schemas) and Skills
(pure methodology functions). Skills do not see the DB; the orchestrator
assembles a SkillContext, calls the Skill, and persists the PlanDraft.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.kb.running_assessment import assess_running_ability
from app.core.context import (
    ActivitySummary,
    Assessment,
    AthleteSnapshot,
    AvailabilityView,
    GoalSpec,
    HistoryView,
    PlanDraft,
    SkillContext,
    WorkoutDraft,
)
from app.kb.running import format_pace
from app.models import (
    AthleteActivity,
    AthleteMetricSnapshot,
    AthleteProfile,
    PlanStatus,
    RaceGoal,
    RaceGoalStatus,
    SportType,
    StructuredWorkout,
    TrainingAvailability,
    TrainingGoal,
    TrainingPlan,
    TrainingSession,
    WorkoutStep,
)
from app.skills import load_skill

log = logging.getLogger(__name__)


def save_availability(db: Session, athlete: AthleteProfile, data) -> TrainingAvailability:
    unavailable = ",".join(str(day) for day in sorted(set(data.unavailable_weekdays)))
    existing = db.execute(
        select(TrainingAvailability).where(TrainingAvailability.athlete_id == athlete.id)
    ).scalar_one_or_none()
    if existing is None:
        existing = TrainingAvailability(athlete_id=athlete.id)
        db.add(existing)
    existing.weekly_training_days = data.weekly_training_days
    existing.preferred_long_run_weekday = data.preferred_long_run_weekday
    existing.unavailable_weekdays = unavailable or None
    existing.max_weekday_duration_min = data.max_weekday_duration_min
    existing.max_weekend_duration_min = data.max_weekend_duration_min
    existing.strength_training_enabled = data.strength_training_enabled
    existing.notes = data.notes
    db.flush()
    return existing


def create_race_goal(db: Session, athlete: AthleteProfile, request, sport: SportType) -> RaceGoal:
    availability = save_availability(db, athlete, request.availability)
    assessment = assess_running_ability(
        db=db,
        athlete_id=athlete.id,
        target_time_sec=request.target_time_sec,
        plan_weeks=request.plan_weeks,
        requested_training_days=availability.weekly_training_days,
    )
    status = _race_goal_status(assessment["goal_status"])
    target_type = "target_time" if request.target_time_sec is not None else "finish"
    goal = RaceGoal(
        athlete_id=athlete.id,
        sport=sport,
        distance=sport.value,
        target_type=target_type,
        target_time_sec=request.target_time_sec,
        race_date=request.race_date,
        training_start_date=request.training_start_date,
        plan_weeks=request.plan_weeks,
        status=status,
        feasibility_summary=assessment["summary"],
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def generate_plan_via_skill(
    db: Session,
    athlete: AthleteProfile,
    request,
    skill_slug: str,
    race_goal: RaceGoal | None = None,
) -> tuple[TrainingPlan | None, str | None]:
    """Generate a plan by dispatching to the named Skill."""
    skill = load_skill(skill_slug)
    sport = skill.manifest.sport

    availability = save_availability(db, athlete, request.availability)
    if race_goal is None:
        race_goal = create_race_goal(db, athlete, request, sport)
        db.refresh(athlete)

    if race_goal.status == RaceGoalStatus.REJECTED:
        return None, race_goal.feasibility_summary or "Goal rejected as unsafe or unrealistic."

    start_date = race_goal.training_start_date or request.training_start_date or date.today()
    race_date = race_goal.race_date or request.race_date or start_date + timedelta(weeks=race_goal.plan_weeks)

    ctx = _build_context(
        db=db,
        athlete=athlete,
        availability=availability,
        race_goal=race_goal,
        start_date=start_date,
        profile_block=getattr(request, "profile_block", "") or "",
        llm_enabled=_llm_enabled() and bool(getattr(request, "use_llm", False)),
    )

    ok, why = skill.applicable(ctx)
    if not ok:
        return None, f"Skill {skill_slug} not applicable: {why}"

    draft = skill.generate_plan(ctx)
    plan = _persist_plan(
        db=db,
        athlete=athlete,
        race_goal=race_goal,
        draft=draft,
        start_date=start_date,
        race_date=race_date,
        sport=sport,
    )
    return plan, None


# ── Context assembly ──────────────────────────────────────────────────────────


def _build_context(
    *,
    db: Session,
    athlete: AthleteProfile,
    availability: TrainingAvailability,
    race_goal: RaceGoal,
    start_date: date,
    profile_block: str,
    llm_enabled: bool,
) -> SkillContext:
    selected_weekdays = _selected_weekdays(availability)
    history = _build_history(db, athlete_id=athlete.id)
    assessment = _build_assessment(
        db=db,
        athlete_id=athlete.id,
        target_time_sec=race_goal.target_time_sec,
        plan_weeks=race_goal.plan_weeks,
        weekly_training_days=availability.weekly_training_days,
    )
    snapshot = AthleteSnapshot(
        id=athlete.id,
        name=athlete.name or "Athlete",
        age=getattr(athlete, "age", None),
        sex=getattr(athlete, "sex", None),
        height_cm=getattr(athlete, "height_cm", None),
        weight_kg=getattr(athlete, "weight_kg", None),
        years_running=getattr(athlete, "years_running", None),
        injury_history=getattr(athlete, "injury_history", "") or "",
        avg_sleep_hours=getattr(athlete, "avg_sleep_hours", None),
        work_stress=getattr(athlete, "work_stress", None),
        resting_hr=getattr(athlete, "resting_hr", None),
        last_race_distance=getattr(athlete, "last_race_distance", None),
        last_race_time=getattr(athlete, "last_race_time", None),
        last_race_date=getattr(athlete, "last_race_date", None),
        notes=getattr(athlete, "notes", "") or "",
        profile_block=profile_block,
    )
    goal_spec = GoalSpec(
        sport=race_goal.sport,
        distance_label=race_goal.distance or race_goal.sport.value,
        distance_m=None,
        target_time_sec=race_goal.target_time_sec,
        race_date=race_goal.race_date,
        plan_weeks=race_goal.plan_weeks,
    )
    avail_view = AvailabilityView(
        weekly_training_days=availability.weekly_training_days,
        selected_weekdays=selected_weekdays,
        preferred_long_run_weekday=availability.preferred_long_run_weekday,
        unavailable_weekdays=_parse_unavailable(availability.unavailable_weekdays),
        max_weekday_duration_min=availability.max_weekday_duration_min,
        max_weekend_duration_min=availability.max_weekend_duration_min,
        strength_training_enabled=availability.strength_training_enabled,
    )
    return SkillContext(
        athlete=snapshot,
        goal=goal_spec,
        availability=avail_view,
        history=history,
        assessment=assessment,
        today=date.today(),
        start_date=start_date,
        llm_enabled=llm_enabled,
    )


def _build_assessment(
    *,
    db: Session,
    athlete_id: int,
    target_time_sec: int | None,
    plan_weeks: int,
    weekly_training_days: int,
) -> Assessment:
    raw = assess_running_ability(
        db=db,
        athlete_id=athlete_id,
        target_time_sec=target_time_sec,
        plan_weeks=plan_weeks,
        requested_training_days=weekly_training_days,
    )
    safe_low, safe_high = raw["safe_weekly_distance_range_km"]
    est_low, est_high = raw["estimated_marathon_time_range_sec"]
    return Assessment(
        overall_score=raw["overall_score"],
        readiness_level=raw["readiness_level"],
        confidence=raw["confidence"],
        safe_weekly_distance_range_km=(float(safe_low), float(safe_high)),
        long_run_capacity_km=float(raw["long_run_capacity_km"]),
        estimated_marathon_time_range_sec=(int(est_low), int(est_high)),
        goal_status=raw["goal_status"],
        summary=raw.get("summary", ""),
        warnings=list(raw.get("warnings", [])),
        limiting_factors=list(raw.get("limiting_factors", [])),
        raw=raw,
    )


def _build_history(db: Session, *, athlete_id: int) -> HistoryView:
    now = datetime.now(UTC).replace(tzinfo=None)
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.discipline == "run")
        .where(AthleteActivity.started_at >= now - timedelta(days=56))
        .order_by(AthleteActivity.started_at.asc())
    ).scalars().all()

    by_week: dict[tuple, float] = defaultdict(float)
    for activity in activities:
        by_week[activity.started_at.isocalendar()[:2]] += (activity.distance_m or 0) / 1000
    weekly_km = [round(value, 1) for _, value in sorted(by_week.items(), key=lambda x: x[0])[-8:]]

    long_runs = [a for a in reversed(activities) if (a.distance_m or 0) >= 15_000][:5]
    long_run_lines: list[str] = []
    for a in reversed(long_runs):
        if not a.avg_pace_sec_per_km:
            continue
        line = (
            f"{a.started_at.strftime('%Y-%m-%d')}: {a.distance_m / 1000:.1f} km @ "
            f"{format_pace(a.avg_pace_sec_per_km)}/km"
        )
        if a.avg_hr:
            line += f" avg HR {int(a.avg_hr)}"
        long_run_lines.append(line)

    metrics = {}
    for name in ("lthr", "ltsp"):
        row = db.execute(
            select(AthleteMetricSnapshot)
            .where(AthleteMetricSnapshot.athlete_id == athlete_id)
            .where(AthleteMetricSnapshot.metric_type == name)
            .order_by(AthleteMetricSnapshot.measured_at.desc())
        ).scalars().first()
        if row is not None:
            metrics[name] = float(row.value)

    recent = [
        ActivitySummary(
            started_at=a.started_at,
            duration_sec=a.duration_sec or 0,
            distance_m=float(a.distance_m or 0),
            discipline=a.discipline,
            avg_pace_sec_per_km=a.avg_pace_sec_per_km,
            avg_hr=a.avg_hr,
            training_load=a.training_load,
            feedback_text=a.feedback_text,
        )
        for a in activities[-20:]
    ]
    return HistoryView(
        recent_activities=recent,
        weekly_km_last_8w=weekly_km,
        recent_long_runs=long_run_lines,
        latest_metrics=metrics,
    )


# ── Persistence ───────────────────────────────────────────────────────────────


def _persist_plan(
    *,
    db: Session,
    athlete: AthleteProfile,
    race_goal: RaceGoal,
    draft: PlanDraft,
    start_date: date,
    race_date: date,
    sport: SportType,
) -> TrainingPlan:
    target_time_sec = race_goal.target_time_sec
    plan = TrainingPlan(
        athlete_id=athlete.id,
        race_goal_id=race_goal.id,
        sport=sport,
        goal=TrainingGoal.RACE_SPECIFIC if target_time_sec else TrainingGoal.FINISH,
        mode=draft.mode,
        weeks=race_goal.plan_weeks,
        status=PlanStatus.DRAFT,
        title=draft.title,
        start_date=start_date,
        race_date=race_date,
        target_time_sec=target_time_sec,
    )
    db.add(plan)
    db.flush()

    for week in draft.weeks:
        week_sorted = sorted(week, key=lambda w: (w.week_index, w.weekday))
        for day_index, workout in enumerate(week_sorted, start=1):
            scheduled_date = _date_for_weekday(start_date, workout.week_index, workout.weekday)
            sw = StructuredWorkout(
                plan_id=plan.id,
                day_index=day_index,
                week_index=workout.week_index,
                scheduled_date=scheduled_date,
                discipline=workout.discipline,
                workout_type=workout.workout_type,
                title=workout.title,
                purpose=workout.purpose,
                duration_min=workout.duration_min,
                distance_m=workout.distance_m,
                target_intensity_type=workout.target_intensity_type,
                target_pace_min_sec_per_km=workout.target_pace_min_sec_per_km,
                target_pace_max_sec_per_km=workout.target_pace_max_sec_per_km,
                target_hr_min=workout.target_hr_min,
                target_hr_max=workout.target_hr_max,
                rpe_min=workout.rpe_min,
                rpe_max=workout.rpe_max,
                adaptation_notes=workout.adaptation_notes,
            )
            db.add(sw)
            db.flush()

            for step_index, step in enumerate(workout.steps, start=1):
                db.add(
                    WorkoutStep(
                        workout_id=sw.id,
                        step_index=step_index,
                        step_type=step.step_type,
                        duration_sec=step.duration_sec,
                        target_type=step.target_type,
                        target_min=step.target_min,
                        target_max=step.target_max,
                        notes=step.notes,
                    )
                )

            db.add(
                TrainingSession(
                    plan_id=plan.id,
                    week_index=sw.week_index,
                    day_index=day_index,
                    discipline=sw.discipline,
                    session_type=sw.workout_type,
                    duration_min=sw.duration_min,
                    intensity=_intensity_for(sw.workout_type),
                    notes=sw.purpose,
                )
            )

    db.commit()
    db.refresh(plan)
    return plan


# ── Helpers ───────────────────────────────────────────────────────────────────


def _race_goal_status(goal_status: str) -> RaceGoalStatus:
    if goal_status == "reject":
        return RaceGoalStatus.REJECTED
    if goal_status in {"accept_with_warning", "recommend_adjustment"}:
        return RaceGoalStatus.WARNING
    return RaceGoalStatus.ACCEPTED


def _selected_weekdays(availability: TrainingAvailability) -> list[int]:
    unavailable = set(_parse_unavailable(availability.unavailable_weekdays))
    candidates = [day for day in [1, 2, 3, 4, 5, 6, 0] if day not in unavailable]
    selected = candidates[: max(1, availability.weekly_training_days)]
    if (
        availability.preferred_long_run_weekday not in selected
        and availability.preferred_long_run_weekday not in unavailable
    ):
        selected[-1] = availability.preferred_long_run_weekday
    return sorted(set(selected))


def _parse_unavailable(raw: str | None) -> list[int]:
    if not raw:
        return []
    return sorted({int(v) for v in raw.split(",") if v.strip().isdigit()})


def _date_for_weekday(start_date: date, week_index: int, weekday: int) -> date:
    week_start = start_date + timedelta(weeks=week_index - 1)
    return week_start + timedelta(days=(weekday - week_start.weekday()) % 7)


def _intensity_for(workout_type: str) -> str:
    if workout_type == "threshold":
        return "high"
    if workout_type == "marathon_pace":
        return "moderate"
    return "low"


def _llm_enabled() -> bool:
    import os
    return bool(os.environ.get("OPENAI_API_KEY"))
