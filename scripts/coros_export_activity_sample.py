from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import BASE_DIR
from app.db import SessionLocal
from app.models import ActivityLap, AthleteActivity


OUT_DIR = BASE_DIR / "var" / "coros_real_sync"


def main() -> int:
    parser = argparse.ArgumentParser(description="Export one stored real COROS activity for manual field review.")
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--provider-activity-id", default="")
    args = parser.parse_args()

    with SessionLocal() as db:
        stmt = select(AthleteActivity).where(
            AthleteActivity.athlete_id == args.athlete_id,
            AthleteActivity.provider == "coros",
            AthleteActivity.raw_payload_json.is_not(None),
            ~AthleteActivity.raw_payload_json.contains("fake_coros"),
        )
        if args.provider_activity_id:
            stmt = stmt.where(AthleteActivity.provider_activity_id == args.provider_activity_id)
        else:
            stmt = stmt.order_by(AthleteActivity.started_at.desc())
        activity = db.execute(stmt.limit(1)).scalar_one_or_none()
        if activity is None:
            print("No matching real COROS activity found.")
            return 1

        laps = db.execute(
            select(ActivityLap).where(ActivityLap.activity_id == activity.id).order_by(ActivityLap.lap_index.asc())
        ).scalars().all()
        payload = {
            "exported_at": datetime.now(UTC).isoformat(),
            "athlete_id": args.athlete_id,
            "activity": {
                "id": activity.id,
                "provider": activity.provider,
                "provider_activity_id": activity.provider_activity_id,
                "sport": activity.sport,
                "discipline": activity.discipline,
                "started_at": activity.started_at.isoformat() if activity.started_at else None,
                "timezone": activity.timezone,
                "duration_sec": activity.duration_sec,
                "moving_duration_sec": activity.moving_duration_sec,
                "distance_m": activity.distance_m,
                "elevation_gain_m": activity.elevation_gain_m,
                "avg_pace_sec_per_km": activity.avg_pace_sec_per_km,
                "avg_hr": activity.avg_hr,
                "max_hr": activity.max_hr,
                "avg_cadence": activity.avg_cadence,
                "avg_power": activity.avg_power,
                "training_load": activity.training_load,
                "perceived_effort": activity.perceived_effort,
                "feedback_text": activity.feedback_text,
                "raw_payload": _decode_json(activity.raw_payload_json),
                "laps": [
                    {
                        "lap_index": lap.lap_index,
                        "duration_sec": lap.duration_sec,
                        "distance_m": lap.distance_m,
                        "avg_pace_sec_per_km": lap.avg_pace_sec_per_km,
                        "avg_hr": lap.avg_hr,
                        "elevation_gain_m": lap.elevation_gain_m,
                    }
                    for lap in laps
                ],
            },
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"activity-sample-{activity.provider_activity_id}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    print(f"Wrote: {output_path}")
    return 0


def _decode_json(raw: str | None) -> object:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


if __name__ == "__main__":
    raise SystemExit(main())
