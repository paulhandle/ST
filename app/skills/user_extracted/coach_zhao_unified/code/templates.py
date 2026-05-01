"""Workout-template library loader + role-based selector.

The library is JSON in data/workout_templates.json. Each template carries
its structured exercises with intensity expressed as %LTHR — portable across
athletes. This module loads the library and exposes role-based picks.
"""
from __future__ import annotations

import json
import random
from importlib.resources import files
from typing import Iterable


def load_library() -> list[dict]:
    raw = files("app.skills.user_extracted.coach_zhao_unified.data").joinpath(
        "workout_templates.json"
    ).read_text(encoding="utf-8")
    return json.loads(raw)["templates"]


def pick(
    library: list[dict],
    role: str,
    *,
    season: str | None = None,
    rng: random.Random | None = None,
    exclude_names: Iterable[str] = (),
) -> dict | None:
    """Pick a template matching role; prefer ones used in the requested season."""
    rng = rng or random.Random(0)
    candidates = [t for t in library if t["role"] == role and t["name"] not in exclude_names]
    if not candidates:
        return None
    if season:
        in_season = [t for t in candidates if season in t.get("seasons", [])]
        if in_season:
            candidates = in_season
    weights = [t.get("occurrences_total", 1) for t in candidates]
    total = sum(weights) or 1
    r = rng.random() * total
    cum = 0
    for t, w in zip(candidates, weights):
        cum += w
        if r <= cum:
            return t
    return candidates[-1]


def find_by_name(library: list[dict], name: str) -> dict | None:
    for t in library:
        if t["name"] == name:
            return t
    return None
