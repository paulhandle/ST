#!/usr/bin/env python3
"""Run methodology analysis on a previously-extracted past plan.

Reads var/extracted_plans/<label>.json and writes a Markdown analysis
to var/extracted_plans/<label>.analysis.md alongside it.

Usage:
  uv run python scripts/analyze_past_plan.py             # all known windows
  uv run python scripts/analyze_past_plan.py summer_2025
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.skill_creator.analyzer import analyze, render_markdown

EXTRACTED_DIR = ROOT / "var" / "extracted_plans"
DEFAULT_LABELS = ("summer_2025", "winter_2025_2026")


def run_one(label: str) -> int:
    src = EXTRACTED_DIR / f"{label}.json"
    if not src.exists():
        print(f"  ! no extract for {label} at {src}", file=sys.stderr)
        return 1
    payload = json.loads(src.read_text(encoding="utf-8"))
    items = payload.get("coach_items", [])
    if not items:
        print(f"  ! {label}: no coach_items")
        return 1

    print(f"[analyze] {label} ({len(items)} workouts)")
    analysis = analyze(label, items)

    out_md = EXTRACTED_DIR / f"{label}.analysis.md"
    out_md.write_text(render_markdown(analysis), encoding="utf-8")

    print(f"  weeks: {len(analysis.weekly)}  peak: {analysis.peak_week_km:.1f} km  longest LR: {analysis.longest_long_run_km:.1f} km")
    print(f"  intensity: " + ", ".join(f"{k}={v:.1f}%" for k, v in analysis.intensity_distribution_pct.items()))
    print(f"  principles:")
    for p in analysis.inferred_principles:
        print(f"    - {p}")
    print(f"  → {out_md.relative_to(ROOT)}")
    return 0


def main(argv: list[str]) -> int:
    labels = argv[1:] if len(argv) > 1 else list(DEFAULT_LABELS)
    rc = 0
    for label in labels:
        rc |= run_one(label)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
