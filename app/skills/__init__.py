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
from typing import Protocol, runtime_checkable, TYPE_CHECKING

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


USER_EXTRACTED_DIR = SKILLS_DIR / "user_extracted"


def _resolve_skill_dir(slug: str) -> tuple[Path, str]:
    """Return (filesystem_dir, dotted_module_prefix) for a slug.

    Built-in skills live at app/skills/<slug>/ ; user-extracted skills live
    at app/skills/user_extracted/<slug>/. Built-in shadows user-extracted.
    """
    builtin = SKILLS_DIR / slug
    if builtin.is_dir() and (builtin / "spec.yaml").exists():
        return builtin, f"app.skills.{slug}"
    user = USER_EXTRACTED_DIR / slug
    if user.is_dir() and (user / "spec.yaml").exists():
        return user, f"app.skills.user_extracted.{slug}"
    raise FileNotFoundError(f"Skill not found: {slug!r}")


def load_skill(slug: str) -> Skill:
    """Load skill at app/skills/<slug>/ or app/skills/user_extracted/<slug>/.

    The skill module must export an attribute named `skill` that satisfies
    the Skill protocol.
    """
    if not _is_safe_slug(slug):
        raise ValueError(f"Invalid skill slug: {slug!r}")
    skill_dir, module_prefix = _resolve_skill_dir(slug)
    module = importlib.import_module(f"{module_prefix}.skill")
    if not hasattr(module, "skill"):
        raise AttributeError(f"{module_prefix}.skill must export `skill`")
    instance: Skill = module.skill
    return instance


def list_skills() -> list[SkillManifest]:
    """Discover skills under app/skills/ and app/skills/user_extracted/."""
    out: list[SkillManifest] = []
    for parent in (SKILLS_DIR, USER_EXTRACTED_DIR):
        if not parent.exists():
            continue
        for child in parent.iterdir():
            if not child.is_dir() or child.name.startswith("_") or child.name == "user_extracted":
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
