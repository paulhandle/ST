# ST Default Marathon Plan

The bundled fallback marathon skill. Used when the user has not selected
another methodology.

## Methodology

Classic **base / build / peak / taper** periodization across the configured
plan length:

| Phase | Window | Focus |
|-------|--------|-------|
| Base   | 0 – 50 % | aerobic volume, easy mileage, durability |
| Build  | 50 – 82 % | introduce threshold + marathon-pace work |
| Peak   | 82 – 94 % | longest long runs + race-specific quality |
| Taper  | last 1–2 weeks | reduce volume, preserve intensity |

Every fourth week is a recovery week (~18 % volume cut). Long runs cap at
32 km. No back-to-back hard sessions: long run on the user's preferred long-run
weekday; one quality session (alternating marathon-pace ↔ threshold) on a
separate day; remaining days are easy aerobic running.

## Pacing

- **Marathon pace**: derived from the user's target finish time, or from the
  midpoint of the assessment's predicted-time range when the user is in
  finish-only mode.
- **Easy pace**: marathon pace + ~70 s/km
- **Threshold pace**: marathon pace − ~18 s/km

## Generation Modes

The skill tries the LLM-personalized generator first when `ctx.llm_enabled` is
true; on any error it falls back to the deterministic rule generator. Both
output the same `PlanDraft` shape, so downstream code is identical regardless
of which path was used.

## When this skill is appropriate

- Sport is marathon
- User has at least 24 km/week of recent volume (lower triggers a warning
  but is not a hard block)
- Plan window is between 8 and 24 weeks

## Sources

Composite of widely published marathon training principles (long-run
progression, polarized intensity distribution, periodization). Not derived
from any single proprietary methodology.
