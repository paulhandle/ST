"""Northern-China climate-aware season detection.

Used to pick which workout templates and what volume ceilings apply to a
given calendar week. The boundaries are tuned to the user's training
geography (Beijing latitude) — not generic global seasons.
"""
from __future__ import annotations

from datetime import date


def season_for(d: date) -> str:
    """Return 'summer' | 'winter' | 'transition' for a date.

    Summer (heat-limited):  June 1 – September 15
    Transition (cool):      September 16 – November 15, March 16 – May 31
    Winter (volume-friendly): November 16 – March 15
    """
    m, day = d.month, d.day
    if m in (6, 7, 8) or (m == 9 and day <= 15):
        return "summer"
    if m in (12, 1, 2) or (m == 11 and day >= 16) or (m == 3 and day <= 15):
        return "winter"
    return "transition"


def season_caps(season: str) -> dict:
    """Return per-season caps the volume curve must respect."""
    if season == "summer":
        return {
            "peak_weekly_km": 127.0,
            "longest_long_run_km": 21.0,
            "include_strength": False,
            "quality_density_max": 3,
        }
    if season == "winter":
        return {
            "peak_weekly_km": 182.0,
            "longest_long_run_km": 26.0,
            "include_strength": True,
            "quality_density_max": 4,
        }
    return {
        "peak_weekly_km": 140.0,
        "longest_long_run_km": 22.0,
        "include_strength": False,
        "quality_density_max": 3,
    }


def dominant_season(start: date, end: date) -> str:
    """Pick the season that best characterizes a date range (for taper windows etc.)."""
    midpoint = date.fromordinal((start.toordinal() + end.toordinal()) // 2)
    return season_for(midpoint)
