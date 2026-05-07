from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ProviderRawRecord


def upsert_provider_raw_records(
    db: Session,
    *,
    athlete_id: int,
    provider: str,
    records: list[dict],
    sync_job_id: int | None = None,
) -> int:
    count = 0
    for item in records:
        record_type = str(item["record_type"])
        provider_record_id = str(item.get("provider_record_id") or record_type)
        payload = item.get("payload", {})
        payload_json = json.dumps(payload, ensure_ascii=False, default=str, sort_keys=True)
        payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

        existing = db.execute(
            select(ProviderRawRecord).where(
                ProviderRawRecord.provider == provider,
                ProviderRawRecord.record_type == record_type,
                ProviderRawRecord.provider_record_id == provider_record_id,
            )
        ).scalar_one_or_none()

        now = datetime.now(UTC)
        if existing is None:
            db.add(
                ProviderRawRecord(
                    athlete_id=athlete_id,
                    sync_job_id=sync_job_id,
                    provider=provider,
                    record_type=record_type,
                    provider_record_id=provider_record_id,
                    endpoint=item.get("endpoint"),
                    payload_hash=payload_hash,
                    payload_json=payload_json,
                    fetched_at=now,
                )
            )
        else:
            existing.athlete_id = athlete_id
            existing.sync_job_id = sync_job_id
            existing.endpoint = item.get("endpoint")
            existing.payload_hash = payload_hash
            existing.payload_json = payload_json
            existing.fetched_at = now
            existing.updated_at = now
        count += 1
    return count
