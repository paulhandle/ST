from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / ".st_profile.toml"


@dataclass
class AthleteProfileData:
    name: str = "Athlete"
    age: int | None = None
    sex: str | None = None              # male / female / other
    height_cm: float | None = None
    weight_kg: float | None = None
    years_running: int | None = None
    injury_history: str = ""
    avg_sleep_hours: float | None = None
    work_stress: str | None = None      # low / moderate / high
    resting_hr: int | None = None
    last_race_distance: str | None = None   # marathon / half_marathon / 10k / 5k
    last_race_time: str | None = None       # "3:58" or "1:52"
    last_race_date: str | None = None       # "2025-10" or "2024-03-15"
    notes: str = ""


def load_profile(path: Path | None = None) -> AthleteProfileData:
    p = path or PROFILE_PATH
    if not p.exists():
        return AthleteProfileData()
    with open(p, "rb") as f:
        data = tomllib.load(f)
    known = AthleteProfileData.__dataclass_fields__
    return AthleteProfileData(**{k: v for k, v in data.items() if k in known})


def save_profile(profile: AthleteProfileData, path: Path | None = None) -> None:
    p = path or PROFILE_PATH
    lines = ["# PerformanceProtocol Athlete Training Profile\n\n"]
    for key, value in asdict(profile).items():
        if value is None or value == "":
            continue
        if isinstance(value, str):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'{key} = "{escaped}"\n')
        else:
            lines.append(f"{key} = {value}\n")
    p.write_text("".join(lines), encoding="utf-8")


def profile_to_prompt_block(profile: AthleteProfileData) -> str:
    parts: list[str] = []
    if profile.age:
        parts.append(f"Age: {profile.age}")
    if profile.sex:
        parts.append(f"Sex: {profile.sex}")
    if profile.height_cm and profile.weight_kg:
        bmi = profile.weight_kg / (profile.height_cm / 100) ** 2
        parts.append(
            f"Height/Weight: {profile.height_cm:.0f} cm / {profile.weight_kg:.0f} kg  (BMI {bmi:.1f})"
        )
    if profile.years_running:
        parts.append(f"Running experience: {profile.years_running} years")
    if profile.last_race_time and profile.last_race_distance:
        when = f" ({profile.last_race_date})" if profile.last_race_date else ""
        parts.append(f"Most recent race: {profile.last_race_distance} in {profile.last_race_time}{when}")
    if profile.injury_history:
        parts.append(f"Injury history: {profile.injury_history}")
    if profile.avg_sleep_hours:
        parts.append(f"Average sleep: {profile.avg_sleep_hours} h/night")
    if profile.work_stress:
        parts.append(f"Life / work stress: {profile.work_stress}")
    if profile.resting_hr:
        parts.append(f"Resting HR: {profile.resting_hr} bpm")
    if profile.notes:
        parts.append(f"Coach notes: {profile.notes}")
    return "\n".join(f"  - {p}" for p in parts) if parts else "  (no profile on file)"
