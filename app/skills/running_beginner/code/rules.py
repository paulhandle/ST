"""Pure rule-based plan generation for beginner runners.

Input:  SkillContext
Output: PlanDraft

No DB access, no external calls. RPE-only intensity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.context import SkillContext, PlanDraft, WorkoutDraft, StepDraft

from app.core.context import WorkoutDraft, StepDraft, PlanDraft
from app.models import TrainingMode


@dataclass
class PhaseWeek:
    phase: str
    runs: int
    easy_min: int   # easy run duration minutes
    long_min: int   # long run duration minutes (0 = no long run this week)


_PHASE_TEMPLATE: list[PhaseWeek] = [
    # Adaptation (weeks 1-4): 2 runs/week, short sessions
    PhaseWeek("adaptation", 2, 20, 0),
    PhaseWeek("adaptation", 2, 25, 0),
    PhaseWeek("adaptation", 2, 25, 30),
    PhaseWeek("adaptation", 2, 30, 35),
    # Base (weeks 5-10): add 3rd run, slowly grow long run
    PhaseWeek("base", 3, 25, 35),
    PhaseWeek("base", 3, 25, 40),
    PhaseWeek("base", 2, 20, 0),    # recovery week
    PhaseWeek("base", 3, 30, 45),
    PhaseWeek("base", 3, 30, 50),
    PhaseWeek("base", 3, 30, 55),
    # Consolidation (weeks 11-16): longer long runs, light taper at end
    PhaseWeek("consolidation", 3, 30, 60),
    PhaseWeek("consolidation", 3, 35, 70),
    PhaseWeek("consolidation", 2, 25, 0),    # recovery
    PhaseWeek("consolidation", 3, 35, 80),
    PhaseWeek("consolidation", 3, 35, 90),
    PhaseWeek("consolidation", 3, 30, 60),   # taper
]


def _steps(warmup_min: int, main_min: int, cooldown_min: int, desc: str) -> list[StepDraft]:
    return [
        StepDraft(
            step_type="warmup",
            duration_sec=warmup_min * 60,
            target_type="rpe",
            target_min=3, target_max=4,
            notes="Walk or jog easily.",
        ),
        StepDraft(
            step_type="work",
            duration_sec=main_min * 60,
            target_type="rpe",
            target_min=4, target_max=5,
            notes=desc,
        ),
        StepDraft(
            step_type="cooldown",
            duration_sec=cooldown_min * 60,
            target_type="rpe",
            target_min=3, target_max=4,
            notes="Walk and relax.",
        ),
    ]


def _easy_run(week_index: int, weekday: int, duration_min: int) -> WorkoutDraft:
    main = max(5, duration_min - 10)
    return WorkoutDraft(
        week_index=week_index,
        weekday=weekday,
        discipline="run",
        workout_type="easy_run",
        title=f"Easy Run {duration_min} min",
        purpose="Build aerobic routine and running consistency.",
        duration_min=duration_min,
        distance_m=None,
        target_intensity_type="rpe",
        rpe_min=4, rpe_max=5,
        steps=_steps(5, main, 5, "Keep the effort conversational."),
    )


def _long_run(week_index: int, weekday: int, duration_min: int) -> WorkoutDraft:
    main = max(10, duration_min - 10)
    return WorkoutDraft(
        week_index=week_index,
        weekday=weekday,
        discipline="run",
        workout_type="long_run",
        title=f"Long Run {duration_min} min",
        purpose="Build endurance capacity.",
        duration_min=duration_min,
        distance_m=None,
        target_intensity_type="rpe",
        rpe_min=4, rpe_max=5,
        steps=_steps(5, main, 5, "Keep the effort easy; do not chase speed."),
    )


def generate(ctx: "SkillContext") -> PlanDraft:
    from datetime import date as _date

    available_weekdays = sorted(ctx.availability.selected_weekdays or [1, 3, 6])

    race_date = ctx.goal.race_date
    today = ctx.today
    if race_date and race_date > today:
        total_weeks = max(4, min((race_date - today).days // 7, len(_PHASE_TEMPLATE)))
    else:
        total_weeks = 12

    weeks: list[list[WorkoutDraft]] = []

    for wi in range(total_weeks):
        tmpl = _PHASE_TEMPLATE[min(wi, len(_PHASE_TEMPLATE) - 1)]
        week_workouts: list[WorkoutDraft] = []

        n_runs = min(tmpl.runs, len(available_weekdays))
        chosen_days = available_weekdays[:n_runs]

        if tmpl.long_min > 0 and n_runs >= 2:
            long_day = chosen_days[-1]
            easy_days = chosen_days[:-1]
        else:
            long_day = None
            easy_days = chosen_days

        for wd in easy_days:
            week_workouts.append(_easy_run(wi + 1, wd, tmpl.easy_min))

        if long_day is not None:
            week_workouts.append(_long_run(wi + 1, long_day, tmpl.long_min))

        weeks.append(week_workouts)

    return PlanDraft(
        title="Beginner Runner Plan",
        mode=TrainingMode.BASE_BUILD_PEAK,
        weeks=weeks,
        notes="Easy effort first; consistency matters more than pace.",
    )
