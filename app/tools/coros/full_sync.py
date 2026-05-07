from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select

from app.db import SessionLocal
from app.ingestion.activity_details import upsert_fit_activity_detail
from app.ingestion.raw_records import upsert_provider_raw_records
from app.ingestion.service import import_provider_history
from app.models import (
    AthleteActivity,
    DeviceAccount,
    DeviceType,
    ProviderSyncEvent,
    ProviderSyncJob,
)
from app.tools.coros.automation import coros_automation_client
from app.tools.coros.credentials import decrypt_secret


ACTIVE_SYNC_STATUSES = {"queued", "running"}


def run_coros_full_sync_job(job_id: int) -> None:
    with SessionLocal() as db:
        job = db.get(ProviderSyncJob, job_id)
        if job is None:
            return
        account = db.execute(
            select(DeviceAccount)
            .where(
                DeviceAccount.athlete_id == job.athlete_id,
                DeviceAccount.device_type == DeviceType.COROS,
            )
            .order_by(DeviceAccount.id.desc())
            .limit(1)
        ).scalars().first()
        if account is None or account.auth_status != "connected" or not account.encrypted_password:
            _fail_job(db, job, "COROS account not connected")
            return

        try:
            password = decrypt_secret(account.encrypted_password)
        except Exception as exc:
            _fail_job(db, job, f"Could not decrypt COROS credentials: {exc}")
            return

        client = coros_automation_client()
        username = account.username or account.external_user_id
        _update_job(db, job, status="running", phase="login", message="Logging in to COROS", started=True)
        login = client.login(username, password)
        if not login.ok:
            account.last_error = login.message
            _fail_job(db, job, login.message)
            return

        account.last_login_at = datetime.now(UTC)
        account.last_error = None
        _add_event(db, job, level="info", phase="login", message="COROS login succeeded")

        def progress(phase: str | None = None, message: str | None = None, **event: object) -> None:
            phase = str(phase or event.get("phase") or job.phase)
            message = str(message or event.get("message") or phase)
            level = str(event.get("level") or "info")
            processed = _optional_int(event.get("processed"))
            total = _optional_int(event.get("total"))
            _update_job(
                db,
                job,
                status="running",
                phase=phase,
                message=message,
                processed_count=processed,
                total_count=total,
                commit=False,
            )
            _add_event(
                db,
                job,
                level=level,
                phase=phase,
                message=message,
                processed_count=processed,
                total_count=total,
                commit=True,
            )

        try:
            _update_job(db, job, status="running", phase="activity_list", message="Reading COROS history")
            if hasattr(client, "fetch_full_history"):
                history = client.fetch_full_history(username, progress=progress)
            else:
                history = client.fetch_history(username)

            _update_job(db, job, status="running", phase="save", message="Saving imported records")
            result = import_provider_history(
                db=db,
                athlete=job.athlete,
                provider="coros",
                activities=history.get("activities", []),
                metrics=history.get("metrics", []),
            )
            raw_count = upsert_provider_raw_records(
                db,
                athlete_id=job.athlete_id,
                provider="coros",
                records=history.get("raw_records", []),
                sync_job_id=job.id,
            )
            failed_count = int(history.get("stats", {}).get("failed_count", 0) or 0)
            if hasattr(client, "download_activity_fit_export"):
                failed_count += _download_and_store_fit_exports(
                    db=db,
                    job=job,
                    client=client,
                    activities=history.get("activities", []),
                )
            now = datetime.now(UTC)
            job.status = "succeeded"
            job.phase = "complete"
            job.message = "COROS full sync completed"
            job.imported_count = int(result["imported_count"])
            job.updated_count = int(result["updated_count"])
            job.metric_count = int(result["metric_count"])
            job.raw_record_count = raw_count
            job.failed_count = failed_count
            job.completed_at = now
            job.updated_at = now
            account.last_import_at = now
            account.last_error = None
            _add_event(
                db,
                job,
                level="info",
                phase="complete",
                message="COROS full sync completed",
                processed_count=job.processed_count,
                total_count=job.total_count,
                commit=False,
            )
            db.commit()
        except Exception as exc:
            account.last_error = str(exc)
            _fail_job(db, job, str(exc))


