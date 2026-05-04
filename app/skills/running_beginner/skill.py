"""running_beginner Skill — export `skill` instance for load_skill()."""
from __future__ import annotations

from pathlib import Path

import yaml

from app.skills.base import SkillManifest
from app.models import SportType
from app.core.context import SkillContext, PlanDraft

from .code.rules import generate

_SPEC_PATH = Path(__file__).parent / "spec.yaml"
_MAX_AVG_WEEKLY_KM = 40.0  # users above this should use a more advanced skill


def _build_manifest() -> SkillManifest:
    data = yaml.safe_load(_SPEC_PATH.read_text(encoding="utf-8")) or {}
    return SkillManifest(
        slug=data.get("slug", "running_beginner"),
        name=str(data.get("name", "Beginner Runner Plan")),
        version=str(data.get("version", "1.0")),
        sport=SportType(data.get("sport", "marathon")),
        supported_goals=list(data.get("supported_goals", ["finish"])),
        description=str(data.get("description", "")),
        author=str(data.get("author", "")),
        tags=list(data.get("tags", [])),
        requires_llm=False,
    )


class RunningBeginnerSkill:
    def __init__(self) -> None:
        self._manifest = _build_manifest()

    @property
    def manifest(self) -> SkillManifest:
        return self._manifest

    def applicable(self, ctx: SkillContext) -> tuple[bool, str]:
        weekly_kms = ctx.history.weekly_km_last_8w or []
        avg = sum(weekly_kms) / len(weekly_kms) if weekly_kms else 0.0
        if avg > _MAX_AVG_WEEKLY_KM:
            return False, (
                f"Average weekly mileage {avg:.0f} km exceeds the beginner plan limit "
                f"of {_MAX_AVG_WEEKLY_KM:.0f} km. Choose a more advanced methodology."
            )
        return True, ""

    def generate_plan(self, ctx: SkillContext) -> PlanDraft:
        return generate(ctx)

    def suggest_adjustment(self, ctx: SkillContext, signals: list) -> None:
        return None


skill = RunningBeginnerSkill()
