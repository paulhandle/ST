from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AthleteActivity, AthleteMetricSnapshot

MARATHON_DISTANCE_KM = 42.195


def assess_running_ability(
    db: Session,
    athlete_id: int,
    target_time_sec: int | None = None,
    plan_weeks: int | None = None,
    requested_training_days: int | None = None,
) -> dict:
    now = datetime.utcnow()
    since_12w = now - timedelta(days=84)
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.discipline == "run")
        .where(AthleteActivity.started_at >= since_12w)
        .order_by(AthleteActivity.started_at.asc())
    ).scalars().all()

    warnings: list[str] = []
    limiting_factors: list[str] = []
    if not activities:
        return _empty_assessment(
            athlete_id=athlete_id,
            target_time_sec=target_time_sec,
            plan_weeks=plan_weeks,
            requested_training_days=requested_training_days,
        )

    weekly_distance = defaultdict(float)
    weekly_runs = defaultdict(int)
    paces = []
    long_run_capacity_km = 0.0
    training_loads = []
    feedback_text = []

    for activity in activities:
        week_key = activity.started_at.isocalendar()[:2]
        distance_km = activity.distance_m / 1000
        weekly_distance[week_key] += distance_km
        weekly_runs[week_key] += 1
        long_run_capacity_km = max(long_run_capacity_km, distance_km)
        if activity.avg_pace_sec_per_km and distance_km >= 5:
            paces.append(activity.avg_pace_sec_per_km)
        if activity.training_load is not None:
            training_loads.append(activity.training_load)
        if activity.feedback_text:
            feedback_text.append(activity.feedback_text.lower())

    distances = list(weekly_distance.values())
    run_counts = list(weekly_runs.values())
    avg_weekly_km = sum(distances) / 12
    peak_weekly_km = max(distances) if distances else 0.0
    avg_runs_per_week = sum(run_counts) / 12
    recent_best_pace = min(paces) if paces else 390.0
    predicted_marathon_sec = _predicted_marathon_time(db, athlete_id, recent_best_pace)

    safe_low = round(max(18.0, avg_weekly_km * 0.85), 1)
    safe_high = round(max(safe_low + 8.0, min(max(35.0, avg_weekly_km * 1.3), peak_weekly_km * 1.15 + 8)), 1)
    safe_days_low = max(3, min(5, round(avg_runs_per_week)))
    safe_days_high = min(6, max(safe_days_low, safe_days_low + 1))

    consistency_score = min(30, int((len(weekly_distance) / 12) * 30))
    volume_score = min(25, int((avg_weekly_km / 55) * 25))
    long_run_score = min(25, int((long_run_capacity_km / 30) * 25))
    recovery_score = 20
    if any("pain" in text or "疼" in text for text in feedback_text):
        recovery_score -= 8
        warnings.append("Recent feedback mentions pain.")
        limiting_factors.append("pain_feedback")
    if training_loads and len(training_loads) >= 8 and sum(training_loads[-4:]) > sum(training_loads[:4]) * 1.8:
        recovery_score -= 5
        warnings.append("Recent training load appears to be rising quickly.")
        limiting_factors.append("load_spike")

    overall_score = max(0, min(100, consistency_score + volume_score + long_run_score + recovery_score))
    readiness_level = "high" if overall_score >= 75 else "moderate" if overall_score >= 55 else "low"

    if avg_weekly_km < 35:
        warnings.append("Recent weekly distance is low for an aggressive full-marathon target.")
        limiting_factors.append("recent_volume")
    if long_run_capacity_km < 24:
        warnings.append("Long-run capacity is still below a typical marathon build requirement.")
        limiting_factors.append("long_run_capacity")
    if requested_training_days is not None and requested_training_days < safe_days_low:
        warnings.append("Requested weekly training days are below the recommended range.")
        limiting_factors.append("training_availability")
    if requested_training_days is not None and requested_training_days > safe_days_high + 1:
        warnings.append("Requested weekly training days may exceed recent training tolerance.")
        limiting_factors.append("training_availability")

    goal_status = _goal_status(
        predicted_marathon_sec=predicted_marathon_sec,
        target_time_sec=target_time_sec,
        plan_weeks=plan_weeks,
        avg_weekly_km=avg_weekly_km,
        long_run_capacity_km=long_run_capacity_km,
        warnings=warnings,
    )

    confidence = "high" if len(activities) >= 36 and paces else "medium" if len(activities) >= 12 else "low"
    estimated_range = [int(predicted_marathon_sec * 0.97), int(predicted_marathon_sec * 1.08)]
    summary = _summary(goal_status=goal_status, target_time_sec=target_time_sec, estimated_range=estimated_range)

    return {
        "athlete_id": athlete_id,
        "overall_score": overall_score,
        "readiness_level": readiness_level,
        "safe_weekly_distance_range_km": [safe_low, safe_high],
        "safe_training_days_range": [safe_days_low, safe_days_high],
        "long_run_capacity_km": round(long_run_capacity_km, 1),
        "estimated_marathon_time_range_sec": estimated_range,
        "goal_status": goal_status,
        "limiting_factors": sorted(set(limiting_factors)),
        "warnings": warnings,
        "confidence": confidence,
        "summary": summary,
    }


