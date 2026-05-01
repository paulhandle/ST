from datetime import datetime

from sqlalchemy.orm import Session

from app.devices.coros import CorosAdapter
from app.devices.garmin import GarminAdapter
from app.models import DeviceType, SyncStatus, SyncTask, TrainingPlan


def _adapter_for(device_type: DeviceType):
    if device_type == DeviceType.GARMIN:
        return GarminAdapter()
    if device_type == DeviceType.COROS:
        return CorosAdapter()
    raise ValueError(f"Unsupported device type: {device_type}")


def sync_plan_to_device(db: Session, plan: TrainingPlan, device_type: DeviceType) -> SyncTask:
    adapter = _adapter_for(device_type)
    try:
        result = adapter.sync_plan(plan, plan.sessions)
        task = SyncTask(
            plan_id=plan.id,
            device_type=device_type,
            status=SyncStatus.SUCCESS,
            details=f"{result['message']} remote_plan_id={result['remote_plan_id']}",
            synced_at=datetime.utcnow(),
        )
    except Exception as exc:
        task = SyncTask(
            plan_id=plan.id,
            device_type=device_type,
            status=SyncStatus.FAILED,
            details=str(exc),
            synced_at=None,
        )

    db.add(task)
    db.commit()
    db.refresh(task)
    return task
