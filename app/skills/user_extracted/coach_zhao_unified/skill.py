"""coach_zhao_unified: marathon skill distilled from real coach plans.

Methodology overview (see skill.md for the full description):

1. Northern-China seasonal adaptation (summer vs winter caps + workouts).
2. Long base period at moderate volume; short specific block with sharp ramp;
   steep taper at the end.
3. Long-LSD de-emphasized (cap 21–26 km). Frequency over volume.
4. Quality is sustained-tempo + strides, not classic VO2max intervals.
5. Adherence rules: completion > pace, same-day execution, cadence preservation.
"""
from __future__ import annotations

import logging
import random
from datetime import date, timedelta

from app.core.context import PlanDraft, SkillContext, WorkoutDraft
from app.models import SportType, TrainingMode
from app.skills.base import SkillManifest

from .code import periodization, render, seasonal, templates

log = logging.getLogger(__name__)


class CoachZhaoUnifiedSkill:
    @property
    def manifest(self) -> SkillManifest:
        return SkillManifest(
            slug="coach_zhao_unified",
            name="Coach Zhao Unified Marathon Methodology",
            version="0.1.0",
            sport=SportType.MARATHON,
            supported_goals=["finish", "target_time"],
            description=(
                "Distilled from two complete coach-prescribed marathon programs. "
                "One unified philosophy with summer / winter strategy adaptation "
                "for Northern-China climate. Working-professional friendly: short "
                "sessions, capped long runs, tempo + strides instead of intervals."
            ),
            author="赵可 (extracted by PerformanceProtocol)",
            tags=[
                "marathon",
                "seasonal",
                "northern-china",
                "low-LSD",
                "working-professional",
                "tempo-and-strides",
                "completion-first",
            ],
            requires_llm=False,
        )

    def applicable(self, ctx: SkillContext) -> tuple[bool, str]:
        if ctx.goal.sport != SportType.MARATHON:
            return False, f"This skill is for marathon, not {ctx.goal.sport.value}."
        if not (12 <= ctx.goal.plan_weeks <= 24):
            return False, f"Plan weeks {ctx.goal.plan_weeks} outside supported 12–24 range."
        return True, ""

    def generate_plan(self, ctx: SkillContext) -> PlanDraft:
        rng = random.Random(ctx.athlete.id * 31 + ctx.goal.plan_weeks)
        library = templates.load_library()

        # Pick season caps based on the dominant season of the plan body
        body_start = ctx.start_date
        body_end = ctx.start_date + timedelta(weeks=ctx.goal.plan_weeks)
        plan_season = seasonal.dominant_season(body_start, body_end)
        caps = seasonal.season_caps(plan_season)

        # Honour athlete's safe range from the assessment
        safe_low = ctx.assessment.safe_weekly_distance_range_km[0] if ctx.assessment else 35.0
        safe_high = ctx.assessment.safe_weekly_distance_range_km[1] if ctx.assessment else 70.0

        # Volume curve + phase tags per week
        weeks = periodization.build_volume_curve(
            plan_weeks=ctx.goal.plan_weeks,
            season_caps=caps,
            safe_low_km=safe_low,
            safe_high_km=safe_high,
        )

        selected_weekdays = sorted(set(ctx.availability.selected_weekdays))
        long_run_weekday = (
            ctx.availability.preferred_long_run_weekday
            if ctx.availability.preferred_long_run_weekday in selected_weekdays
            else selected_weekdays[-1]
        )

        plan_weeks_out: list[list[WorkoutDraft]] = []
        for wp in weeks:
            week_date = ctx.start_date + timedelta(weeks=wp.week_index - 1)
            week_season = seasonal.season_for(week_date)
            week_workouts = self._build_week(
                ctx=ctx,
                library=library,
                week_plan=wp,
                week_season=week_season,
                selected_weekdays=selected_weekdays,
                long_run_weekday=long_run_weekday,
                rng=rng,
                include_strength=caps["include_strength"]
                                 and ctx.availability.strength_training_enabled
                                 and week_season == "winter",
            )
            plan_weeks_out.append(week_workouts)

        title = self._title(ctx)
        return PlanDraft(
            title=title,
            mode=TrainingMode.PYRAMIDAL if plan_season == "winter" else TrainingMode.POLARIZED,
            weeks=plan_weeks_out,
            notes=(
                "Extracted from real coach methodology. Adherence rules: "
                "complete > pace; do today's prescription today; "
                "preserve cadence during recovery jogs."
            ),
        )

    # ── per-week build ────────────────────────────────────────────────────────

    def _build_week(
        self,
        *,
        ctx: SkillContext,
        library: list[dict],
        week_plan: periodization.WeekPlan,
        week_season: str,
        selected_weekdays: list[int],
        long_run_weekday: int,
        rng: random.Random,
        include_strength: bool,
    ) -> list[WorkoutDraft]:
        # Decide slot roles for the week
        non_long_days = [d for d in selected_weekdays if d != long_run_weekday]

        # Allocate quality slots first (spread, not back-to-back)
        quality_slots = self._spread_quality(non_long_days, week_plan.quality_count)
        easy_slots = [d for d in non_long_days if d not in quality_slots]
        strength_day: int | None = None
        if include_strength and easy_slots:
            strength_day = easy_slots[-1]

        rendered: list[WorkoutDraft] = []
        used_names: set[str] = set()

        # Long run
        long_role = week_plan.long_run_role
        if week_plan.phase == "taper" and week_plan.long_run_role == "long_run_taper":
            long_template = templates.pick(library, "recovery", season=week_season, rng=rng)
        else:
            long_template = templates.pick(
                library, long_role, season=week_season, rng=rng, exclude_names=used_names
            )
            if long_template is None and long_role == "long_run_extended":
                long_template = templates.pick(library, "long_run_race_specific", season=week_season, rng=rng)
            if long_template is None:
                long_template = templates.pick(library, "long_run_easy", season=week_season, rng=rng)
        if long_template:
            used_names.add(long_template["name"])
            rendered.append(render.render_workout(ctx, long_template, week_plan.week_index, long_run_weekday, role_override=long_role))

        # Quality sessions
        for day in quality_slots:
            role = self._quality_role_for(week_plan.phase, week_season, rng)
            qt = templates.pick(library, role, season=week_season, rng=rng, exclude_names=used_names)
            if qt is None:
                qt = templates.pick(library, "speed_alactic_strides", season=week_season, rng=rng)
            if qt:
                used_names.add(qt["name"])
                rendered.append(render.render_workout(ctx, qt, week_plan.week_index, day))

        # Easy aerobic on remaining days. In specific block, the methodology
        # repeats long-style runs across multiple days to drive weekly volume up.
        for day in easy_slots:
            if day == strength_day:
                continue
            if week_plan.phase == "block":
                # Block weeks pile on volume by using long-easy templates instead of short easy
                t = templates.pick(library, "long_run_easy", season=week_season, rng=rng)
                role_override = "long_run_easy"
            else:
                role = "aerobic_base" if rng.random() < 0.4 else "easy_aerobic"
                t = templates.pick(library, role, season=week_season, rng=rng)
                role_override = "easy_aerobic"
            if t is None:
                t = templates.pick(library, "long_run_easy", season=week_season, rng=rng)
                role_override = "easy_aerobic"
            if t:
                rendered.append(render.render_workout(ctx, t, week_plan.week_index, day, role_override=role_override))

        # Strength
        if strength_day is not None:
            t = templates.pick(library, "strength")
            if t:
                rendered.append(render.render_workout(ctx, t, week_plan.week_index, strength_day))

        rendered.sort(key=lambda w: w.weekday)
        return rendered

    @staticmethod
    def _spread_quality(days: list[int], count: int) -> list[int]:
        if count <= 0 or not days:
            return []
        if count >= len(days):
            return list(days)
        if count == 1:
            return [days[len(days) // 2]]
        if count == 2:
            return [days[0], days[-1]]
        # Evenly spaced indices
        step = (len(days) - 1) / (count - 1)
        idxs = [int(round(i * step)) for i in range(count)]
        return [days[i] for i in sorted(set(idxs))]

    @staticmethod
    def _quality_role_for(phase: str, season: str, rng: random.Random) -> str:
        if phase == "base":
            options = ["speed_alactic_strides", "sustained_tempo_strides"]
        elif phase == "block":
            options = ["tempo_combo", "speed_alactic_strides", "sustained_tempo_strides"]
        else:
            options = ["sustained_tempo_strides"]
        if season == "winter" and "tempo_combo" not in options:
            options.append("tempo_combo")
        return rng.choice(options)

    @staticmethod
    def _title(ctx: SkillContext) -> str:
        if ctx.goal.target_time_sec:
            hours = ctx.goal.target_time_sec // 3600
            minutes = (ctx.goal.target_time_sec % 3600) // 60
            return f"赵可方法论 全马 {hours}:{minutes:02d} 计划"
        return "赵可方法论 全马完赛计划"


skill = CoachZhaoUnifiedSkill()
