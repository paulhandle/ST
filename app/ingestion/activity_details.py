from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ActivityDetailExport,
    ActivityDetailLap,
    ActivityDetailSample,
    AthleteActivity,
)
from app.tools.coros.fit_parser import FitActivityDetail, parse_fit_activity


def upsert_fit_activity_detail(
    db: Session,
    *,
    activity: AthleteActivity,
    data: bytes,
    file_url: str | None = None,
    downloaded_at: datetime | None = None,
) -> ActivityDetailExport:
    now = datetime.now(UTC)
    source_format = "fit"
    payload_hash = hashlib.sha256(data).hexdigest()
    existing = db.execute(
        select(ActivityDetailExport).where(
            ActivityDetailExport.activity_id == activity.id,
            ActivityDetailExport.source_format == source_format,
        )
    ).scalar_one_or_none()

    if existing is None:
        export = ActivityDetailExport(
            athlete_id=activity.athlete_id,
            activity_id=activity.id,
            provider=activity.provider,
            provider_activity_id=activity.provider_activity_id,
            source_format=source_format,
            raw_file_bytes=data,
        )
        db.add(export)
    else:
        export = existing

    export.athlete_id = activity.athlete_id
    export.provider = activity.provider
    export.provider_activity_id = activity.provider_activity_id
    export.file_size_bytes = len(data)
    export.payload_hash = payload_hash
    export.file_url_host = _host(file_url)
    export.downloaded_at = _naive_utc(downloaded_at or now)
    export.raw_file_bytes = data
    export.updated_at = now

    try:
        detail = parse_fit_activity(data)
    except Exception as exc:
        export.parsed_at = None
        export.sample_count = 0
        export.lap_count = 0
        export.warnings_json = json.dumps([f"FIT parse failed: {exc}"], ensure_ascii=False)
        db.flush()
        return export

    export.parsed_at = _naive_utc(now)
    export.sample_count = len(detail.samples)
    export.lap_count = len(detail.laps)
    export.warnings_json = json.dumps(detail.warnings, ensure_ascii=False)

    db.query(ActivityDetailSample).filter(ActivityDetailSample.activity_id == activity.id).delete()
    db.query(ActivityDetailLap).filter(ActivityDetailLap.activity_id == activity.id).delete()
    _update_activity_summary(activity, detail)
    for sample in detail.samples:
        db.add(
            ActivityDetailSample(
                activity_id=activity.id,
                sample_index=sample.sample_index,
                timestamp=sample.timestamp,
                elapsed_sec=sample.elapsed_sec,
                distance_m=sample.distance_m,
                latitude=sample.latitude,
                longitude=sample.longitude,
                altitude_m=sample.altitude_m,
                heart_rate=sample.heart_rate,
                cadence=sample.cadence,
                speed_mps=sample.speed_mps,
                pace_sec_per_km=sample.pace_sec_per_km,
                power_w=sample.power_w,
                temperature_c=sample.temperature_c,
                raw_json=json.dumps(sample.raw, ensure_ascii=False, default=str),
            )
        )
    for lap in detail.laps:
        db.add(
            ActivityDetailLap(
                activity_id=activity.id,
                lap_index=lap.lap_index,
                start_time=lap.start_time,
                end_time=lap.end_time,
                duration_sec=lap.duration_sec,
                distance_m=lap.distance_m,
                avg_hr=lap.avg_hr,
                max_hr=lap.max_hr,
                min_hr=lap.min_hr,
                avg_cadence=lap.avg_cadence,
                max_cadence=lap.max_cadence,
                avg_speed_mps=lap.avg_speed_mps,
                max_speed_mps=lap.max_speed_mps,
                avg_power_w=lap.avg_power_w,
                elevation_gain_m=lap.elevation_gain_m,
                elevation_loss_m=lap.elevation_loss_m,
                calories=lap.calories,
                avg_temperature_c=lap.avg_temperature_c,
                raw_json=json.dumps(lap.raw, ensure_ascii=False, default=str),
            )
        )
    db.flush()
    return export


def _update_activity_summary(activity: AthleteActivity, detail: FitActivityDetail) -> None:
    session = detail.session
    activity.distance_m = _float(session.get("total_distance")) or activity.distance_m
    activity.duration_sec = int(_float(session.get("total_timer_time")) or activity.duration_sec)
    activity.moving_duration_sec = int(_float(session.get("total_timer_time")) or activity.moving_duration_sec or activity.duration_sec)
    activity.elevation_gain_m = _float(session.get("total_ascent")) or activity.elevation_gain_m
    activity.avg_hr = _float(session.get("avg_heart_rate")) or activity.avg_hr
    activity.max_hr = _float(session.get("max_heart_rate")) or activity.max_hr
    activity.avg_power = _float(session.get("avg_power")) or activity.avg_power
    cadence = _float(session.get("avg_running_cadence") or session.get("avg_cadence"))
    if cadence is not None:
        activity.avg_cadence = cadence * 2 if cadence < 120 else cadence
    if activity.distance_m:
        activity.avg_pace_sec_per_km = activity.duration_sec / (activity.distance_m / 1000)
    activity.updated_at = datetime.now(UTC)


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _host(url: str | None) -> str | None:
    if not url:
        return None
    return urlparse(url).netloc or None


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
