from uuid import uuid4

from app.devices.base import DeviceSyncAdapter
from app.models import TrainingPlan, TrainingSession


class CorosAdapter(DeviceSyncAdapter):
    def sync_plan(self, plan: TrainingPlan, sessions: list[TrainingSession]) -> dict:
        return {
            "provider": "coros",
            "remote_plan_id": f"coros-{uuid4()}",
            "pushed_sessions": len(sessions),
            "message": f"Mock synced plan {plan.id} to COROS Training Hub.",
        }
