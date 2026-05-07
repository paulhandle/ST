from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.core.config import BASE_DIR
from app.db import SessionLocal
from app.models import AthleteActivity, AthleteMetricSnapshot, ProviderRawRecord, ProviderSyncEvent, ProviderSyncJob


OUT_DIR = BASE_DIR / "var" / "coros_real_sync"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect COROS data stored in the local database.")
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--sample-limit", type=int, default=5)
    args = parser.parse_args()

    with SessionLocal() as db:
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "athlete_id": args.athlete_id,
            "activities": _activities(db, args.athlete_id, args.sample_limit),
            "metrics": _metrics(db, args.athlete_id),
            "raw_records": _raw_records(db, args.athlete_id, args.sample_limit),
            "jobs": _jobs(db, args.athlete_id, args.sample_limit),
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUT_DIR / f"db-inspect-{args.athlete_id}-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}.json"
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print(f"Wrote: {output_path}")
    return 0


def _activities(db, athlete_id: int, limit: int) -> dict:
    count = db.scalar(
        select(func.count()).select_from(AthleteActivity).where(
            AthleteActivity.athlete_id == athlete_id,
            AthleteActivity.provider == "coros",
        )
    )
    sport_counts = db.execute(
        select(AthleteActivity.sport, func.count())
        .where(AthleteActivity.athlete_id == athlete_id, AthleteActivity.provider == "coros")
        .group_by(AthleteActivity.sport)
        .order_by(AthleteActivity.sport.asc())
    ).all()
    samples = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id, AthleteActivity.provider == "coros")
        .order_by(AthleteActivity.started_at.desc())
        .limit(limit)
    ).scalars().all()
    all_ids = db.execute(
        select(AthleteActivity.provider_activity_id, AthleteActivity.raw_payload_json)
        .where(AthleteActivity.athlete_id == athlete_id, AthleteActivity.provider == "coros")
    ).all()
    real_like_count = sum(1 for provider_id, _raw in all_ids if re.fullmatch(r"\d+", provider_id or ""))
    fake_like_count = sum(1 for _provider_id, raw in all_ids if raw and "fake_coros" in raw)
    return {
        "count": count or 0,
        "real_like_count": real_like_count,
        "fake_like_count": fake_like_count,
        "sport_counts": {sport: amount for sport, amount in sport_counts},
        "samples": [
            {
                "id": item.id,
                "provider_activity_id": item.provider_activity_id,
                "sport": item.sport,
                "discipline": item.discipline,
                "started_at": item.started_at,
                "duration_sec": item.duration_sec,
                "distance_m": item.distance_m,
                "avg_hr": item.avg_hr,
                "avg_pace_sec_per_km": item.avg_pace_sec_per_km,
                "raw_payload_json_chars": len(item.raw_payload_json or ""),
            }
            for item in samples
        ],
    }


def _metrics(db, athlete_id: int) -> dict:
    rows = db.execute(
        select(AthleteMetricSnapshot.metric_type, func.count())
        .where(AthleteMetricSnapshot.athlete_id == athlete_id, AthleteMetricSnapshot.provider == "coros")
        .group_by(AthleteMetricSnapshot.metric_type)
        .order_by(AthleteMetricSnapshot.metric_type.asc())
    ).all()
    return {"count_by_type": {metric_type: amount for metric_type, amount in rows}}


def _raw_records(db, athlete_id: int, limit: int) -> dict:
    count = db.scalar(
        select(func.count()).select_from(ProviderRawRecord).where(
            ProviderRawRecord.athlete_id == athlete_id,
            ProviderRawRecord.provider == "coros",
        )
    )
    type_counts = db.execute(
        select(ProviderRawRecord.record_type, func.count())
        .where(ProviderRawRecord.athlete_id == athlete_id, ProviderRawRecord.provider == "coros")
        .group_by(ProviderRawRecord.record_type)
        .order_by(ProviderRawRecord.record_type.asc())
    ).all()
    samples = db.execute(
        select(ProviderRawRecord)
        .where(ProviderRawRecord.athlete_id == athlete_id, ProviderRawRecord.provider == "coros")
        .order_by(ProviderRawRecord.id.desc())
        .limit(limit)
    ).scalars().all()
    return {
        "count": count or 0,
        "count_by_type": {record_type: amount for record_type, amount in type_counts},
        "samples": [
            {
                "id": item.id,
                "sync_job_id": item.sync_job_id,
                "record_type": item.record_type,
                "provider_record_id": item.provider_record_id,
                "endpoint": item.endpoint,
                "payload_hash": item.payload_hash,
                "payload_json_chars": len(item.payload_json or ""),
                "fetched_at": item.fetched_at,
            }
            for item in samples
        ],
    }


def _jobs(db, athlete_id: int, limit: int) -> dict:
    jobs = db.execute(
        select(ProviderSyncJob)
        .where(ProviderSyncJob.athlete_id == athlete_id, ProviderSyncJob.provider == "coros")
        .order_by(ProviderSyncJob.id.desc())
        .limit(limit)
    ).scalars().all()
    return {
        "samples": [
            {
                "id": job.id,
                "status": job.status,
                "phase": job.phase,
                "message": job.message,
                "processed_count": job.processed_count,
                "total_count": job.total_count,
                "imported_count": job.imported_count,
                "updated_count": job.updated_count,
                "metric_count": job.metric_count,
                "raw_record_count": job.raw_record_count,
                "failed_count": job.failed_count,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "events": _events(db, job.id, 3),
            }
            for job in jobs
        ]
    }


def _events(db, job_id: int, limit: int) -> list[dict]:
    events = db.execute(
        select(ProviderSyncEvent)
        .where(ProviderSyncEvent.job_id == job_id)
        .order_by(ProviderSyncEvent.id.desc())
        .limit(limit)
    ).scalars().all()
    return [
        {
            "id": event.id,
            "level": event.level,
            "phase": event.phase,
            "message": event.message,
            "processed_count": event.processed_count,
            "total_count": event.total_count,
            "created_at": event.created_at,
        }
        for event in events
    ]


if __name__ == "__main__":
    raise SystemExit(main())
