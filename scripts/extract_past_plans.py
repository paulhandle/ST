#!/usr/bin/env python3
"""Extract structured + human-readable views of historical training programs.

Reads the latest var/coros_probe/history-<label>-<timestamp>.json files and
produces:

  var/extracted_plans/<label>.md      Human-readable per-week summary
  var/extracted_plans/<label>.json    Structured records for downstream use

The structured form decodes COROS unit conventions:
  - distance: cm   →  meters
  - intensityValue (pace): sec*1000 / km  →  sec/km
  - intensityPercent: % * 1000  →  %
  - targetType: 1=none, 2=duration_sec, 5=distance_cm

Filters out self-created programs (nickname == "paulhandle"); keeps only
coach-prescribed entries.

Usage:
  uv run python scripts/extract_past_plans.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE_DIR = ROOT / "var" / "coros_probe"
OUT_DIR = ROOT / "var" / "extracted_plans"
OUT_DIR.mkdir(parents=True, exist_ok=True)

LABELS = ("summer_2025", "winter_2025_2026")
SELF_NICKNAMES = {"paulhandle"}


def _latest_probe(label: str) -> Path:
    candidates = sorted(PROBE_DIR.glob(f"history-{label}-*.json"))
    candidates = [p for p in candidates if not p.name.endswith(".shape.json")]
    if not candidates:
        raise FileNotFoundError(f"no probe file for {label}")
    return candidates[-1]


def _yyyymmdd_to_date(value) -> date | None:
    s = str(value)
    if len(s) != 8 or not s.isdigit():
        return None
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))


def _decode_target(target_type: int, target_value: int) -> tuple[str, str]:
    """Return (kind, formatted) like ('distance', '5.0 km') or ('duration', '45:00')."""
    if target_type == 5:
        meters = target_value / 100
        if meters >= 1000:
            return "distance", f"{meters / 1000:.2f} km"
        return "distance", f"{meters:.0f} m"
    if target_type == 2:
        sec = int(target_value)
        if sec >= 60:
            mm, ss = divmod(sec, 60)
            return "duration", f"{mm}:{ss:02d}"
        return "duration", f"{sec}s"
    return "open", "open"


def _decode_intensity(intensity_type: int, intensity_value: int, intensity_percent: int) -> str:
    parts: list[str] = []
    if intensity_type == 3 and intensity_value:
        sec_per_km = intensity_value / 1000
        mm, ss = divmod(int(sec_per_km), 60)
        parts.append(f"pace {mm}:{ss:02d}/km")
    elif intensity_type == 2 and intensity_value:
        parts.append(f"HR {intensity_value} bpm")
    if intensity_percent:
        parts.append(f"{intensity_percent / 1000:.0f}% LTHR")
    return ", ".join(parts) if parts else "—"


def _decode_rest(rest_type: int, rest_value: int) -> str:
    if rest_type == 3 and rest_value:
        mm, ss = divmod(int(rest_value), 60)
        return f"rest {mm}:{ss:02d}" if mm else f"rest {ss}s"
    if rest_type == 0 and rest_value:
        return f"rest {rest_value}s"
    return ""


def _decode_program(prog: dict) -> dict:
    exercises = []
    for ex in prog.get("exercises", []):
        kind, target_str = _decode_target(ex.get("targetType", 0), ex.get("targetValue", 0))
        intensity = _decode_intensity(
            ex.get("intensityType", 0),
            ex.get("intensityValue", 0),
            ex.get("intensityPercent", 0),
        )
        rest = _decode_rest(ex.get("restType", 0), ex.get("restValue", 0))
        exercises.append({
            "sets": ex.get("sets", 1),
            "target_kind": kind,
            "target": target_str,
            "intensity": intensity,
            "rest": rest,
            "internal_name": ex.get("name", ""),
            "raw": {
                "targetType": ex.get("targetType"),
                "targetValue": ex.get("targetValue"),
                "intensityType": ex.get("intensityType"),
                "intensityValue": ex.get("intensityValue"),
                "intensityPercent": ex.get("intensityPercent"),
                "restType": ex.get("restType"),
                "restValue": ex.get("restValue"),
            },
        })
    return {
        "id": prog.get("id"),
        "name": prog.get("name", ""),
        "author": prog.get("nickname", ""),
        "overview": prog.get("overview", ""),
        "sport_type": prog.get("sportType"),
        "distance_m": (prog.get("distance") or 0) / 100,
        "duration_sec": prog.get("duration") or 0,
        "training_load": prog.get("trainingLoad") or 0,
        "exercise_count": prog.get("exerciseNum") or 0,
        "total_sets": prog.get("totalSets") or 0,
        "exercises": exercises,
    }


def _format_program_one_line(prog: dict) -> str:
    km = prog["distance_m"] / 1000
    mm, ss = divmod(int(prog["duration_sec"]), 60)
    return (
        f"{prog['name']:<22} | "
        f"{km:5.1f}km / {mm:>3d}:{ss:02d} / TL {prog['training_load']:>3d} | "
        f"{prog['author']}"
    )


def _format_exercises_block(prog: dict) -> str:
    if not prog["exercises"]:
        return "  (no structured intervals)"
    rows = []
    for i, ex in enumerate(prog["exercises"]):
        sets = f"{ex['sets']}×" if ex["sets"] != 1 else "    "
        target = ex["target"]
        intensity = ex["intensity"]
        rest = f"  {ex['rest']}" if ex["rest"] else ""
        rows.append(f"    {i + 1}. {sets} {target:<12} @ {intensity}{rest}")
    return "\n".join(rows)


def extract(label: str) -> dict:
    raw_file = _latest_probe(label)
    raw = json.loads(raw_file.read_text(encoding="utf-8"))
    data = raw["data"]

    programs_by_id = {p["id"]: _decode_program(p) for p in data.get("programs", [])}

    # Map entity (calendar instance) → date + program
    items: list[dict] = []
    for ent in data.get("entities", []):
        program_id = ent.get("planProgramId") or ent.get("planProgramID")
        # Some entities reference the program via planId+idInPlan; programs[] uses 'id'
        # Fall back to matching by planId
        prog = None
        for p in data.get("programs", []):
            if p.get("id") == program_id or p.get("planId") == ent.get("planId"):
                prog = programs_by_id.get(p["id"])
                break
        # Direct program match by ent.planProgramId hashing through programs_by_id
        if prog is None and program_id and program_id in programs_by_id:
            prog = programs_by_id[program_id]
        # As last resort: if 1:1, match by sortNo / dayNo
        d = _yyyymmdd_to_date(ent.get("happenDay"))
        items.append({
            "happen_day": d.isoformat() if d else None,
            "execute_status": ent.get("executeStatus"),
            "score": ent.get("score"),
            "complete_rate": ent.get("completeRate"),
            "standard_rate": ent.get("standardRate"),
            "third_party": ent.get("thirdParty"),
            "program": prog,
        })

    # Some entities may not match — we still need a fallback. Many COROS schemas
    # use 1:1 ordering between programs and entities by sortNo. Build that index too.
    by_sort = sorted(data.get("entities", []), key=lambda e: e.get("sortNoInSchedule") or 0)
    progs_by_sort = sorted(data.get("programs", []), key=lambda p: p.get("planIdIndex") or 0)

    # If matching above failed for any item, try positional fallback
    if any(item["program"] is None for item in items) and len(by_sort) == len(progs_by_sort):
        items_pos: list[dict] = []
        for ent, p in zip(by_sort, progs_by_sort):
            d = _yyyymmdd_to_date(ent.get("happenDay"))
            items_pos.append({
                "happen_day": d.isoformat() if d else None,
                "execute_status": ent.get("executeStatus"),
                "score": ent.get("score"),
                "complete_rate": ent.get("completeRate"),
                "standard_rate": ent.get("standardRate"),
                "third_party": ent.get("thirdParty"),
                "program": _decode_program(p),
            })
        items = items_pos

    # Filter coach-prescribed
    coach_items = [i for i in items if i["program"] and i["program"]["author"] not in SELF_NICKNAMES]
    self_items = [i for i in items if i["program"] and i["program"]["author"] in SELF_NICKNAMES]

    return {
        "label": label,
        "raw_file": str(raw_file.name),
        "all_count": len(items),
        "coach_count": len(coach_items),
        "self_count": len(self_items),
        "coach_items": coach_items,
        "self_items": self_items,
    }


def write_markdown(extract_result: dict) -> Path:
    label = extract_result["label"]
    items = extract_result["coach_items"]
    if not items:
        print(f"  ! no coach items in {label}")

    items_dated = sorted([i for i in items if i["happen_day"]], key=lambda x: x["happen_day"])

    by_week: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for it in items_dated:
        d = date.fromisoformat(it["happen_day"])
        iso = d.isocalendar()
        by_week[(iso[0], iso[1])].append(it)

    # Author breakdown
    authors = defaultdict(int)
    for it in items_dated:
        authors[it["program"]["author"]] += 1

    # Workout-name frequency
    name_freq: dict[str, int] = defaultdict(int)
    for it in items_dated:
        name_freq[it["program"]["name"]] += 1

    lines = [f"# Past Training Plan — {label}", ""]
    if items_dated:
        lines.append(
            f"Date range: {items_dated[0]['happen_day']} → {items_dated[-1]['happen_day']}  "
            f"(week count: {len(by_week)})"
        )
    lines.append(f"Coach-prescribed: {extract_result['coach_count']} workouts")
    lines.append(f"Self-created:     {extract_result['self_count']} workouts")
    lines.append("")
    lines.append("## Author breakdown")
    for author, count in sorted(authors.items(), key=lambda x: -x[1]):
        lines.append(f"- {count:3d}× {author}")
    lines.append("")
    lines.append("## Workout-name frequency (top 25)")
    for name, count in sorted(name_freq.items(), key=lambda x: -x[1])[:25]:
        lines.append(f"- {count:3d}× {name}")
    lines.append("")
    lines.append("## Per-week digest")
    lines.append("")
    for (year, week), week_items in sorted(by_week.items()):
        first_day = min(it["happen_day"] for it in week_items)
        total_sec = sum(it["program"]["duration_sec"] for it in week_items)
        total_km = sum(it["program"]["distance_m"] for it in week_items) / 1000
        total_tl = sum(it["program"]["training_load"] for it in week_items)
        lines.append(f"### {year}-W{week:02d}  (week of {first_day})")
        lines.append(
            f"  Total: {total_km:.1f} km · {total_sec // 60} min · TL {total_tl} · {len(week_items)} sessions"
        )
        for it in sorted(week_items, key=lambda x: x["happen_day"]):
            d = date.fromisoformat(it["happen_day"])
            day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]
            prog = it["program"]
            status_flag = "✓" if it.get("execute_status") else "·"
            lines.append(f"  {status_flag} {it['happen_day']} {day_name}  {_format_program_one_line(prog)}")
            block = _format_exercises_block(prog)
            if block.strip():
                lines.append(block)
        lines.append("")

    out_file = OUT_DIR / f"{label}.md"
    out_file.write_text("\n".join(lines), encoding="utf-8")
    return out_file


def write_structured(extract_result: dict) -> Path:
    label = extract_result["label"]
    out_file = OUT_DIR / f"{label}.json"

    payload = {
        "label": label,
        "extracted_at": datetime.now().isoformat(timespec="seconds"),
        "source_file": extract_result["raw_file"],
        "coach_count": extract_result["coach_count"],
        "self_count": extract_result["self_count"],
        "coach_items": extract_result["coach_items"],
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return out_file


def main() -> int:
    for label in LABELS:
        try:
            print(f"[extract] {label}")
            result = extract(label)
            md = write_markdown(result)
            js = write_structured(result)
            print(f"  coach: {result['coach_count']}  self: {result['self_count']}")
            print(f"  → {md.relative_to(ROOT)}")
            print(f"  → {js.relative_to(ROOT)}")
        except FileNotFoundError as exc:
            print(f"  ! {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
