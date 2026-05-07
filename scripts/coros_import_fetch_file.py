from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.db import SessionLocal
from app.ingestion.raw_records import upsert_provider_raw_records
from app.ingestion.service import import_provider_history
from app.models import AthleteProfile, ProviderSyncEvent, ProviderSyncJob


def main() -> int:
    parser = argparse.ArgumentParser(description="Import a coros_real_fetch_probe JSON file into the local DB.")
    parser.add_argument("fetch_json", type=Path)
    parser.add_argument("--athlete-id", type=int, default=1)
    args = parser.parse_args()

    payload = json.loads(args.fetch_json.read_text(encoding="utf-8"))
    history = payload["history"]
    _normalize_history_dates(history)
    with SessionLocal() as db:
        athlete = db.get(AthleteProfile, args.athlete_id)
        if athlete is None:
            print(f"Athlete not found: {args.athlete_id}")
            return 2
        job = ProviderSyncJob(
            athlete_id=args.athlete_id,
            provider="coros",
            status="running",
            phase="save",
            message=f"Importing fetched file {args.fetch_json.name}",
            total_count=len(history.get("activities", [])),
            processed_count=len(history.get("activities", [])),
            started_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        result = import_provider_history(
            db=db,
            athlete=athlete,
            provider="coros",
            activities=history.get("activities", []),
            metrics=history.get("metrics", []),
        )
        raw_count = upsert_provider_raw_records(
            db,
            athlete_id=args.athlete_id,
            provider="coros",
            records=history.get("raw_records", []),
            sync_job_id=job.id,
        )
        now = datetime.now(UTC)
        job.status = "succeeded"
        job.phase = "complete"
        job.message = f"Imported fetched file {args.fetch_json.name}"
        job.imported_count = int(result["imported_count"])
        job.updated_count = int(result["updated_count"])
        job.metric_count = int(result["metric_count"])
        job.raw_record_count = raw_count
        job.failed_count = int(history.get("stats", {}).get("failed_count", 0) or 0)
        job.completed_at = now
        job.updated_at = now
        db.add(
            ProviderSyncEvent(
                job_id=job.id,
                level="info",
                phase="complete",
                message=job.message,
                processed_count=job.processed_count,
                total_count=job.total_count,
            )
        )
        db.commit()
        print(
            json.dumps(
                {
                    "job_id": job.id,
                    "imported_count": job.imported_count,
                    "updated_count": job.updated_count,
                    "metric_count": job.metric_count,
                    "raw_record_count": job.raw_record_count,
                    "failed_count": job.failed_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


def _normalize_history_dates(history: dict) -> None:
    for activity in history.get("activities", []):
        if isinstance(activity.get("started_at"), str):
            activity["started_at"] = _parse_datetime(activity["started_at"])
    for metric in history.get("metrics", []):
        if isinstance(metric.get("measured_at"), str):
            metric["measured_at"] = _parse_datetime(metric["measured_at"])


def _parse_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