def _predicted_marathon_time(db: Session, athlete_id: int, recent_best_pace: float) -> float:
    predictor = db.execute(
        select(AthleteMetricSnapshot)
        .where(AthleteMetricSnapshot.athlete_id == athlete_id)
        .where(AthleteMetricSnapshot.metric_type == "race_predictor_marathon")
        .order_by(AthleteMetricSnapshot.measured_at.desc())
    ).scalars().first()
    if predictor is not None:
        return predictor.value
    return recent_best_pace * MARATHON_DISTANCE_KM * 1.15


def _goal_status(
    predicted_marathon_sec: float,
    target_time_sec: int | None,
    plan_weeks: int | None,
    avg_weekly_km: float,
    long_run_capacity_km: float,
    warnings: list[str],
) -> str:
    if plan_weeks is not None and plan_weeks < 8:
        warnings.append("Training window is too short for a safe full-marathon build.")
        return "reject"
    if target_time_sec is None:
        return "accept_with_warning" if warnings else "accept"

    if target_time_sec < predicted_marathon_sec * 0.88:
        return "reject"
    if avg_weekly_km < 25 and target_time_sec < 4 * 3600:
        return "reject"
    if long_run_capacity_km < 18 and target_time_sec < 4 * 3600:
        return "recommend_adjustment"
    if target_time_sec < predicted_marathon_sec * 0.97 or warnings:
        return "accept_with_warning"
    return "accept"


def _summary(goal_status: str, target_time_sec: int | None, estimated_range: list[int]) -> str:
    estimate = f"{_format_time(estimated_range[0])}-{_format_time(estimated_range[1])}"
    if target_time_sec is None:
        return f"Current data supports building a completion-focused marathon plan. Estimated range is {estimate}."
    target = _format_time(target_time_sec)
    if goal_status == "reject":
        return f"Current data does not safely support a {target} marathon target in the requested window."
    if goal_status in {"accept_with_warning", "recommend_adjustment"}:
        return f"A {target} target may be possible but needs conservative progression. Estimated range is {estimate}."
    return f"Current data supports a {target} marathon target. Estimated range is {estimate}."


def _empty_assessment(
    athlete_id: int,
    target_time_sec: int | None,
    plan_weeks: int | None,
    requested_training_days: int | None,
) -> dict:
    warnings = ["No recent running history is available."]
    if plan_weeks is not None and plan_weeks < 12:
        warnings.append("Training window is short for a first full-marathon build.")
    if requested_training_days is not None and requested_training_days < 4:
        warnings.append("Requested training days are low for marathon preparation.")
    return {
        "athlete_id": athlete_id,
        "overall_score": 20,
        "readiness_level": "low",
        "safe_weekly_distance_range_km": [15.0, 25.0],
        "safe_training_days_range": [3, 4],
        "long_run_capacity_km": 0.0,
        "estimated_marathon_time_range_sec": [16200, 19800],
        "goal_status": "reject" if target_time_sec and target_time_sec < 4 * 3600 else "recommend_adjustment",
        "limiting_factors": ["missing_history"],
        "warnings": warnings,
        "confidence": "low",
        "summary": "Import COROS running history before trusting goal feasibility or plan intensity.",
    }


def _format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}:{minutes:02d}"
