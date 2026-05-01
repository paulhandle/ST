"""Render template-based workouts into WorkoutDraft + StepDraft, decoding
intensity from %LTHR back to absolute pace / HR using the athlete's threshold.

Athlete portability: each template stores intensity_pct_lthr (e.g. 73 = 73%
of LTHR). At plan-generation time we map that to a pace using the athlete's
LTSP (lactate threshold pace). Mapping is approximate but consistent with
how the source coach assigned paces.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean

from app.core.context import SkillContext, StepDraft, WorkoutDraft
from app.kb.running import MARATHON_DISTANCE_KM


def _athlete_lthr_pace_sec_per_km(ctx: SkillContext) -> float:
    """Best-effort estimate of the athlete's LTSP (sec/km at 100 % LTHR)."""
    ltsp = ctx.history.latest_metrics.get("ltsp")
    if ltsp:
        return float(ltsp)
    if ctx.goal.target_time_sec:
        return ctx.goal.target_time_sec / MARATHON_DISTANCE_KM - 25
    if ctx.assessment:
        est = mean(ctx.assessment.estimated_marathon_time_range_sec)
        return est / MARATHON_DISTANCE_KM - 25
    return 320.0


def _pace_for_pct(pct: float | None, ltsp: float) -> float | None:
    """Map %LTHR to pace-sec-per-km using a piecewise model.

    100 % LTHR ≈ LTSP. Higher LTHR % runs faster (lower sec/km).
    Below LTHR pace falls off non-linearly:
      70 %  → LTSP + 80 s/km
      80 %  → LTSP + 50 s/km
      90 %  → LTSP + 18 s/km
      100 % → LTSP
      110 % → LTSP - 25 s/km
      120 % → LTSP - 55 s/km (sprint repeats)
    """
    if pct is None:
        return None
    if pct >= 100:
        delta = (pct - 100) * -3
    elif pct >= 90:
        delta = (100 - pct) * 1.8
    elif pct >= 80:
        delta = 18 + (90 - pct) * 3.2
    elif pct >= 70:
        delta = 50 + (80 - pct) * 3.0
    else:
        delta = 80 + (70 - pct) * 4.0
    return round(ltsp + delta, 1)


def _step_from_exercise(ex: dict, ltsp: float) -> StepDraft:
    pct = ex.get("intensity_pct_lthr")
    pace = _pace_for_pct(pct, ltsp)
    target_kind = ex.get("target_kind") or "open"
    target_value = ex.get("target_value")
    duration_sec = 0
    distance_m = None
    if target_kind == "duration_sec" and target_value:
        duration_sec = int(target_value)
    elif target_kind == "distance_m" and target_value:
        distance_m = float(target_value)
        if pace:
            duration_sec = int(distance_m / 1000 * pace)
        else:
            duration_sec = 0
    rest = ex.get("rest") or {}
    notes_parts = []
    if pct is not None:
        notes_parts.append(f"{pct:.0f}% LTHR")
    if ex.get("sets", 1) > 1:
        notes_parts.append(f"{ex['sets']}× repeat")
    if rest.get("value"):
        notes_parts.append(f"rest {rest['value']}s")
    notes = " · ".join(notes_parts) or None
    return StepDraft(
        step_type=_step_type_for(pct),
        duration_sec=duration_sec,
        target_type="pace_sec_per_km" if pace else "open",
        target_min=(round(pace - 8, 1) if pace else None),
        target_max=(round(pace + 12, 1) if pace else None),
        notes=notes,
        distance_m=distance_m,
        repeat_count=ex.get("sets") if ex.get("sets", 1) > 1 else None,
    )


def _step_type_for(pct: float | None) -> str:
    if pct is None:
        return "work"
    if pct < 60:
        return "warmup"
    if pct >= 100:
        return "work"
    if pct >= 88:
        return "work"
    return "work"


def _workout_type_for_role(role: str) -> str:
    return {
        "aerobic_base": "easy_run",
        "easy_aerobic": "easy_run",
        "recovery": "recovery_run",
        "long_run_easy": "long_run",
        "long_run_race_specific": "long_run",
        "long_run_extended": "long_run",
        "speed_alactic_strides": "speed",
        "tempo_combo": "threshold",
        "sustained_tempo_strides": "marathon_pace",
        "strength": "strength",
        "long_run_taper": "long_run",
    }.get(role, "easy_run")


def render_workout(
    ctx: SkillContext,
    template: dict,
    week_index: int,
    weekday: int,
    role_override: str | None = None,
) -> WorkoutDraft:
    """Convert a JSON template to a WorkoutDraft for the given week + weekday."""
    ltsp = _athlete_lthr_pace_sec_per_km(ctx)
    role = role_override or template.get("role", "easy_aerobic")
    workout_type = _workout_type_for_role(role)
    distance_m = float(template.get("distance_m") or 0)
    duration_min = int((template.get("duration_sec") or 0) // 60) or max(20, int(distance_m / 1000 * ltsp / 60))

    steps = [_step_from_exercise(ex, ltsp) for ex in template.get("exercises", [])]
    overall_pcts = [ex.get("intensity_pct_lthr") for ex in template.get("exercises", []) if ex.get("intensity_pct_lthr")]
    pace_min, pace_max = None, None
    if overall_pcts:
        avg_pct = mean(overall_pcts)
        avg_pace = _pace_for_pct(avg_pct, ltsp)
        if avg_pace:
            pace_min = round(avg_pace - 12, 1)
            pace_max = round(avg_pace + 18, 1)

    rpe_min, rpe_max = _rpe_for_role(role)

    return WorkoutDraft(
        week_index=week_index,
        weekday=weekday,
        discipline="strength" if role == "strength" else "run",
        workout_type=workout_type,
        title=f"W{week_index:02d} {template['name']}",
        purpose=f"{role.replace('_', ' ').title()} — extracted from coach methodology.",
        duration_min=duration_min,
        distance_m=round(distance_m, 1) if distance_m else None,
        target_intensity_type="pace" if pace_min else "rpe",
        target_pace_min_sec_per_km=pace_min,
        target_pace_max_sec_per_km=pace_max,
        rpe_min=rpe_min,
        rpe_max=rpe_max,
        adaptation_notes=(
            "完成 > 配速；未达配速也要完成。当日缺训不补；今日做今日课。"
            "速度课内的恢复跑保持步频，速度可降。"
        ),
        steps=steps,
    )


def _rpe_for_role(role: str) -> tuple[int, int]:
    return {
        "recovery": (2, 3),
        "aerobic_base": (3, 4),
        "easy_aerobic": (3, 4),
        "long_run_easy": (3, 5),
        "long_run_race_specific": (5, 7),
        "long_run_extended": (4, 6),
        "long_run_taper": (3, 4),
        "speed_alactic_strides": (5, 8),
        "tempo_combo": (6, 8),
        "sustained_tempo_strides": (5, 7),
        "strength": (4, 6),
    }.get(role, (3, 5))


def date_for_weekday(start_date: date, week_index: int, weekday: int) -> date:
    week_start = start_date + timedelta(weeks=week_index - 1)
    return week_start + timedelta(days=(weekday - week_start.weekday()) % 7)
