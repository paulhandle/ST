"""Skill registry and loader.

A Skill is a methodology that takes a SkillContext and produces a PlanDraft.
Skills live under app/skills/<slug>/ with this layout:

    <slug>/
      skill.md          (human-readable methodology)
      spec.yaml         (machine-readable manifest)
      skill.py          (exports `skill: Skill`)
      code/             (implementation modules; freely structured)
"""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Protocol, runtime_checkable

import yaml

from app.core.context import PlanDraft, SkillContext
from app.models import SportType
from app.skills.base import SkillManifest

SKILLS_DIR = Path(__file__).resolve().parent


@runtime_checkable
class Skill(Protocol):
    @property
    def manifest(self) -> SkillManifest: ...

    def applicable(self, ctx: SkillContext) -> tuple[bool, str]:
        """Return (True, "") if skill can run in this ctx; else (False, reason)."""
        ...

    def generate_plan(self, ctx: SkillContext) -> PlanDraft:
        """Pure function: ctx in, plan out. No DB or external API access."""
        ...


def load_skill(slug: str) -> Skill:
    """Load skill at app/skills/<slug>/.

    The skill module (app.skills.<slug>.skill) must export an attribute named
    `skill` that satisfies the Skill protocol.
    """
    if not _is_safe_slug(slug):
        raise ValueError(f"Invalid skill slug: {slug!r}")
    skill_dir = SKILLS_DIR / slug
    if not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill not found: {skill_dir}")
    spec_path = skill_dir / "spec.yaml"
    if not spec_path.exists():
        raise FileNotFoundError(f"Skill {slug!r} is missing spec.yaml")

    module = importlib.import_module(f"app.skills.{slug}.skill")
    if not hasattr(module, "skill"):
        raise AttributeError(f"app.skills.{slug}.skill must export `skill`")
    instance: Skill = module.skill
    return instance


def list_skills() -> list[SkillManifest]:
    """Discover all skills under app/skills/ by reading their spec.yaml files."""
    out: list[SkillManifest] = []
    for child in SKILLS_DIR.iterdir():
        if not child.is_dir() or child.name.startswith("_"):
            continue
        spec_path = child / "spec.yaml"
        if not spec_path.exists():
            continue
        manifest = _load_manifest(child.name, spec_path)
        if manifest is not None:
            out.append(manifest)
    return out


def _load_manifest(slug: str, spec_path: Path) -> SkillManifest | None:
    with open(spec_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    sport_value = data.get("sport")
    try:
        sport = SportType(sport_value) if sport_value else SportType.MARATHON
    except ValueError:
        return None
    return SkillManifest(
        slug=slug,
        name=str(data.get("name", slug)),
        version=str(data.get("version", "0.0.0")),
        sport=sport,
        supported_goals=list(data.get("supported_goals", [])),
        description=str(data.get("description", "")),
        author=str(data.get("author", "")),
        tags=list(data.get("tags", [])),
        requires_llm=bool(data.get("requires_llm", False)),
    )


def _is_safe_slug(slug: str) -> bool:
    return bool(slug) and slug.replace("_", "").replace("-", "").isalnum()


__all__ = ["Skill", "SkillManifest", "load_skill", "list_skills"]
