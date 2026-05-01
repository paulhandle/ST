# Lessons

## 2026-05-01 — Architectural patterns confirmed during the Skill refactor

These were validated by the user during the MVP+1 design discussion. Apply going forward:

1. **Skill = Hybrid (rules + LLM)**, not pure LLM and not pure code. Hard safety rules (volume bounds, taper, no back-to-back hard) are deterministic; creative slots (workout choice this week, intensity nudges) are LLM. Pure LLM was rejected because it can't be formally verified for athlete safety.

2. **Skills are pure functions of `SkillContext`**. They never see the DB or external APIs. The orchestrator does all I/O. This makes skills replayable, testable, version-controllable.

3. **One skill per training cycle**. Mixing methodologies (e.g., Daniels VO2max work + Norwegian sub-threshold in the same week) is scientifically unsound — competing adaptation signals. Across cycles you can switch skills; within a cycle you cannot.

4. **Tools belong to the platform, not skills**. Skills receive summarized data via the context; they do not call COROS / Garmin / Strava directly. This keeps caching, rate limiting, error handling, and auditing in one place.

5. **Skills are filesystem artifacts, not DB rows**. Each skill is a directory with `skill.md` + `spec.yaml` + `skill.py` + `code/`. This aligns with Claude Skill format, supports git versioning, and lets users edit / share skills as plain text.

6. **Increment, don't big-bang**. The user wanted a clean refactor *first*, before adding the skill-creator feature, even though skill-creator is the differentiating value. Rationale: easier to validate the abstraction with one bundled skill before building the harder UX flow that creates new skills.

## 2026-05-01 — Process patterns

- **macOS sed has no `\b` word boundary**. Fall back to a Python regex one-liner via `python3 -c "..."` for bulk file rewrites. Pattern `default=datetime\.utcnow\b` failed silently with `sed -i ''`.
- **`git mv` requires the source to be tracked**. Untracked new files (e.g., a freshly created `checkin.py` that hadn't been committed) need plain `mv`. Mixing tracked and untracked file moves means doing the operation in two passes.
- **Stale SQLite DB lock from a previous test run will block the next test run**. If `database is locked` shows up at `Base.metadata.drop_all(...)`, look for a leftover `python -m unittest` process via `lsof <db file>` and kill it.
- **AthleteProfile DB model and AthleteProfileData TOML dataclass are different shapes**. The DB model only has `id, name, sport, level, weekly_training_days, weekly_training_hours, notes` — `age`, `sex`, etc. live in the local TOML profile. Use `getattr(athlete, "age", None)` when bridging the two, never direct attribute access.

## 2026-05-01 — User preferences confirmed

- For exploratory or architectural questions, the user wants me to **push back** with concrete tensions, not write more agreeable design docs. Listing real risks/IP-issues/scientific-issues is more valuable than a polished diagram.
- The user wants **directory structure that visibly separates skill from business logic** — not just module-level discipline. Skills live in their own top-level directory; tools in their own; KB in its own.
- For projects without active git remotes / branches, **don't propose CI integration or extensive feature flags** — keep changes simple and purely structural.
