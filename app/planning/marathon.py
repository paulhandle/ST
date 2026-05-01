from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.assessment.running import assess_running_ability
from app.models import (
    AthleteProfile,
    PlanStatus,
    RaceGoal,
    RaceGoalStatus,
    SportType,
    StructuredWorkout,
    TrainingAvailability,
    TrainingGoal,
    TrainingMode,
    TrainingPlan,
    TrainingSession,
    WorkoutStep,
)

MARATHON_KM = 42.195


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


def create_marathon_goal(db: Session, athlete: AthleteProfile, request) -> RaceGoal:
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
        sport=SportType.MARATHON,
        distance="marathon",
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


def generate_marathon_plan(db: Session, athlete: AthleteProfile, request, race_goal: RaceGoal | None = None):
    availability = save_availability(db, athlete, request.availability)
    if race_goal is None:
        race_goal = create_marathon_goal(db, athlete, request)
        db.refresh(athlete)

    if race_goal.status == RaceGoalStatus.REJECTED:
        return None, race_goal.feasibility_summary or "Goal rejected as unsafe or unrealistic."

    assessment = assess_running_ability(
        db=db,
        athlete_id=athlete.id,
        target_time_sec=race_goal.target_time_sec,
        plan_weeks=race_goal.plan_weeks,
        requested_training_days=availability.weekly_training_days,
    )
    start_date = race_goal.training_start_date or request.training_start_date or date.today()
    race_date = race_goal.race_date or request.race_date or start_date + timedelta(weeks=race_goal.plan_weeks)
    target_time_sec = race_goal.target_time_sec

    plan = TrainingPlan(
        athlete_id=athlete.id,
        race_goal_id=race_goal.id,
        sport=SportType.MARATHON,
        goal=TrainingGoal.RACE_SPECIFIC if target_time_sec else TrainingGoal.FINISH,
        mode=TrainingMode.BASE_BUILD_PEAK,
        weeks=race_goal.plan_weeks,
        status=PlanStatus.DRAFT,
        title=_plan_title(target_time_sec),
        start_date=start_date,
        race_date=race_date,
        target_time_sec=target_time_sec,
    )
    db.add(plan)
    db.flush()

    selected_weekdays = _selected_weekdays(availability)
    target_pace = _target_marathon_pace(target_time_sec, assessment)
    safe_low, safe_high = assessment["safe_weekly_distance_range_km"]
    peak_km = max(safe_high, 55.0 if target_time_sec and target_time_sec <= 4 * 3600 else 42.0)
    start_km = max(24.0, safe_low)

    for week_index in range(1, race_goal.plan_weeks + 1):
        phase = _phase(week_index, race_goal.plan_weeks)
        week_target_km = _week_target_km(week_index, race_goal.plan_weeks, start_km, peak_km, phase)
        week_sessions = _week_workouts(
            selected_weekdays=selected_weekdays,
            preferred_long_run_weekday=availability.preferred_long_run_weekday,
            week_target_km=week_target_km,
            phase=phase,
            target_pace=target_pace,
            week_index=week_index,
            start_date=start_date,
        )
        for day_index, workout_data in enumerate(week_sessions, start=1):
            workout = StructuredWorkout(plan_id=plan.id, day_index=day_index, **workout_data)
            db.add(workout)
            db.flush()
            for step_index, step in enumerate(_steps_for_workout(workout_data, target_pace), start=1):
                db.add(WorkoutStep(workout_id=workout.id, step_index=step_index, **step))
            db.add(
                TrainingSession(
                    plan_id=plan.id,
                    week_index=workout.week_index,
                    day_index=day_index,
                    discipline=workout.discipline,
                    session_type=workout.workout_type,
                    duration_min=workout.duration_min,
                    intensity=_intensity_for(workout.workout_type),
                    notes=workout.purpose,
                )
            )

    db.commit()
    db.refresh(plan)
    return plan, None


def _race_goal_status(goal_status: str) -> RaceGoalStatus:
    if goal_status == "reject":
        return RaceGoalStatus.REJECTED
    if goal_status in {"accept_with_warning", "recommend_adjustment"}:
        return RaceGoalStatus.WARNING
    return RaceGoalStatus.ACCEPTED


def _plan_title(target_time_sec: int | None) -> str:
    if target_time_sec is None:
        return "ST Full Marathon Finish Plan"
    hours = target_time_sec // 3600
    minutes = (target_time_sec % 3600) // 60
    return f"ST Full Marathon {hours}:{minutes:02d} Plan"


def _selected_weekdays(availability: TrainingAvailability) -> list[int]:
    unavailable = {
        int(value)
        for value in (availability.unavailable_weekdays or "").split(",")
        if value.strip().isdigit()
    }
    candidates = [day for day in [1, 2, 3, 4, 5, 6, 0] if day not in unavailable]
    selected = candidates[: max(1, availability.weekly_training_days)]
    if availability.preferred_long_run_weekday not in selected and availability.preferred_long_run_weekday not in unavailable:
        selected[-1] = availability.preferred_long_run_weekday
    return sorted(set(selected))


def _target_marathon_pace(target_time_sec: int | None, assessment: dict) -> float:
    if target_time_sec is not None:
        return target_time_sec / MARATHON_KM
    estimate = mean(assessment["estimated_marathon_time_range_sec"])
    return estimate / MARATHON_KM