def _download_and_store_fit_exports(db, job: ProviderSyncJob, client, activities: list[dict]) -> int:
    failed_count = 0
    total = len(activities)
    _update_job(
        db,
        job,
        status="running",
        phase="activity_fit_exports",
        message="Downloading COROS FIT exports",
        processed_count=0,
        total_count=total,
    )
    for index, item in enumerate(activities, start=1):
        provider_activity_id = str(item.get("provider_activity_id") or "")
        if not provider_activity_id:
            continue
        sport_type = _sport_type_from_payload(item)
        try:
            export = client.download_activity_fit_export(provider_activity_id, sport_type)
            activity = db.execute(
                select(AthleteActivity).where(
                    AthleteActivity.athlete_id == job.athlete_id,
                    AthleteActivity.provider == "coros",
                    AthleteActivity.provider_activity_id == provider_activity_id,
                )
            ).scalar_one()
            upsert_fit_activity_detail(
                db,
                activity=activity,
                data=export["data"],
                file_url=export.get("file_url"),
            )
            _add_event(
                db,
                job,
                level="info",
                phase="activity_fit_exports",
                message=f"Stored COROS FIT export {provider_activity_id}",
                processed_count=index,
                total_count=total,
                commit=False,
            )
            db.commit()
        except Exception as exc:
            failed_count += 1
            _add_event(
                db,
                job,
                level="warning",
                phase="activity_fit_exports",
                message=f"Could not store COROS FIT export {provider_activity_id}: {exc}",
                processed_count=index,
                total_count=total,
                commit=True,
            )
        _update_job(
            db,
            job,
            status="running",
            phase="activity_fit_exports",
            message=f"Processed COROS FIT export {index} of {total}",
            processed_count=index,
            total_count=total,
        )
    return failed_count


def _sport_type_from_payload(item: dict) -> int:
    raw = item.get("raw_payload")
    if isinstance(raw, dict):
        if raw.get("sportType") is not None:
            return int(raw["sportType"])
        summary = raw.get("summary")
        if isinstance(summary, dict) and summary.get("sportType") is not None:
            return int(summary["sportType"])
    sport = str(item.get("sport") or "")
    discipline = str(item.get("discipline") or "")
    if sport == "cycling" or discipline == "ride":
        return 200
    if sport == "swimming" or discipline == "swim":
        return 300
    if sport == "strength" or discipline == "strength":
        return 400
    return 100


def _update_job(
    db,
    job: ProviderSyncJob,
    *,
    status: str | None = None,
    phase: str | None = None,
    message: str | None = None,
    processed_count: int | None = None,
    total_count: int | None = None,
    started: bool = False,
    commit: bool = True,
) -> None:
    now = datetime.now(UTC)
    if status is not None:
        job.status = status
    if phase is not None:
        job.phase = phase
    if message is not None:
        job.message = message
    if processed_count is not None:
        job.processed_count = processed_count
    if total_count is not None:
        job.total_count = total_count
    if started and job.started_at is None:
        job.started_at = now
    job.updated_at = now
    if commit:
        db.commit()


def _add_event(
    db,
    job: ProviderSyncJob,
    *,
    level: str,
    phase: str,
    message: str,
    processed_count: int | None = None,
    total_count: int | None = None,
    commit: bool = True,
) -> None:
    db.add(
        ProviderSyncEvent(
            job_id=job.id,
            level=level,
            phase=phase,
            message=message,
            processed_count=processed_count,
            total_count=total_count,
        )
    )
    if commit:
        db.commit()


def _fail_job(db, job: ProviderSyncJob, message: str) -> None:
    now = datetime.now(UTC)
    job.status = "failed"
    job.phase = "failed"
    job.message = message
    job.error_message = message
    job.completed_at = now
    job.updated_at = now
    _add_event(db, job, level="error", phase="failed", message=message, commit=False)
    db.commit()


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)
