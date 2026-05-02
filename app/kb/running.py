"""Running knowledge base — physiological constants and pace helpers.

Skills should import constants from here rather than redefining them.
"""
from __future__ import annotations

sport = "running"

MARATHON_DISTANCE_KM = 42.195
HALF_MARATHON_DISTANCE_KM = 21.0975
TEN_K_DISTANCE_KM = 10.0
FIVE_K_DISTANCE_KM = 5.0


def target_pace_sec_per_km(target_time_sec: int, distance_km: float) -> float:
    return target_time_sec / distance_km


def format_pace(sec_per_km: float) -> str:
    minutes = int(sec_per_km // 60)
    seconds = int(sec_per_km % 60)
    return f"{minutes}:{seconds:02d}"


def format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}:{minutes:02d}"


class RunningKB:
    """Concrete running KB instance for passing into SkillContext."""
    sport = "running"
    marathon_distance_km = MARATHON_DISTANCE_KM
    half_marathon_distance_km = HALF_MARATHON_DISTANCE_KM

    def target_pace_sec_per_km(self, target_time_sec: int, distance_km: float) -> float:
        return target_pace_sec_per_km(target_time_sec, distance_km)

    def format_pace(self, sec_per_km: float) -> str:
        return format_pace(sec_per_km)
