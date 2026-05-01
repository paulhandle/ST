"""ST default marathon skill.

Tries the LLM-personalized generator first; falls back to the deterministic
rule generator on any error. Both produce the same PlanDraft shape.
"""
from __future__ import annotations

import logging
from statistics import mean

from app.core.context import PlanDraft, SkillContext
from app.kb.running import MARATHON_DISTANCE_KM
from app.models import SportType, TrainingMode
from app.skills.base import SkillManifest

from .code import llm as llm_mod
from .code import rules as rules_mod

log = logging.getLogger(__name__)


class MarathonStDefaultSkill:
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            slug="marathon_st_default",
            name="ST Default Marathon Plan",
            version="0.1.0",
            sport=SportType.MARATHON,
            supported_goals=["finish", "target_time"],
            description=(
                "Periodized base/build/peak/taper marathon plan combining "
                "deterministic rule-based volume curves with optional LLM "
                "personalization."
            ),
            author="ST team",
            tags=["marathon", "hybrid", "base-build-peak"],
            requires_llm=False,
        )

    def applicable(self, ctx: SkillContext) -> tuple[bool, str]:
        if ctx.goal.sport != SportType.MARATHON:
            return False, f"This skill is for marathon, not {ctx.goal.sport.value}."
        if not (8 <= ctx.goal.plan_weeks <= 24):
            return False, f"Plan weeks {ctx.goal.plan_weeks} outside supported 8-24 range."
        return True, ""

    def generate_plan(self, ctx: SkillContext) -> PlanDraft:
        weeks = None
        if ctx.llm_enabled:
            try:
                weeks = llm_mod.generate_weeks(ctx)
                log.info("LLM plan generated successfully: %d weeks", len(weeks))
            except Exception as exc:
                log.warning("LLM plan generation failed (%s); falling back to rules.", exc)
                weeks = None
        if weeks is None:
            weeks = rules_mod.generate_weeks(ctx)

        target_pace = self._target_pace(ctx)
        for week in weeks:
            for workout in week:
                if not workout.steps:
                    workout.steps = rules_mod.steps_for_workout(workout, target_pace)

        return PlanDraft(
            title=rules_mod.plan_title(ctx.goal.target_time_sec),
            mode=TrainingMode.BASE_BUILD_PEAK,
            weeks=weeks,
        )

    def _target_pace(self, ctx: SkillContext) -> float:
        if ctx.goal.target_time_sec is not None:
            return ctx.goal.target_time_sec / MARATHON_DISTANCE_KM
        if ctx.assessment is None:
            return 360.0
        return mean(ctx.assessment.estimated_marathon_time_range_sec) / MARATHON_DISTANCE_KM


skill = MarathonStDefaultSkill()
