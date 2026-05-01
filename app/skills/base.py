"""Skill manifest and helpers."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import SportType


@dataclass(frozen=True)
class SkillManifest:
    slug: str
    name: str
    version: str
    sport: SportType
    supported_goals: list[str]         # ["finish", "target_time"]
    description: str
    author: str = ""
    tags: list[str] = field(default_factory=list)
    requires_llm: bool = False
