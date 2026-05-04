"""Rule-based marathon plan generator.

Pure function: SkillContext in, list of weeks of WorkoutDraft out.
No DB, no external API, no LLM.
"""
from __future__ import annotations

from datetime import date, timedelta
from statistics import mean

from app.core.context import SkillContext, StepDraft, WorkoutDraft
from app.kb.running import MARATHON_DISTANCE_KM


def generate_weeks(ctx: SkillContext) -> list[list[WorkoutDraft]]:
    target_time_sec = ctx.goal.target_time_sec
    plan_weeks = ctx.goal.plan_weeks
    target_pace = _target_marathon_pace(target_time_sec, ctx.assessment)

    safe_low, safe_high = ctx.assessment.safe_weekly_distance_range_km if ctx.assessment else (24.0, 60.0)
    peak_km = max(safe_high, 55.0 if target_time_sec and target_time_sec <= 4 * 3600 else 42.0)
    start_km = max(24.0, safe_low)

    selected_weekdays = sorted(set(ctx.availability.selected_weekdays))
    preferred_long_run_weekday = ctx.availability.preferred_long_run_weekday

    out: list[list[WorkoutDraft]] = []
    for week_index in range(1, plan_weeks + 1):
        phase = _phase(week_index, plan_weeks)
        week_target_km = _week_target_km(week_index, plan_weeks, start_km, peak_km, phase)
        out.append(
            _week_workouts(
                selected_weekdays=selected_weekdays,
                preferred_long_run_weekday=preferred_long_run_weekday,
                week_target_km=week_target_km,
                phase=phase,
                target_pace=target_pace,
                week_index=week_index,
            )
        )
    return out


def steps_for_workout(workout: WorkoutDraft, target_pace: float) -> list[StepDraft]:
    duration = workout.duration_min * 60
    if workout.workout_type == "threshold":
        return [
            _step("warmup", 900, target_pace + 70, target_pace + 95, "Warm up easily."),
            _step("work", max(900, duration - 1800), target_pace - 25, target_pace - 5, "Controlled threshold block."),
            _step("cooldown", 900, target_pace + 75, target_pace + 110, "Cool down easily."),
        ]
    if workout.workout_type == "marathon_pace":
        return [
            _step("warmup", 900, target_pace + 65, target_pace + 90, "Warm up easily."),
            _step("work", max(1200, duration - 1800), target_pace - 5, target_pace + 10, "Hold marathon effort."),
            _step("cooldown", 900, target_pace + 70, target_pace + 100, "Cool down easily."),
        ]
    return [
        _step("warmup", 600, target_pace + 65, target_pace + 100, "Start relaxed."),
        _step(
            "work",
            max(900, duration - 900),
            workout.target_pace_min_sec_per_km or (target_pace + 50),
            workout.target_pace_max_sec_per_km or (target_pace + 90),
            "Stay smooth.",
        ),
        _step("cooldown", 300, target_pace + 80, target_pace + 120, "Finish relaxed."),
    ]


def plan_title(target_time_sec: int | None) -> str:
    if target_time_sec is None:
        return "PerformanceProtocol Full Marathon Finish Plan"
    hours = target_time_sec // 3600
    minutes = (target_time_sec % 3600) // 60
    return f"PerformanceProtocol Full Marathon {hours}:{minutes:02d} Plan"


def _target_marathon_pace(target_time_sec: int | None, assessment) -> float:
    if target_time_sec is not None:
        return target_time_sec / MARATHON_DISTANCE_KM
    if assessment is None:
        return 360.0
    estimate = mean(assessment.estimated_marathon_time_range_sec)
    return estimate / MARATHON_DISTANCE_KM


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
) -> list[WorkoutDraft]:
    long_day = (
        preferred_long_run_weekday
        if preferred_long_run_weekday in selected_weekdays
        else selected_weekdays[-1]
    )
    quality_day = next((day for day in selected_weekdays if day != long_day), selected_weekdays[0])
    easy_days = [day for day in selected_weekdays if day not in {long_day, quality_day}]

    long_km = min(32.0, max(16.0, week_target_km * (0.34 if phase != "taper" else 0.28)))
    quality_km = max(8.0, week_target_km * 0.22)
    remaining_km = max(0.0, week_target_km - long_km - quality_km)
    easy_km = remaining_km / max(1, len(easy_days))

    out: list[WorkoutDraft] = []
    for weekday in selected_weekdays:
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
        out.append(
            WorkoutDraft(
                week_index=week_index,
                weekday=weekday,
                discipline="run",
                workout_type=workout_type,
                title=f"W{week_index:02d} {_title_for(workout_type)}",
                purpose=purpose,
                duration_min=duration_min,
                distance_m=round(distance_km * 1000, 1),
                target_intensity_type="pace",
                target_pace_min_sec_per_km=round(target_pace + pace_offset - 8, 1),
                target_pace_max_sec_per_km=round(target_pace + pace_offset + 12, 1),
                rpe_min=3 if workout_type != "threshold" else 6,
                rpe_max=5 if workout_type != "threshold" else 8,
                adaptation_notes="Generated from current COROS history and marathon goal.",
            )
        )
    return sorted(out, key=lambda w: w.weekday)


def _title_for(workout_type: str) -> str:
    return {
        "long_run": "Long Run",
        "marathon_pace": "Marathon Pace",
        "threshold": "Threshold",
        "easy_run": "Easy Run",
    }.get(workout_type, workout_type.replace("_", " ").title())


def _step(step_type: str, duration_sec: int, target_min: float, target_max: float, notes: str) -> StepDraft:
    return StepDraft(
        step_type=step_type,
        duration_sec=duration_sec,
        target_type="pace_sec_per_km",
        target_min=round(target_min, 1),
        target_max=round(target_max, 1),
        notes=notes,
    )
