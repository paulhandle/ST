from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import (
    ActivityLap,
    AthleteActivity,
    AthleteMetricSnapshot,
    DeviceAccount,
    DeviceType,
    ProviderRawRecord,
    ProviderSyncEvent,
    ProviderSyncJob,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove synthetic COROS rows from the local database.")
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        fake_activity_ids = [
            row[0]
            for row in db.execute(
                select(AthleteActivity.id).where(
                    AthleteActivity.athlete_id == args.athlete_id,
                    AthleteActivity.provider == "coros",
                    AthleteActivity.raw_payload_json.contains("fake_coros"),
                )
            ).all()
        ]
        fake_metric_ids = [
            row[0]
            for row in db.execute(
                select(AthleteMetricSnapshot.id).where(
                    AthleteMetricSnapshot.athlete_id == args.athlete_id,
                    AthleteMetricSnapshot.provider == "coros",
                    AthleteMetricSnapshot.raw_payload_json.contains("fake_coros"),
                )
            ).all()
        ]
        fake_raw_record_ids = [
            row[0]
            for row in db.execute(
                select(ProviderRawRecord.id).where(
                    ProviderRawRecord.athlete_id == args.athlete_id,
                    ProviderRawRecord.provider == "coros",
                    (
                        (ProviderRawRecord.record_type == "fake_history")
                        | (ProviderRawRecord.endpoint == "fake://coros/history")
                        | ProviderRawRecord.payload_json.contains("fake_coros")
                    ),
                )
            ).all()
        ]
        fake_job_ids = _fake_job_ids(db, args.athlete_id, fake_raw_record_ids)
        fake_account_ids = [
            row[0]
            for row in db.execute(
                select(DeviceAccount.id).where(
                    DeviceAccount.athlete_id == args.athlete_id,
                    DeviceAccount.device_type == DeviceType.COROS,
                    (
                        (DeviceAccount.username.like("coros_user_%"))
                        | (DeviceAccount.external_user_id.like("coros_user_%"))
                    ),
                )
            ).all()
        ]

        before = {
            "activities": _count_coros_activities(db, args.athlete_id),
            "fake_activities": len(fake_activity_ids),
            "fake_metrics": len(fake_metric_ids),
            "fake_raw_records": len(fake_raw_record_ids),
            "fake_sync_jobs": len(fake_job_ids),
            "fake_device_accounts": len(fake_account_ids),
        }

        deleted = {
            "activity_laps": 0,
            "activities": 0,
            "metrics": 0,
            "raw_records": 0,
            "sync_events": 0,
            "sync_jobs": 0,
            "device_accounts": 0,
        }
        if not args.dry_run:
            if fake_activity_ids:
                deleted["activity_laps"] = db.execute(
                    delete(ActivityLap).where(ActivityLap.activity_id.in_(fake_activity_ids))
                ).rowcount or 0
                deleted["activities"] = db.execute(
                    delete(AthleteActivity).where(AthleteActivity.id.in_(fake_activity_ids))
                ).rowcount or 0
            if fake_metric_ids:
                deleted["metrics"] = db.execute(
                    delete(AthleteMetricSnapshot).where(AthleteMetricSnapshot.id.in_(fake_metric_ids))
                ).rowcount or 0
            if fake_raw_record_ids:
                deleted["raw_records"] = db.execute(
                    delete(ProviderRawRecord).where(ProviderRawRecord.id.in_(fake_raw_record_ids))
                ).rowcount or 0
            if fake_job_ids:
                deleted["sync_events"] = db.execute(
                    delete(ProviderSyncEvent).where(ProviderSyncEvent.job_id.in_(fake_job_ids))
                ).rowcount or 0
                deleted["sync_jobs"] = db.execute(
                    delete(ProviderSyncJob).where(ProviderSyncJob.id.in_(fake_job_ids))
                ).rowcount or 0
            if fake_account_ids:
                deleted["device_accounts"] = db.execute(
                    delete(DeviceAccount).where(DeviceAccount.id.in_(fake_account_ids))
                ).rowcount or 0
            db.commit()

        after = {
            "activities": _count_coros_activities(db, args.athlete_id),
            "fake_activities": _count_fake_activities(db, args.athlete_id),
            "fake_raw_records": _count_fake_raw_records(db, args.athlete_id),
        }
        summary = {
            "timestamp": datetime.now(UTC).isoformat(),
            "athlete_id": args.athlete_id,
            "dry_run": args.dry_run,
            "before": before,
            "deleted": deleted,
            "after": after,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _fake_job_ids(db, athlete_id: int, fake_raw_record_ids: list[int]) -> list[int]:
    ids = {
        row[0]
        for row in db.execute(
            select(ProviderSyncJob.id)
            .outerjoin(ProviderSyncEvent, ProviderSyncEvent.job_id == ProviderSyncJob.id)
            .where(
                ProviderSyncJob.athlete_id == athlete_id,
                ProviderSyncJob.provider == "coros",
                (
                    ProviderSyncJob.message.contains("fake")
                    | ProviderSyncEvent.message.contains("fake")
                    | ProviderSyncEvent.message.contains("Generated")
                ),
            )
        ).all()
    }
    if fake_raw_record_ids:
        ids.update(
            row[0]
            for row in db.execute(
                select(ProviderRawRecord.sync_job_id).where(
                    ProviderRawRecord.id.in_(fake_raw_record_ids),
                    ProviderRawRecord.sync_job_id.is_not(None),
                )
            ).all()
            if row[0] is not None
        )
    return sorted(ids)


def _count_coros_activities(db, athlete_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(AthleteActivity).where(
            AthleteActivity.athlete_id == athlete_id,
            AthleteActivity.provider == "coros",
        )
    ) or 0


def _count_fake_activities(db, athlete_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(AthleteActivity).where(
            AthleteActivity.athlete_id == athlete_id,
            AthleteActivity.provider == "coros",
            AthleteActivity.raw_payload_json.contains("fake_coros"),
        )
    ) or 0


def _count_fake_raw_records(db, athlete_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(ProviderRawRecord).where(
            ProviderRawRecord.athlete_id == athlete_id,
            ProviderRawRecord.provider == "coros",
            (
                (ProviderRawRecord.record_type == "fake_history")
                | (ProviderRawRecord.endpoint == "fake://coros/history")
                | ProviderRawRecord.payload_json.contains("fake_coros")
            ),
        )
    ) or 0


if __name__ == "__main__":
    raise SystemExit(main())
