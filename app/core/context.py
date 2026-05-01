"""Skill execution context — the immutable data bundle a Skill receives.

A Skill must be a pure function of SkillContext. The platform owns all DB and
external API access; the Skill receives only the snapshot it needs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.models import SportType, TrainingMode


@dataclass(frozen=True)
class GoalSpec:
    sport: SportType
    distance_label: str                # "marathon", "half_marathon", "10k", custom
    distance_m: float | None
    target_time_sec: int | None        # None means finish goal
    race_date: date | None
    plan_weeks: int


@dataclass(frozen=True)
class AthleteSnapshot:
    id: int
    name: str
    age: int | None
    sex: str | None
    height_cm: float | None
    weight_kg: float | None
    years_running: int | None
    injury_history: str
    avg_sleep_hours: float | None
    work_stress: str | None
    resting_hr: int | None
    last_race_distance: str | None
    last_race_time: str | None
    last_race_date: str | None
    notes: str
    profile_block: str = ""            # rendered text for prompts


@dataclass(frozen=True)
class AvailabilityView:
    weekly_training_days: int
    selected_weekdays: list[int]
    preferred_long_run_weekday: int
    unavailable_weekdays: list[int]
    max_weekday_duration_min: int | None
    max_weekend_duration_min: int | None
    strength_training_enabled: bool


@dataclass(frozen=True)
class ActivitySummary:
    started_at: datetime
    duration_sec: int
    distance_m: float
    discipline: str
    avg_pace_sec_per_km: float | None
    avg_hr: float | None
    training_load: float | None
    feedback_text: str | None


@dataclass(frozen=True)
class HistoryView:
    recent_activities: list[ActivitySummary]
    weekly_km_last_8w: list[float]
    recent_long_runs: list[str]        # formatted lines
    latest_metrics: dict[str, float]   # lthr, ltsp, etc.


@dataclass(frozen=True)
class Assessment:
    """Sport-specific readiness/feasibility assessment, pre-computed by KB."""
    overall_score: int
    readiness_level: str
    confidence: str
    safe_weekly_distance_range_km: tuple[float, float]
    long_run_capacity_km: float
    estimated_marathon_time_range_sec: tuple[int, int]
    goal_status: str
    summary: str
    warnings: list[str]
    limiting_factors: list[str]
    raw: dict = field(default_factory=dict)   # full backing dict for legacy access


@dataclass(frozen=True)
class SkillContext:
    athlete: AthleteSnapshot
    goal: GoalSpec
    availability: AvailabilityView
    history: HistoryView
    assessment: Assessment | None
    today: date
    start_date: date
    llm_enabled: bool = True


# ── Plan output (what skills produce) ──────────────────────────────────────────


@dataclass
class StepDraft:
    step_type: str                     # warmup, work, cooldown, recovery
    duration_sec: int
    target_type: str                   # pace_sec_per_km, hr_bpm, rpe
    target_min: float | None
    target_max: float | None
    notes: str | None = None
    distance_m: float | None = None
    repeat_count: int | None = None


@dataclass
class WorkoutDraft:
    week_index: int
    weekday: int                       # 0=Mon .. 6=Sun
    discipline: str
    workout_type: str
    title: str
    purpose: str
    duration_min: int
    distance_m: float | None
    target_intensity_type: str         # "pace" | "hr" | "rpe" | "power"
    target_pace_min_sec_per_km: float | None = None
    target_pace_max_sec_per_km: float | None = None
    target_hr_min: float | None = None
    target_hr_max: float | None = None
    rpe_min: int | None = None
    rpe_max: int | None = None
    adaptation_notes: str = ""
    steps: list[StepDraft] = field(default_factory=list)


@dataclass
class PlanDraft:
    title: str
    mode: TrainingMode
    weeks: list[list[WorkoutDraft]]
    notes: str | None = None


# ── Adjustment signals (used by suggest_adjustment, optional in MVP+1) ─────────


@dataclass(frozen=True)
class Signal:
    kind: str                          # "fatigue" | "pain" | "missed" | "overperform"
    severity: str                      # "low" | "medium" | "high"
    detail: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Adjustment:
    reason: str
    recommendation: str
    effective_start_date: date
    effective_end_date: date
