from __future__ import annotations

import json
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.coros.automation import coros_automation_client
from app.coros.credentials import decrypt_secret
from app.models import (
    DeviceAccount,
    ProviderSyncRecord,
    StructuredWorkout,
    SyncStatus,
    TrainingPlan,
    WorkoutStatus,
)


def sync_confirmed_plan_to_coros(db: Session, plan: TrainingPlan, account: DeviceAccount) -> dict:
    client = coros_automation_client()
    password = decrypt_secret(account.encrypted_password or "")
    login = client.login(account.username or account.external_user_id, password)
    if not login.ok:
        account.auth_status = "failed"
        account.last_error = login.message
        db.commit()
        return {"records": [], "synced_count": 0, "failed_count": 1}

    workouts = db.execute(
        select(StructuredWorkout)
        .where(StructuredWorkout.plan_id == plan.id)
        .where(StructuredWorkout.scheduled_date >= date.today())
        .where(StructuredWorkout.status.in_([WorkoutStatus.CONFIRMED, WorkoutStatus.SYNCED]))
        .options(selectinload(StructuredWorkout.steps))
        .order_by(StructuredWorkout.scheduled_date.asc())
    ).scalars().all()

    payloads = [_workout_payload(workout) for workout in workouts]
    results = client.sync_workouts(account.username or account.external_user_id, payloads)
    result_by_id = {item["local_workout_id"]: item for item in results}
    records: list[ProviderSyncRecord] = []

    for workout in workouts:
        result = result_by_id.get(workout.id)
        if result is None:
            record = ProviderSyncRecord(
                athlete_id=plan.athlete_id,
                plan_id=plan.id,
                workout_id=workout.id,
                provider="coros",
                sync_status=SyncStatus.FAILED,
                error_message="Fake COROS sync did not return a result.",
            )
        else:
            record = ProviderSyncRecord(
                athlete_id=plan.athlete_id,
                plan_id=plan.id,
                workout_id=workout.id,
                provider="coros",
                provider_workout_id=result["provider_workout_id"],
                provider_calendar_item_id=result["provider_calendar_item_id"],
                sync_status=SyncStatus.SUCCESS,
                synced_at=datetime.utcnow(),
                raw_payload_json=json.dumps(result.get("raw_payload", result), ensure_ascii=False, default=str),
            )
            workout.status = WorkoutStatus.SYNCED
        db.add(record)
        records.append(record)

    account.auth_status = "connected"
    account.last_login_at = datetime.utcnow()
    account.last_sync_at = datetime.utcnow()
    account.last_error = None
    db.commit()
    for record in records:
        db.refresh(record)

    synced_count = len([record for record in records if record.sync_status == SyncStatus.SUCCESS])
    failed_count = len(records) - synced_count
    return {"records": records, "synced_count": synced_count, "failed_count": failed_count}


def _workout_payload(workout: StructuredWorkout) -> dict:
    return {
        "id": workout.id,
        "scheduled_date": workout.scheduled_date.isoformat(),
        "title": workout.title,
        "workout_type": workout.workout_type,
        "duration_min": workout.duration_min,
        "distance_m": workout.distance_m,
        "steps": [
            {
                "step_type": step.step_type,
                "duration_sec": step.duration_sec,
                "distance_m": step.distance_m,
                "target_type": step.target_type,
                "target_min": step.target_min,
                "target_max": step.target_max,
                "repeat_count": step.repeat_count,
                "notes": step.notes,
            }
            for step in workout.steps
        ],
    }
