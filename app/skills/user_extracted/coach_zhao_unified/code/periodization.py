"""Volume curve + phase assignment for the unified methodology.

The historical pattern across both seasons:
  - Long base period (~65 % of plan) at moderate volume with a 3-week recovery
    cycle. Each 4th week dips to ~70 % of the trailing mean.
  - Short specific block (~25 % of plan, 4-5 weeks) where volume jumps
    sharply — 60-100 % above base. This is the methodology's signature shock.
  - Steep taper (last 1-2 weeks): 50 % then 15 % of peak.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeekPlan:
    week_index: int                    # 1-based
    phase: str                         # base | block | taper
    target_km: float
    is_recovery: bool
    quality_count: int                 # 2, 3, or 4
    long_run_role: str                 # long_run_easy | long_run_race_specific | long_run_extended | long_run_taper


def build_volume_curve(
    plan_weeks: int,
    season_caps: dict,
    safe_low_km: float,
    safe_high_km: float,
) -> list[WeekPlan]:
    """Produce one WeekPlan per week respecting season caps and athlete-safe range."""
    base_floor = max(35.0, safe_low_km)
    base_ceiling = min(80.0, max(60.0, safe_high_km))
    peak_target = min(season_caps["peak_weekly_km"], max(110.0, safe_high_km * 1.6))

    base_end = max(4, int(plan_weeks * 0.65))
    block_end = max(base_end + 3, int(plan_weeks * 0.90))
    taper_start = block_end

    weeks: list[WeekPlan] = []
    for i in range(1, plan_weeks + 1):
        if i <= base_end:
            phase = "base"
            progress = i / max(1, base_end)
            raw = base_floor + (base_ceiling - base_floor) * progress
            is_recovery = (i % 4 == 0)
            if is_recovery:
                raw *= 0.7
            quality = 2 if i <= base_end // 2 else 3
            # Long-run progression in base: mostly easy 16K, with race-specific
            # 半马 every ~3 weeks to introduce sustained effort.
            long_run_role = "long_run_race_specific" if i % 3 == 0 else "long_run_easy"
        elif i <= block_end:
            phase = "block"
            progress = (i - base_end) / max(1, block_end - base_end)
            raw = base_ceiling + (peak_target - base_ceiling) * progress
            is_recovery = False
            quality = max(2, season_caps["quality_density_max"] - 1)  # leave 1 easy day in week
            block_weeks_total = block_end - base_end
            block_index = i - base_end
            # Long-run progression peaks late in the block
            if season_caps["longest_long_run_km"] >= 25 and block_index >= max(2, block_weeks_total - 1):
                long_run_role = "long_run_extended"
            elif block_index >= max(1, block_weeks_total // 2):
                long_run_role = "long_run_race_specific"
            else:
                long_run_role = "long_run_easy"
        else:
            phase = "taper"
            taper_index = i - taper_start
            taper_total = plan_weeks - taper_start
            if taper_index == taper_total:
                raw = peak_target * 0.18
                quality = 1
                long_run_role = "long_run_taper"
            else:
                raw = peak_target * 0.55
                quality = 2
                long_run_role = "long_run_easy"
            is_recovery = True
        weeks.append(
            WeekPlan(
                week_index=i,
                phase=phase,
                target_km=round(raw, 1),
                is_recovery=is_recovery,
                quality_count=quality,
                long_run_role=long_run_role,
            )
        )
    return weeks
