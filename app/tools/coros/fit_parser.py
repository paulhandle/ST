from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import BytesIO
from typing import Any

from fitparse import FitFile


SEMICIRCLE_SCALE = 180.0 / (2**31)


@dataclass
class FitSample:
    sample_index: int
    timestamp: datetime
    elapsed_sec: float | None = None
    distance_m: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None
    speed_mps: float | None = None
    pace_sec_per_km: float | None = None
    power_w: float | None = None
    temperature_c: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FitLap:
    lap_index: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_sec: float | None = None
    distance_m: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    min_hr: float | None = None
    avg_cadence: float | None = None
    max_cadence: float | None = None
    avg_speed_mps: float | None = None
    max_speed_mps: float | None = None
    avg_power_w: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    calories: float | None = None
    avg_temperature_c: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FitActivityDetail:
    samples: list[FitSample]
    laps: list[FitLap]
    session: dict[str, Any]
    warnings: list[str]


def parse_fit_activity(data: bytes) -> FitActivityDetail:
    fit = FitFile(BytesIO(data))
    samples: list[FitSample] = []
    laps: list[FitLap] = []
    session: dict[str, Any] = {}
    warnings: list[str] = []
    start_time: datetime | None = None

    for message in fit.get_messages():
        values = _message_values(message)
        if message.name == "session":
            session = values
            start_time = _as_datetime(values.get("start_time")) or start_time
        elif message.name == "record":
            timestamp = _as_datetime(values.get("timestamp"))
            if timestamp is None:
                warnings.append(f"Skipped record without timestamp at index {len(samples)}")
                continue
            if start_time is None:
                start_time = timestamp
            speed_mps = _float(values.get("enhanced_speed") or values.get("speed"))
            sample = FitSample(
                sample_index=len(samples),
                timestamp=timestamp,
                elapsed_sec=(timestamp - start_time).total_seconds() if start_time else None,
                distance_m=_float(values.get("distance")),
                latitude=_semicircle_to_degrees(values.get("position_lat")),
                longitude=_semicircle_to_degrees(values.get("position_long")),
                altitude_m=_float(values.get("enhanced_altitude") or values.get("altitude")),
                heart_rate=_float(values.get("heart_rate")),
                cadence=_float(values.get("cadence") or values.get("running_cadence")),
                speed_mps=speed_mps,
                pace_sec_per_km=(1000.0 / speed_mps) if speed_mps and speed_mps > 0 else None,
                power_w=_float(values.get("power")),
                temperature_c=_float(values.get("temperature")),
                raw=_json_safe(values),
            )
            samples.append(sample)
        elif message.name == "lap":
            start = _as_datetime(values.get("start_time"))
            end = _as_datetime(values.get("timestamp"))
            laps.append(
                FitLap(
                    lap_index=len(laps),
                    start_time=start,
                    end_time=end,
                    duration_sec=_float(values.get("total_timer_time") or values.get("total_elapsed_time")),
                    distance_m=_float(values.get("total_distance")),
                    avg_hr=_float(values.get("avg_heart_rate")),
                    max_hr=_float(values.get("max_heart_rate")),
                    min_hr=_float(values.get("min_heart_rate")),
                    avg_cadence=_float(values.get("avg_running_cadence") or values.get("avg_cadence")),
                    max_cadence=_float(values.get("max_running_cadence") or values.get("max_cadence")),
                    avg_speed_mps=_float(values.get("enhanced_avg_speed") or values.get("avg_speed")),
                    max_speed_mps=_float(values.get("enhanced_max_speed") or values.get("max_speed")),
                    avg_power_w=_float(values.get("avg_power")),
                    elevation_gain_m=_float(values.get("total_ascent")),
                    elevation_loss_m=_float(values.get("total_descent")),
                    calories=_float(values.get("total_calories")),
                    avg_temperature_c=_float(values.get("avg_temperature")),
                    raw=_json_safe(values),
                )
            )

    if not samples:
        warnings.append("No FIT record samples found")
    if not any(sample.latitude is not None and sample.longitude is not None for sample in samples):
        warnings.append("No GPS coordinates found in FIT records")
    if not laps:
        warnings.append("No FIT lap messages found")

    return FitActivityDetail(
        samples=samples,
        laps=laps,
        session=_json_safe(session),
        warnings=warnings,
    )


def _message_values(message) -> dict[str, Any]:
    return {field.name: field.value for field in message}


def _as_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            return value.astimezone(UTC).replace(tzinfo=None)
        return value
    return None


def _float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _semicircle_to_degrees(value: object) -> float | None:
    numeric = _float(value)
    if numeric is None:
        return None
    return numeric * SEMICIRCLE_SCALE


def _json_safe(values: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in values.items():
        if isinstance(value, datetime):
            safe[key] = value.isoformat()
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value
        else:
            safe[key] = str(value)
    return safe
