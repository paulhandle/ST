from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta

from openai import OpenAI

log = logging.getLogger(__name__)

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _make_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://us.api.xianfeiglobal.com/v1"),
    )


def _pace_to_sec(pace: str) -> float:
    """Convert 'M:SS' or 'MM:SS' string to seconds per km."""
    try:
        parts = pace.strip().split(":")
        return float(parts[0]) * 60 + float(parts[1])
    except Exception:
        return 360.0


def _format_pace(sec_per_km: float) -> str:
    m = int(sec_per_km // 60)
    s = int(sec_per_km % 60)
    return f"{m}:{s:02d}"


def _format_time(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h}:{m:02d}"


def _date_for_weekday(start_date: date, week_index: int, weekday: int) -> date:
    week_start = start_date + timedelta(weeks=week_index - 1)
    return week_start + timedelta(days=(weekday - week_start.weekday()) % 7)


def generate_marathon_plan_llm(
    assessment: dict,
    plan_weeks: int,
    target_time_sec: int | None,
    target_pace_sec_per_km: float,
    selected_weekdays: list[int],
    preferred_long_run_weekday: int,
    start_date: date,
) -> list[list[dict]]:
    """
    Calls the LLM to generate a full marathon training plan.

    Returns a list (one entry per week) of lists of workout_data dicts,
    each compatible with StructuredWorkout(**workout_data).
    Raises on any error so caller can fall back to rule-based generation.
    """
    client = _make_client()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    available_days_str = ", ".join(WEEKDAY_NAMES[d] for d in sorted(selected_weekdays))
    long_run_day_str = WEEKDAY_NAMES[preferred_long_run_weekday]

    if target_time_sec:
        goal_str = f"sub-{_format_time(target_time_sec)} ({target_time_sec // 60} minutes total)"
    else:
        goal_str = "finish the marathon (no specific time goal)"

    safe_low, safe_high = assessment["safe_weekly_distance_range_km"]
    est_low, est_high = assessment["estimated_marathon_time_range_sec"]

    assessment_block = f"""\
- Readiness: {assessment['readiness_level']} (score {assessment['overall_score']}/100, confidence {assessment['confidence']})
- Recent avg weekly volume: {safe_low:.0f}–{safe_high:.0f} km safe range
- Long run capacity: {assessment['long_run_capacity_km']:.1f} km
- Estimated marathon time: {_format_time(est_low)}–{_format_time(est_high)}
- Warnings: {'; '.join(assessment['warnings']) or 'None'}
- Limiting factors: {', '.join(assessment['limiting_factors']) or 'None'}"""

    base_end = int(plan_weeks * 0.50)
    build_end = int(plan_weeks * 0.82)
    peak_end = int(plan_weeks * 0.94)
    taper_weeks = plan_weeks - peak_end

    system_prompt = f"""You are an expert marathon coach. Generate a {plan_weeks}-week full marathon training plan as JSON.

TRAINING PRINCIPLES:
- 80/20 polarized: ~80% easy (RPE 3-5), ~20% quality (RPE 6-9)
- Periodization: Base (weeks 1-{base_end}) → Build (weeks {base_end+1}-{build_end}) → Peak (weeks {build_end+1}-{peak_end}) → Taper (last {taper_weeks} week{'s' if taper_weeks > 1 else ''})
- Every 4th week is a recovery week: reduce volume ~18%
- Long runs cap at 32 km
- No back-to-back hard sessions
- Taper: reduce volume ~40%, keep intensity

OUTPUT FORMAT — respond with ONLY valid JSON:
{{
  "weeks": [
    {{
      "week_index": 1,
      "phase": "base",
      "total_km": 42.0,
      "focus": "One sentence training focus",
      "workouts": [
        {{
          "weekday": 0,
          "workout_type": "easy_run",
          "title": "Easy Aerobic Run",
          "purpose": "Build aerobic base",
          "distance_km": 9.0,
          "duration_min": 56,
          "pace_min": "5:50",
          "pace_max": "6:20",
          "rpe_min": 3,
          "rpe_max": 4
        }}
      ]
    }}
  ]
}}

RULES:
- weekday: 0=Monday … 6=Sunday
- workout_type: easy_run | long_run | marathon_pace | threshold
- pace_min/pace_max: "M:SS" format (minutes:seconds per km)
- Include EXACTLY {len(selected_weekdays)} workouts per week
- Include ALL {plan_weeks} weeks (week_index 1 through {plan_weeks})
- Long run goes on {long_run_day_str} (weekday {preferred_long_run_weekday})
- Training days: weekdays {sorted(selected_weekdays)} ({available_days_str})"""

    user_prompt = f"""Create a {plan_weeks}-week marathon training plan.

GOAL: {goal_str}
ATHLETE DATA:
{assessment_block}

TARGET PACES:
- Marathon pace: {_format_pace(target_pace_sec_per_km)}/km
- Easy pace: ~{_format_pace(target_pace_sec_per_km + 75)}/km
- Threshold pace: ~{_format_pace(target_pace_sec_per_km - 20)}/km

Generate the complete plan now. Respect the athlete's current fitness and safe volume range."""

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

    return _convert_to_workout_dicts(weeks_data, selected_weekdays, start_date, target_pace_sec_per_km)


def _convert_to_workout_dicts(
    weeks_data: list[dict],
    selected_weekdays: list[int],
    start_date: date,
    target_pace_sec_per_km: float,
) -> list[list[dict]]:
    result: list[list[dict]] = []
    for week_data in weeks_data:
        week_index = int(week_data.get("week_index", len(result) + 1))
        week_workouts: list[dict] = []

        for w in week_data.get("workouts", []):
            weekday = int(w.get("weekday", selected_weekdays[0]))
            if weekday not in selected_weekdays:
                weekday = min(selected_weekdays, key=lambda d: abs(d - weekday))

            scheduled_date = _date_for_weekday(start_date, week_index, weekday)
            distance_km = float(w.get("distance_km", 8.0))
            pace_min_sec = _pace_to_sec(str(w.get("pace_min", "6:00")))
            pace_max_sec = _pace_to_sec(str(w.get("pace_max", "6:30")))
            duration_min = int(w.get("duration_min") or max(25, int(distance_km * pace_min_sec / 60)))
            workout_type = str(w.get("workout_type", "easy_run"))

            week_workouts.append(
                {
                    "scheduled_date": scheduled_date,
                    "week_index": week_index,
                    "discipline": "run",
                    "workout_type": workout_type,
                    "title": str(w.get("title", f"W{week_index:02d} {workout_type.replace('_', ' ').title()}")),
                    "purpose": str(w.get("purpose", "")),
                    "duration_min": duration_min,
                    "distance_m": round(distance_km * 1000, 1),
                    "target_intensity_type": "pace",
                    "target_pace_min_sec_per_km": round(pace_min_sec, 1),
                    "target_pace_max_sec_per_km": round(pace_max_sec, 1),
                    "rpe_min": int(w.get("rpe_min", 3)),
                    "rpe_max": int(w.get("rpe_max", 5)),
                    "adaptation_notes": "AI-generated by LLM coach based on COROS history and marathon goal.",
                }
            )

        result.append(sorted(week_workouts, key=lambda x: x["scheduled_date"]))
    return result
