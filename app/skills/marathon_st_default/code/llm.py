"""LLM-based marathon plan generator.

Pure function: SkillContext in, list of weeks of WorkoutDraft out.
Constructs an OpenAI client from env vars and renders the prompt template
from llm_prompt.md. Raises on any failure so the skill can fall back cleanly.
"""
from __future__ import annotations

import json
import logging
import os
from importlib.resources import files

from openai import OpenAI

from app.core.context import SkillContext, StepDraft, WorkoutDraft
from app.kb.running import format_pace, format_time

log = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def generate_weeks(ctx: SkillContext) -> list[list[WorkoutDraft]]:
    client = _make_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    plan_weeks = ctx.goal.plan_weeks
    target_time_sec = ctx.goal.target_time_sec
    target_pace = (
        target_time_sec / 42.195
        if target_time_sec is not None
        else (
            sum(ctx.assessment.estimated_marathon_time_range_sec) / 2 / 42.195
            if ctx.assessment
            else 360.0
        )
    )

    selected_weekdays = sorted(set(ctx.availability.selected_weekdays))
    preferred_long_run_weekday = ctx.availability.preferred_long_run_weekday

    available_days_str = ", ".join(WEEKDAY_NAMES[d] for d in selected_weekdays)
    long_run_day_str = WEEKDAY_NAMES[preferred_long_run_weekday]

    if target_time_sec:
        goal_str = f"sub-{format_time(target_time_sec)} ({target_time_sec // 60} minutes total)"
    else:
        goal_str = "finish the marathon (no specific time goal)"

    base_end = int(plan_weeks * 0.50)
    build_end = int(plan_weeks * 0.82)
    peak_end = int(plan_weeks * 0.94)
    taper_weeks = max(1, plan_weeks - peak_end)

    template = _load_prompt_template()
    system_prompt = template.format(
        plan_weeks=plan_weeks,
        base_end=base_end,
        build_end=build_end,
        peak_end=peak_end,
        base_end_plus_1=base_end + 1,
        build_end_plus_1=build_end + 1,
        taper_weeks=taper_weeks,
        taper_plural="s" if taper_weeks > 1 else "",
        workouts_per_week=len(selected_weekdays),
        selected_weekdays_list=str(selected_weekdays),
        available_days_str=available_days_str,
        long_run_day_str=long_run_day_str,
        preferred_long_run_weekday=preferred_long_run_weekday,
    )

    user_prompt = _build_user_prompt(ctx, goal_str, target_pace)

    log.info("Requesting LLM marathon plan: model=%s weeks=%d goal=%s", model, plan_weeks, goal_str)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )
    raw = resp.choices[0].message.content
    plan_data = json.loads(raw)
    weeks_data = plan_data.get("weeks") or plan_data.get("plan", {}).get("weeks", [])
    if not weeks_data:
        raise ValueError("LLM response missing 'weeks' key")

    return _convert_to_workouts(weeks_data, selected_weekdays)


def _make_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://us.api.xianfeiglobal.com/v1"),
    )


def _load_prompt_template() -> str:
    raw = files("app.skills.marathon_st_default.code").joinpath("llm_prompt.md").read_text(encoding="utf-8")
    parts = raw.split("---\n", 1)
    return parts[1] if len(parts) == 2 else raw


