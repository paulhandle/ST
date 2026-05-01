"""Sport-specific knowledge bases (physiology, distance constants, assessors).

Skills consume knowledge bases via the SkillContext; they should not import
KB modules directly. This keeps the Skill <-> Platform contract narrow.
"""
from __future__ import annotations

from typing import Protocol


class KnowledgeBase(Protocol):
    """Common interface every sport KB exposes."""

    sport: str
