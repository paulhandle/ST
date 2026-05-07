from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.ingestion.activity_details import upsert_fit_activity_detail
from app.models import AthleteActivity


def main() -> int:
    parser = argparse.ArgumentParser(description="Import one COROS FIT export into activity detail tables.")
    parser.add_argument("fit_file", type=Path)
    parser.add_argument("--athlete-id", type=int, default=1)
    parser.add_argument("--provider-activity-id", required=True)
    args = parser.parse_args()

    if not args.fit_file.exists():
        print(f"FIT file not found: {args.fit_file}")
        return 2

    with SessionLocal() as db:
        activity = db.execute(
            select(AthleteActivity).where(
                AthleteActivity.athlete_id == args.athlete_id,
                AthleteActivity.provider == "coros",
                AthleteActivity.provider_activity_id == args.provider_activity_id,
            )
        ).scalar_one_or_none()
        if activity is None:
            print(
                f"Activity not found: athlete_id={args.athlete_id} "
                f"provider_activity_id={args.provider_activity_id}"
            )
            return 3
        export = upsert_fit_activity_detail(
            db,
            activity=activity,
            data=args.fit_file.read_bytes(),
            file_url=None,
        )
        db.commit()
        print(
            json.dumps(
                {
                    "activity_id": activity.id,
                    "provider_activity_id": activity.provider_activity_id,
                    "source_format": export.source_format,
                    "file_size_bytes": export.file_size_bytes,
                    "sample_count": export.sample_count,
                    "lap_count": export.lap_count,
                    "payload_hash": export.payload_hash,
                    "warnings": json.loads(export.warnings_json or "[]"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
