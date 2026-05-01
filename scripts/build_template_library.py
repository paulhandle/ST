#!/usr/bin/env python3
"""Build the workout template library for the coach_zhao_unified skill.

Walks both extracted past-plan windows, deduplicates by exercise structure
(NOT by the athlete's absolute pace), classifies each unique template by
role + season presence, and writes a portable JSON library to
app/skills/user_extracted/coach_zhao_unified/data/workout_templates.json.

Intensity is normalized to %LTHR so the templates can be reused for any
athlete; absolute paces are recomputed at plan-generation time.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTED = ROOT / "var" / "extracted_plans"
SKILL_DIR = ROOT / "app" / "skills" / "user_extracted" / "coach_zhao_unified"
DATA_DIR = SKILL_DIR / "data"

WINDOWS = ("summer_2025", "winter_2025_2026")


def _load_window(label: str) -> list[dict]:
    path = EXTRACTED / f"{label}.json"
    return json.loads(path.read_text(encoding="utf-8"))["coach_items"]


def _normalize_exercise(ex: dict) -> dict:
    """Convert one exercise into a portable form (no absolute paces)."""
    raw = ex.get("raw", {})
    pct_milli = raw.get("intensityPercent") or 0
    pct = round(pct_milli / 1000, 0) if pct_milli else None
    target_type = raw.get("targetType")
    target_value = raw.get("targetValue") or 0
    target_kind = "open"
    target = None
    if target_type == 5:
        target_kind = "distance_m"
        target = round(target_value / 100, 0)
    elif target_type == 2:
        target_kind = "duration_sec"
        target = int(target_value)
    rest_type = raw.get("restType")
    rest_value = raw.get("restValue") or 0
    rest = None
    if rest_type in (3, 0) and rest_value:
        rest = {"type": "duration_sec", "value": int(rest_value)}
    return {
        "sets": ex.get("sets", 1),
        "target_kind": target_kind,
        "target_value": target,
        "intensity_pct_lthr": pct,
        "rest": rest,
    }


def _signature(name: str, exercises: list[dict]) -> str:
    """Stable hash of the workout structure for dedup."""
    parts = [name]
    for ex in exercises:
        parts.append(
            f"{ex['sets']}/{ex['target_kind']}:{ex['target_value']}/{ex['intensity_pct_lthr']}/{ex['rest']}"
        )
    return "|".join(parts)


def _classify_role(name: str, distance_m: float, duration_sec: int, exercises: list[dict]) -> str:
    """Assign a role tag used by the planner to slot workouts into a week."""
    n = name.lower()
    km = distance_m / 1000

    if re.search(r"恢复|recovery", n):
        return "recovery"
    if re.search(r"力量|strength", n):
        return "strength"
    if re.search(r"半马|半马训练|race|race-specific|race_specific", n) or km >= 20:
        if km >= 25:
            return "long_run_extended"   # winter-only 26K-style
        return "long_run_race_specific"  # 半马 or 2K+8K+10K progressive 20K
    if re.search(r"16k|轻松跑.*1[5-9]|long\s*run", n) or (km >= 14 and not _has_quality(exercises)):
        return "long_run_easy"
    if re.search(r"有氧基础|有氧.*\d|aerobic", n):
        return "aerobic_base"
    if re.search(r"40min\+|30min\+|30min\s*\+|节奏|tempo", n):
        return "sustained_tempo_strides"
    if re.search(r"200m|200x|200\s*x|x\s*200|800.*1500|800x|1500x", n):
        return "speed_alactic_strides"
    if re.search(r"1k|2k|3k|5k\s*\+|^[125]k", n) and km < 14:
        return "tempo_combo"
    if re.search(r"速度|speed", n):
        return "speed_alactic_strides"
    if km < 4 and duration_sec < 30 * 60:
        return "recovery"
    return "easy_aerobic"


def _has_quality(exercises: list[dict]) -> bool:
    return any(
        ex["intensity_pct_lthr"] is not None and ex["intensity_pct_lthr"] >= 88
        for ex in exercises
    )


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    by_signature: dict[str, dict] = {}

    for label in WINDOWS:
        items = _load_window(label)
        season = "summer" if label.startswith("summer") else "winter"

        for it in items:
            prog = it.get("program")
            if not prog or prog.get("author") == "paulhandle":
                continue
            exercises = [_normalize_exercise(ex) for ex in prog.get("exercises", [])]
            sig = _signature(prog["name"], exercises)
            distance_m = float(prog.get("distance_m", 0))
            duration_sec = int(prog.get("duration_sec", 0))

            if sig not in by_signature:
                by_signature[sig] = {
                    "name": prog["name"],
                    "role": _classify_role(prog["name"], distance_m, duration_sec, exercises),
                    "distance_m": round(distance_m, 0),
                    "duration_sec": duration_sec,
                    "training_load_estimate": prog.get("training_load") or 0,
                    "authors": set([prog.get("author", "")]),
                    "seasons": set([season]),
                    "occurrences_total": 0,
                    "occurrences_by_season": defaultdict(int),
                    "exercises": exercises,
                }
            entry = by_signature[sig]
            entry["authors"].add(prog.get("author", ""))
            entry["seasons"].add(season)
            entry["occurrences_total"] += 1
            entry["occurrences_by_season"][season] += 1

    library = []
    for sig, entry in sorted(by_signature.items(), key=lambda x: -x[1]["occurrences_total"]):
        library.append({
            "name": entry["name"],
            "role": entry["role"],
            "distance_m": entry["distance_m"],
            "duration_sec": entry["duration_sec"],
            "training_load_estimate": entry["training_load_estimate"],
            "authors": sorted(entry["authors"]),
            "seasons": sorted(entry["seasons"]),
            "occurrences_total": entry["occurrences_total"],
            "occurrences_by_season": dict(entry["occurrences_by_season"]),
            "exercises": entry["exercises"],
        })

    out = {
        "version": "1.0",
        "source": "Distilled from real coach-prescribed workouts in COROS history (赵可, 刘征).",
        "intensity_convention": "All intensities expressed as %LTHR for athlete portability.",
        "templates": library,
    }

    out_path = DATA_DIR / "workout_templates.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote {out_path.relative_to(ROOT)}  ({len(library)} unique templates)")

    # Print role breakdown
    by_role: dict[str, list[str]] = defaultdict(list)
    for tpl in library:
        by_role[tpl["role"]].append(f"{tpl['name']} ({tpl['occurrences_total']}×)")
    print()
    for role in sorted(by_role.keys()):
        print(f"  {role}:")
        for n in by_role[role][:8]:
            print(f"    - {n}")
        if len(by_role[role]) > 8:
            print(f"    ... +{len(by_role[role]) - 8} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())
