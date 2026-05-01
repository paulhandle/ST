from uuid import uuid4

from app.tools.devices.base import DeviceSyncAdapter
from app.models import TrainingPlan, TrainingSession


class GarminAdapter(DeviceSyncAdapter):
    def sync_plan(self, plan: TrainingPlan, sessions: list[TrainingSession]) -> dict:
        return {
            "provider": "garmin",
            "remote_plan_id": f"garmin-{uuid4()}",
            "pushed_sessions": len(sessions),
            "message": f"Mock synced plan {plan.id} to Garmin Connect.",
        }