def _build_user_prompt(ctx: SkillContext, goal_str: str, target_pace: float) -> str:
    plan_weeks = ctx.goal.plan_weeks
    a = ctx.assessment
    safe_low, safe_high = (a.safe_weekly_distance_range_km if a else (24.0, 60.0))
    est_low, est_high = (a.estimated_marathon_time_range_sec if a else (4 * 3600, 5 * 3600))

    lthr = ctx.history.latest_metrics.get("lthr")
    if lthr:
        z2_lo, z2_hi = int(lthr * 0.69), int(lthr * 0.83)
        z3_lo, z3_hi = int(lthr * 0.83), int(lthr * 0.91)
        z4_lo, z4_hi = int(lthr * 0.91), int(lthr)
        lthr_block = (
            f"- LTHR: {lthr:.0f} bpm → "
            f"Zone 2 (easy) {z2_lo}–{z2_hi} bpm | "
            f"Zone 3 (aerobic) {z3_lo}–{z3_hi} bpm | "
            f"Zone 4 (threshold) {z4_lo}–{z4_hi} bpm"
        )
        ltsp = ctx.history.latest_metrics.get("ltsp")
        if ltsp:
            lthr_block += f" | Threshold pace: {format_pace(ltsp)}/km"
    else:
        lthr_block = "- LTHR: unknown (use pace-based zones)"

    weekly_km_str = ", ".join(str(v) for v in ctx.history.weekly_km_last_8w)
    long_runs_str = "\n".join(f"  {lr}" for lr in ctx.history.recent_long_runs)

    if a:
        assessment_block = (
            f"- Readiness: {a.readiness_level} (score {a.overall_score}/100, confidence {a.confidence})\n"
            f"- Safe weekly volume range: {safe_low:.0f}–{safe_high:.0f} km\n"
            f"- Long run capacity: {a.long_run_capacity_km:.1f} km\n"
            f"- Estimated marathon time: {format_time(est_low)}–{format_time(est_high)}\n"
            f"{lthr_block}\n"
            f"- Recent 8-week volumes (km): {weekly_km_str or 'not available'}\n"
            f"- Recent long runs:\n{long_runs_str or '  none on record'}\n"
            f"- Warnings: {'; '.join(a.warnings) or 'None'}\n"
            f"- Limiting factors: {', '.join(a.limiting_factors) or 'None'}"
        )
    else:
        assessment_block = (
            f"{lthr_block}\n"
            f"- Recent 8-week volumes (km): {weekly_km_str or 'not available'}\n"
            f"- Recent long runs:\n{long_runs_str or '  none on record'}"
        )

    profile_section = f"\nATHLETE PROFILE:\n{ctx.athlete.profile_block}\n" if ctx.athlete.profile_block.strip() else ""

    return (
        f"Create a {plan_weeks}-week marathon training plan.\n\n"
        f"GOAL: {goal_str}\n"
        f"{profile_section}\n"
        f"ATHLETE TRAINING DATA:\n{assessment_block}\n\n"
        f"TARGET PACES:\n"
        f"- Marathon pace: {format_pace(target_pace)}/km\n"
        f"- Easy pace: ~{format_pace(target_pace + 75)}/km\n"
        f"- Threshold pace: ~{format_pace(target_pace - 20)}/km\n\n"
        "Generate the complete plan now. Use LTHR zones where available. "
        "Respect the athlete's current fitness, safe volume range, and any injury notes."
    )


def _convert_to_workouts(weeks_data: list[dict], selected_weekdays: list[int]) -> list[list[WorkoutDraft]]:
    out: list[list[WorkoutDraft]] = []
    for idx, week_data in enumerate(weeks_data):
        week_index = int(week_data.get("week_index", idx + 1))
        week_workouts: list[WorkoutDraft] = []
        for w in week_data.get("workouts", []):
            weekday = int(w.get("weekday", selected_weekdays[0]))
            if weekday not in selected_weekdays:
                weekday = min(selected_weekdays, key=lambda d: abs(d - weekday))

            distance_km = float(w.get("distance_km", 8.0))
            pace_min_sec = _pace_to_sec(str(w.get("pace_min", "6:00")))
            pace_max_sec = _pace_to_sec(str(w.get("pace_max", "6:30")))
            duration_min = int(w.get("duration_min") or max(25, int(distance_km * pace_min_sec / 60)))
            workout_type = str(w.get("workout_type", "easy_run"))

            week_workouts.append(
                WorkoutDraft(
                    week_index=week_index,
                    weekday=weekday,
                    discipline="run",
                    workout_type=workout_type,
                    title=str(w.get("title", f"W{week_index:02d} {workout_type.replace('_', ' ').title()}")),
                    purpose=str(w.get("purpose", "")),
                    duration_min=duration_min,
                    distance_m=round(distance_km * 1000, 1),
                    target_intensity_type="pace",
                    target_pace_min_sec_per_km=round(pace_min_sec, 1),
                    target_pace_max_sec_per_km=round(pace_max_sec, 1),
                    rpe_min=int(w.get("rpe_min", 3)),
                    rpe_max=int(w.get("rpe_max", 5)),
                    adaptation_notes="AI-generated by LLM coach based on COROS history and marathon goal.",
                )
            )
        out.append(sorted(week_workouts, key=lambda x: x.weekday))
    return out


def _pace_to_sec(pace: str) -> float:
    try:
        parts = pace.strip().split(":")
        return float(parts[0]) * 60 + float(parts[1])
    except Exception:
        return 360.0