def _phase(week_index: int, weeks: int) -> str:
    progress = week_index / weeks
    if progress <= 0.5:
        return "base"
    if progress <= 0.82:
        return "build"
    if progress <= 0.94:
        return "peak"
    return "taper"


def _week_target_km(week_index: int, weeks: int, start_km: float, peak_km: float, phase: str) -> float:
    if phase == "taper":
        taper_weeks = max(1, weeks - week_index + 1)
        return max(start_km * 0.75, peak_km * (0.55 if taper_weeks == 1 else 0.7))
    progress = min(1.0, week_index / max(1, int(weeks * 0.82)))
    raw = start_km + (peak_km - start_km) * progress
    if week_index % 4 == 0:
        raw *= 0.82
    return round(raw, 1)


def _week_workouts(
    selected_weekdays: list[int],
    preferred_long_run_weekday: int,
    week_target_km: float,
    phase: str,
    target_pace: float,
    week_index: int,
    start_date: date,
) -> list[dict]:
    long_day = preferred_long_run_weekday if preferred_long_run_weekday in selected_weekdays else selected_weekdays[-1]
    quality_day = next((day for day in selected_weekdays if day != long_day), selected_weekdays[0])
    easy_days = [day for day in selected_weekdays if day not in {long_day, quality_day}]
    long_km = min(32.0, max(16.0, week_target_km * (0.34 if phase != "taper" else 0.28)))
    quality_km = max(8.0, week_target_km * 0.22)
    remaining_km = max(0.0, week_target_km - long_km - quality_km)
    easy_km = remaining_km / max(1, len(easy_days))

    workouts = []
    for weekday in selected_weekdays:
        scheduled_date = _date_for_weekday(start_date, week_index, weekday)
        if weekday == long_day:
            workout_type = "long_run"
            distance_km = long_km
            pace_offset = 55
            purpose = f"{phase} phase long run to build marathon durability."
        elif weekday == quality_day:
            workout_type = "marathon_pace" if week_index % 2 else "threshold"
            distance_km = quality_km
            pace_offset = 0 if workout_type == "marathon_pace" else -18
            purpose = f"{phase} phase quality session for goal pace control."
        else:
            workout_type = "easy_run"
            distance_km = max(5.0, easy_km)
            pace_offset = 70
            purpose = f"{phase} phase easy aerobic support."

        duration_min = max(25, int(distance_km * (target_pace + pace_offset) / 60))
        workouts.append(
            {
                "scheduled_date": scheduled_date,
                "week_index": week_index,
                "discipline": "run",
                "workout_type": workout_type,
                "title": f"ST W{week_index:02d} {_title_for(workout_type)}",
                "purpose": purpose,
                "duration_min": duration_min,
                "distance_m": round(distance_km * 1000, 1),
                "target_intensity_type": "pace",
                "target_pace_min_sec_per_km": round(target_pace + pace_offset - 8, 1),
                "target_pace_max_sec_per_km": round(target_pace + pace_offset + 12, 1),
                "rpe_min": 3 if workout_type != "threshold" else 6,
                "rpe_max": 5 if workout_type != "threshold" else 8,
                "adaptation_notes": "Generated from current COROS history and marathon goal.",
            }
        )
    return sorted(workouts, key=lambda item: item["scheduled_date"])


def _date_for_weekday(start_date: date, week_index: int, weekday: int) -> date:
    week_start = start_date + timedelta(weeks=week_index - 1)
    return week_start + timedelta(days=(weekday - week_start.weekday()) % 7)


def _title_for(workout_type: str) -> str:
    return {
        "long_run": "Long Run",
        "marathon_pace": "Marathon Pace",
        "threshold": "Threshold",
        "easy_run": "Easy Run",
    }.get(workout_type, workout_type.replace("_", " ").title())


def _steps_for_workout(workout_data: dict, target_pace: float) -> list[dict]:
    workout_type = workout_data["workout_type"]
    duration = workout_data["duration_min"] * 60
    if workout_type == "threshold":
        return [
            _step("warmup", 900, target_pace + 70, target_pace + 95, "Warm up easily."),
            _step("work", max(900, duration - 1800), target_pace - 25, target_pace - 5, "Controlled threshold block."),
            _step("cooldown", 900, target_pace + 75, target_pace + 110, "Cool down easily."),
        ]
    if workout_type == "marathon_pace":
        return [
            _step("warmup", 900, target_pace + 65, target_pace + 90, "Warm up easily."),
            _step("work", max(1200, duration - 1800), target_pace - 5, target_pace + 10, "Hold marathon effort."),
            _step("cooldown", 900, target_pace + 70, target_pace + 100, "Cool down easily."),
        ]
    return [
        _step("warmup", 600, target_pace + 65, target_pace + 100, "Start relaxed."),
        _step("work", max(900, duration - 900), workout_data["target_pace_min_sec_per_km"], workout_data["target_pace_max_sec_per_km"], "Stay smooth."),
        _step("cooldown", 300, target_pace + 80, target_pace + 120, "Finish relaxed."),
    ]


def _step(step_type: str, duration_sec: int, target_min: float, target_max: float, notes: str) -> dict:
    return {
        "step_type": step_type,
        "duration_sec": duration_sec,
        "target_type": "pace_sec_per_km",
        "target_min": round(target_min, 1),
        "target_max": round(target_max, 1),
        "notes": notes,
    }


def _intensity_for(workout_type: str) -> str:
    if workout_type == "threshold":
        return "high"
    if workout_type == "marathon_pace":
        return "moderate"
    return "low"
