from abc import ABC, abstractmethod

from app.models import TrainingPlan, TrainingSession


class DeviceSyncAdapter(ABC):
    @abstractmethod
    def sync_plan(self, plan: TrainingPlan, sessions: list[TrainingSession]) -> dict:
        raise NotImplementedError
