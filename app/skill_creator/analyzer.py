"""Analyze a structured past-plan extract and surface methodology features.

Input: list of decoded coach-prescribed items (from `extract_past_plans.py`).
Output: a methodology summary covering volume curve, periodization, intensity
distribution, workout-type patterns, and inferred principles.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from statistics import mean, median


# Workout-name → category classifier (Chinese + English heuristics).
# Order matters: more specific patterns first.
_NAME_PATTERNS: list[tuple[str, str]] = [
    (r"恢复|recovery|easy\s*shake", "recovery"),
    (r"半马|half\s*marathon", "race_specific_half"),
    (r"全马|full\s*marathon", "race_specific_full"),
    (r"间歇|interval|x\s*200|x\s*400|x\s*600|x\s*800|x\s*1000|x\s*1500", "intervals"),
    (r"速度|speed|sprint", "speed"),
    (r"节奏|tempo|threshold|阈值", "tempo"),
    (r"长距离|long\s*run|长跑", "long_run"),
    (r"轻松|easy|有氧", "easy"),
    (r"E\d+|R\d+|M\d+|T\d+", "coded"),  # coach short-codes
]


def _classify_name(name: str) -> str:
    if not name:
        return "unknown"
    n = name.lower()
    for pattern, category in _NAME_PATTERNS:
        if re.search(pattern, n):
            return category
    return "other"


@dataclass
class ExerciseSummary:
    sets: int
    target_kind: str
    target_meters: float | None       # parsed from target string when target_kind=="distance"
    target_seconds: int | None        # parsed when target_kind=="duration"
    pace_sec_per_km: float | None     # parsed from intensity
    intensity_pct_lthr: float | None
    rest_seconds: int | None


@dataclass
class WorkoutSummary:
    happen_day: date
    name: str
    category: str
    distance_km: float
    duration_min: int
    training_load: int
    exercises: list[ExerciseSummary]
    intensity_zone: str               # dominant zone: easy / aerobic / threshold / vo2 / mixed


@dataclass
class WeeklySummary:
    iso_year: int
    iso_week: int
    start_date: date
    workouts: list[WorkoutSummary] = field(default_factory=list)

    @property
    def total_km(self) -> float:
        return sum(w.distance_km for w in self.workouts)

    @property
    def total_min(self) -> int:
        return sum(w.duration_min for w in self.workouts)

    @property
    def total_load(self) -> int:
        return sum(w.training_load for w in self.workouts)

    @property
    def quality_count(self) -> int:
        return sum(1 for w in self.workouts if w.intensity_zone in ("threshold", "vo2", "mixed"))


@dataclass
class MethodologyAnalysis:
    label: str
    coach_authors: list[tuple[str, int]]
    date_start: date
    date_end: date
    weekly: list[WeeklySummary]
    total_workouts: int
    workout_categories: dict[str, int]
    intensity_distribution_pct: dict[str, float]    # by time
    volume_curve_km: list[float]                    # one entry per week
    peak_week_km: float
    median_week_km: float
    recovery_week_indices: list[int]                # 0-indexed weeks with reduced load
    taper_week_indices: list[int]
    longest_long_run_km: float
    long_run_progression_km: list[float]            # one max-LR per week
    typical_quality_per_week: float
    typical_sessions_per_week: float
    inferred_principles: list[str]


# ── Per-workout summarization ────────────────────────────────────────────────


_NUM_RE = re.compile(r"(\d+(?:\.\d+)?)")
_PACE_RE = re.compile(r"pace\s+(\d+):(\d+)/km")
_PCT_RE = re.compile(r"(\d+(?:\.\d+)?)%\s*LTHR")


def _parse_target(target_kind: str, target: str) -> tuple[float | None, int | None]:
    if target_kind == "distance":
        m = _NUM_RE.search(target)
        if not m:
            return None, None
        value = float(m.group(1))
        return (value * 1000 if "km" in target else value), None
    if target_kind == "duration":
        if ":" in target:
            mm, ss = target.split(":")
            return None, int(mm) * 60 + int(ss)
        m = _NUM_RE.search(target)
        return None, (int(m.group(1)) if m else None)
    return None, None


def _parse_intensity(intensity: str) -> tuple[float | None, float | None]:
    pace = None
    pct = None
    pm = _PACE_RE.search(intensity)
    if pm:
        pace = int(pm.group(1)) * 60 + int(pm.group(2))
    cm = _PCT_RE.search(intensity)
    if cm:
        pct = float(cm.group(1))
    return pace, pct


def _parse_rest(rest: str) -> int | None:
    if not rest:
        return None
    if ":" in rest:
        m = re.search(r"(\d+):(\d+)", rest)
        if m:
            return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+)\s*s", rest)
    if m:
        return int(m.group(1))
    return None


def _summarize_exercise(ex: dict) -> ExerciseSummary:
    target_meters, target_seconds = _parse_target(ex.get("target_kind", "open"), ex.get("target", ""))
    pace, pct = _parse_intensity(ex.get("intensity", ""))
    return ExerciseSummary(
        sets=ex.get("sets", 1),
        target_kind=ex.get("target_kind", "open"),
        target_meters=target_meters,
        target_seconds=target_seconds,
        pace_sec_per_km=pace,
        intensity_pct_lthr=pct,
        rest_seconds=_parse_rest(ex.get("rest", "")),
    )


def _intensity_zone(pct: float | None) -> str:
    if pct is None:
        return "unspecified"
    if pct < 75:
        return "easy"
    if pct < 88:
        return "aerobic"
    if pct < 96:
        return "threshold"
    return "vo2"


def _classify_workout_intensity(exercises: list[ExerciseSummary]) -> str:
    """Pick a single dominant intensity zone for the whole workout."""
    pcts = [e.intensity_pct_lthr for e in exercises if e.intensity_pct_lthr is not None]
    if not pcts:
        return "unspecified"
    zones = {_intensity_zone(p) for p in pcts}
    if zones == {"easy"} or zones == {"aerobic"} or zones == {"easy", "aerobic"}:
        return "easy" if "easy" in zones and "aerobic" not in zones else "aerobic"
    if "vo2" in zones and "threshold" in zones:
        return "mixed"
    if "vo2" in zones:
        return "vo2"
    if "threshold" in zones:
        return "threshold"
    if "aerobic" in zones:
        return "aerobic"
    return "easy"


def _summarize_workout(item: dict) -> WorkoutSummary:
    program = item["program"]
    exercises = [_summarize_exercise(ex) for ex in program.get("exercises", [])]
    happen_day_str = item.get("happen_day")
    happen_day = date.fromisoformat(happen_day_str) if happen_day_str else date.today()
    return WorkoutSummary(
        happen_day=happen_day,
        name=program.get("name", ""),
        category=_classify_name(program.get("name", "")),
        distance_km=program.get("distance_m", 0) / 1000,
        duration_min=int(program.get("duration_sec", 0) // 60),
        training_load=program.get("training_load", 0),
        exercises=exercises,
        intensity_zone=_classify_workout_intensity(exercises),
    )


# ── Weekly aggregation + methodology inference ───────────────────────────────


def analyze(label: str, coach_items: list[dict]) -> MethodologyAnalysis:
    workouts = [_summarize_workout(it) for it in coach_items if it.get("happen_day") and it.get("program")]
    workouts.sort(key=lambda w: w.happen_day)

    if not workouts:
        raise ValueError("no datable coach-prescribed workouts to analyze")

    by_week: dict[tuple[int, int], WeeklySummary] = {}
    for w in workouts:
        iso_year, iso_week, _ = w.happen_day.isocalendar()
        key = (iso_year, iso_week)
        if key not in by_week:
            by_week[key] = WeeklySummary(iso_year=iso_year, iso_week=iso_week, start_date=w.happen_day)
        by_week[key].workouts.append(w)
        if w.happen_day < by_week[key].start_date:
            by_week[key].start_date = w.happen_day

    weekly = [by_week[k] for k in sorted(by_week.keys())]

    # Volume curve
    volume_curve = [round(wk.total_km, 1) for wk in weekly]
    peak = max(volume_curve)
    med = median(volume_curve)

    # Recovery weeks: <= 70% of preceding 3-week median
    recovery_indices: list[int] = []
    for i, km in enumerate(volume_curve):
        if i < 3:
            continue
        ref = median(volume_curve[max(0, i - 3): i])
        if ref > 0 and km <= 0.75 * ref:
            recovery_indices.append(i)

    # Taper weeks: last 1-3 weeks where volume < 50% of peak
    taper_indices: list[int] = []
    for i in range(max(0, len(volume_curve) - 3), len(volume_curve)):
        if volume_curve[i] < 0.5 * peak:
            taper_indices.append(i)

    # Long-run progression (longest workout per week)
    long_run_progression = [
        round(max((w.distance_km for w in wk.workouts), default=0), 1) for wk in weekly
    ]

    # Workout categories (count)
    cat_counter: Counter = Counter(w.category for w in workouts)

    # Intensity distribution by *time* (uses workout duration as weight)
    minutes_by_zone: dict[str, float] = defaultdict(float)
    total_minutes = 0
    for w in workouts:
        # Distribute the workout minutes across its exercises by zone
        zone_mins = _distribute_minutes_to_zones(w)
        for zone, mins in zone_mins.items():
            minutes_by_zone[zone] += mins
            total_minutes += mins

    intensity_pct = (
        {zone: round(mins / total_minutes * 100, 1) for zone, mins in minutes_by_zone.items()}
        if total_minutes > 0 else {}
    )

    # Quality sessions per week
    quality_per_week = mean(wk.quality_count for wk in weekly) if weekly else 0
    sessions_per_week = mean(len(wk.workouts) for wk in weekly) if weekly else 0

    # Author breakdown
    authors_counter: Counter = Counter(it["program"].get("author", "") for it in coach_items if it.get("program"))

    # Inferred principles
    principles = _infer_principles(intensity_pct, cat_counter, recovery_indices, taper_indices, peak, med)

    return MethodologyAnalysis(
        label=label,
        coach_authors=authors_counter.most_common(),
        date_start=workouts[0].happen_day,
        date_end=workouts[-1].happen_day,
        weekly=weekly,
        total_workouts=len(workouts),
        workout_categories=dict(cat_counter),
        intensity_distribution_pct=intensity_pct,
        volume_curve_km=volume_curve,
        peak_week_km=peak,
        median_week_km=med,
        recovery_week_indices=recovery_indices,
        taper_week_indices=taper_indices,
        longest_long_run_km=max(long_run_progression),
        long_run_progression_km=long_run_progression,
        typical_quality_per_week=round(quality_per_week, 1),
        typical_sessions_per_week=round(sessions_per_week, 1),
        inferred_principles=principles,
    )


def _distribute_minutes_to_zones(workout: WorkoutSummary) -> dict[str, float]:
    """Allocate workout minutes across HR zones using exercise targets when available."""
    out: dict[str, float] = defaultdict(float)
    total_target_seconds = 0
    per_ex: list[tuple[str, float]] = []
    for ex in workout.exercises:
        zone = _intensity_zone(ex.intensity_pct_lthr)
        # Estimate exercise time
        ex_seconds = 0
        if ex.target_seconds:
            ex_seconds = ex.target_seconds * (ex.sets or 1)
        elif ex.target_meters and ex.pace_sec_per_km:
            ex_seconds = int(ex.target_meters / 1000 * ex.pace_sec_per_km) * (ex.sets or 1)
        if ex.rest_seconds:
            ex_seconds += ex.rest_seconds * (ex.sets or 1)
        per_ex.append((zone, ex_seconds))
        total_target_seconds += ex_seconds

    if total_target_seconds <= 0 or workout.duration_min <= 0:
        # Fall back: assign whole workout to dominant zone
        out[workout.intensity_zone] += workout.duration_min
        return out

    factor = (workout.duration_min * 60) / total_target_seconds
    for zone, sec in per_ex:
        out[zone] += (sec * factor) / 60
    return out


def _infer_principles(
    intensity_pct: dict[str, float],
    categories: Counter,
    recovery_indices: list[int],
    taper_indices: list[int],
    peak_km: float,
    median_km: float,
) -> list[str]:
    out: list[str] = []
    easy_pct = intensity_pct.get("easy", 0) + intensity_pct.get("aerobic", 0)
    quality_pct = intensity_pct.get("threshold", 0) + intensity_pct.get("vo2", 0) + intensity_pct.get("mixed", 0)

    if easy_pct >= 75 and quality_pct <= 25 and quality_pct > 0:
        out.append(f"polarized-style 80/20 distribution (easy {easy_pct:.0f}% / quality {quality_pct:.0f}%)")
    elif easy_pct >= 60 and quality_pct >= 25:
        out.append(f"pyramidal distribution (easy {easy_pct:.0f}% / quality {quality_pct:.0f}%)")
    elif quality_pct >= 35:
        out.append(f"threshold-heavy distribution (quality {quality_pct:.0f}%)")

    if recovery_indices:
        gaps = [recovery_indices[i] - recovery_indices[i - 1] for i in range(1, len(recovery_indices))]
        if gaps and round(mean(gaps)) in (3, 4):
            out.append(f"recovery week every ~{round(mean(gaps))} weeks")
        else:
            out.append(f"{len(recovery_indices)} recovery weeks detected (irregular)")

    if taper_indices:
        out.append(f"taper detected in last {len(taper_indices)} week(s) — volume cut to <50% of peak")

    if "long_run" in categories:
        out.append(f"long run featured ({categories['long_run']} sessions)")
    if categories.get("intervals", 0) >= 5:
        out.append(f"interval/track work prominent ({categories['intervals']} sessions)")
    if categories.get("tempo", 0) >= 3:
        out.append(f"tempo/threshold sessions present ({categories['tempo']} sessions)")
    if "race_specific_half" in categories or "race_specific_full" in categories:
        out.append("race-specific simulation workouts included")

    if peak_km > 1.5 * median_km:
        out.append(f"strong volume build (peak {peak_km:.0f} km vs median {median_km:.0f} km)")

    return out


# ── Markdown report ──────────────────────────────────────────────────────────


def render_markdown(analysis: MethodologyAnalysis) -> str:
    lines = [f"# Methodology Analysis — {analysis.label}", ""]
    lines.append(f"**Date range**: {analysis.date_start.isoformat()} → {analysis.date_end.isoformat()}")
    lines.append(f"**Coaches**: " + ", ".join(f"{n} ({c})" for n, c in analysis.coach_authors))
    lines.append(f"**Total workouts**: {analysis.total_workouts} across {len(analysis.weekly)} weeks")
    lines.append("")

    lines.append("## Inferred principles")
    for p in analysis.inferred_principles:
        lines.append(f"- {p}")
    lines.append("")

    lines.append("## Volume profile")
    lines.append(f"- Peak weekly volume: **{analysis.peak_week_km:.1f} km**")
    lines.append(f"- Median weekly volume: {analysis.median_week_km:.1f} km")
    lines.append(f"- Longest long run: **{analysis.longest_long_run_km:.1f} km**")
    lines.append(f"- Typical sessions/week: {analysis.typical_sessions_per_week}")
    lines.append(f"- Typical quality sessions/week: {analysis.typical_quality_per_week}")
    if analysis.recovery_week_indices:
        weeks_str = ", ".join(f"W{i + 1}" for i in analysis.recovery_week_indices)
        lines.append(f"- Recovery weeks (≤75 % of 3-wk median): {weeks_str}")
    if analysis.taper_week_indices:
        weeks_str = ", ".join(f"W{i + 1}" for i in analysis.taper_week_indices)
        lines.append(f"- Taper weeks (<50 % of peak): {weeks_str}")
    lines.append("")

    lines.append("## Intensity distribution (by minutes)")
    for zone, pct in sorted(analysis.intensity_distribution_pct.items(), key=lambda x: -x[1]):
        lines.append(f"- {zone:<12} {pct:5.1f}%")
    lines.append("")

    lines.append("## Workout-type breakdown")
    for cat, count in sorted(analysis.workout_categories.items(), key=lambda x: -x[1]):
        lines.append(f"- {cat:<22} {count:>3}")
    lines.append("")

    lines.append("## Weekly volume curve")
    lines.append("```")
    bar_max = 40
    for i, (km, lr) in enumerate(zip(analysis.volume_curve_km, analysis.long_run_progression_km)):
        bar_len = int(km / max(analysis.peak_week_km, 1) * bar_max)
        marks: list[str] = []
        if i in analysis.recovery_week_indices:
            marks.append("rec")
        if i in analysis.taper_week_indices:
            marks.append("taper")
        flag = f"  ({', '.join(marks)})" if marks else ""
        lines.append(f"W{i + 1:02d} {km:5.1f} km {'█' * bar_len:<{bar_max}}  long {lr:5.1f}{flag}")
    lines.append("```")
    lines.append("")

    return "\n".join(lines)
