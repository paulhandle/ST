from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ActivityLap, AthleteActivity, AthleteMetricSnapshot, AthleteProfile


def import_provider_history(
    db: Session,
    athlete: AthleteProfile,
    provider: str,
    activities: list[dict],
    metrics: list[dict] | None = None,
) -> dict:
    imported_count = 0
    updated_count = 0

    for item in activities:
        provider_activity_id = str(item["provider_activity_id"])
        existing = db.execute(
            select(AthleteActivity).where(
                AthleteActivity.provider == provider,
                AthleteActivity.provider_activity_id == provider_activity_id,
            )
        ).scalar_one_or_none()

        payload = _activity_payload(athlete_id=athlete.id, provider=provider, item=item)
        if existing is None:
            activity = AthleteActivity(**payload)
            db.add(activity)
            db.flush()
            imported_count += 1
        else:
            activity = existing
            for key, value in payload.items():
                setattr(activity, key, value)
            activity.updated_at = datetime.now(UTC)
            db.query(ActivityLap).filter(ActivityLap.activity_id == activity.id).delete()
            updated_count += 1

        for lap in item.get("laps", []):
            db.add(ActivityLap(activity_id=activity.id, **_lap_payload(lap)))

    metric_count = 0
    for metric in metrics or []:
        db.add(
            AthleteMetricSnapshot(
                athlete_id=athlete.id,
                provider=provider,
                measured_at=metric.get("measured_at") or datetime.now(UTC),
                metric_type=metric["metric_type"],
                value=float(metric["value"]),
                unit=metric.get("unit"),
                raw_payload_json=json.dumps(metric.get("raw_payload", metric), ensure_ascii=False),
            )
        )
        metric_count += 1

    db.commit()
    return {
        "imported_count": imported_count,
        "updated_count": updated_count,
        "metric_count": metric_count,
    }


def _activity_payload(athlete_id: int, provider: str, item: dict) -> dict:
    raw_payload = item.get("raw_payload", item)
    return {
        "athlete_id": athlete_id,
        "provider": provider,
        "provider_activity_id": str(item["provider_activity_id"]),
        "sport": item.get("sport", "running"),
        "discipline": item.get("discipline", "run"),
        "started_at": item["started_at"],
        "timezone": item.get("timezone"),
        "duration_sec": int(item["duration_sec"]),
        "moving_duration_sec": item.get("moving_duration_sec"),
        "distance_m": float(item["distance_m"]),
        "elevation_gain_m": _optional_float(item.get("elevation_gain_m")),
        "avg_pace_sec_per_km": _optional_float(item.get("avg_pace_sec_per_km")),
        "avg_hr": _optional_float(item.get("avg_hr")),
        "max_hr": _optional_float(item.get("max_hr")),
        "avg_cadence": _optional_float(item.get("avg_cadence")),
        "avg_power": _optional_float(item.get("avg_power")),
        "training_load": _optional_float(item.get("training_load")),
        "perceived_effort": item.get("perceived_effort"),
        "feedback_text": item.get("feedback_text"),
        "raw_payload_json": json.dumps(raw_payload, ensure_ascii=False, default=str),
    }


def _lap_payload(item: dict) -> dict:
    return {
        "lap_index": int(item["lap_index"]),
        "duration_sec": int(item["duration_sec"]),
        "distance_m": float(item["distance_m"]),
        "avg_pace_sec_per_km": _optional_float(item.get("avg_pace_sec_per_km")),
        "avg_hr": _optional_float(item.get("avg_hr")),
        "elevation_gain_m": _optional_float(item.get("elevation_gain_m")),
    }


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    return float(value)
