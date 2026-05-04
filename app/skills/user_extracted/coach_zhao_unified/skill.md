# Coach Zhao Unified Marathon Methodology

> Distilled from two complete coach-prescribed marathon programs that the
> athlete trained under (summer 2025-06-23 → 2025-10-26 and winter 2025-12-02
> → 2026-04-19). One unified philosophy, seasonally adapted.

## Origin

This skill was extracted by PerformanceProtocol from real coach-prescribed
workouts in the athlete's COROS Training Hub history:

- **Summer 2025**: 101 coach workouts (赵可 89×, 刘征 12×)
- **Winter 2025-26**: 127 coach workouts (赵可)

228 workouts total. The methodology underneath both seasons is the same; only
the strategy adapts.

## Core philosophy

1. **One methodology, two seasons.** Northern-China summers are too hot for
   long sustained efforts; winters allow higher volume and longer
   race-specific blocks. The skill picks summer or winter mode automatically
   from the calendar dates of the plan.

2. **Built for working professionals.** Sessions stay short by design.
   Quality sessions are 40–65 minutes. Long runs cap at 26 km
   (winter, ~2:40) or 21 km (summer). No 32 km / 3-hour grinds.

3. **Long-LSD is not the centerpiece.** Where most marathon plans pile on
   3-hour easy long runs, this one favors high-frequency moderate-volume
   sessions and race-specific 20-26 km efforts at sustained pace.

4. **Few traditional intervals; lots of tempo + strides.** The signature
   workout `速度训练` is **30 min easy warmup + 200/400/600m at high effort
   spaced through the run** — not VO2max repeats. `10K+5x200m` is sustained
   threshold + finishing strides. This builds speed reserve without
   accumulating the deep fatigue of classic VO2max work.

5. **Specific block over gradual ramp.** Volume stays low-moderate (40-80 km/wk)
   for ~70 % of the plan, then jumps sharply (often doubling) for a 3-5 week
   "specific block" before a steep taper. Bold, but it is what the historical
   data shows worked.

6. **3-week recovery rhythm during base.** Roughly every 3-4 weeks during the
   base phase, a recovery week cuts volume to ~70 % of the surrounding mean.

## Adherence rules (the user's specific principles)

These are part of the methodology and must be carried into the plan output as
guidance:

- **Completion > pace.** If you can't hit the target pace today, finish the
  workout anyway at whatever pace you can hold. Don't shorten it.

- **Don't reschedule.** If you miss a session, do today's prescribed workout
  today. Do not shift the missed workout into the next day.

- **Cadence preservation.** During recovery jogs inside speed sessions
  (e.g. between strides), let pace fall but **keep cadence constant**. This
  is the unique cue that protects running form when fatigued.

- **Same-day self-runs are fine** if today's prescription is rest, but do not
  replace prescribed quality with self-paced runs.

## Volume profile (typical for full-marathon plan)

| Phase | Window | Weekly volume | Long run | Quality density |
|-------|--------|--------------|----------|-----------------|
| Base | 0 – 65 % | 40 – 80 km, 3-week recovery cycle | 11 – 16 km | 2–3 quality / wk |
| Specific block | 65 – 90 % | 100 – 180 km (winter) / 100 – 130 km (summer) | 20 – 26 km (winter) / 20 – 21 km (summer) | 4 quality / wk |
| Taper | last 1–2 weeks | 50 % → 15 % of peak | 16 km → 3 km | 1 quality / wk |

In summer, peak weekly volume tops out around 127 km and long runs cap at
21 km. In winter, peak weekly volume can reach 180 km and long runs go to 26 km.
Strength training (~45 min, 1× per week) is added in winter only.

## Workout vocabulary

The skill draws from a library of 30 canonical templates extracted from the
historical data and stored as `data/workout_templates.json`. They group by
role:

- `aerobic_base` — graded easy run, 60 min total, two halves (`有氧基础60MIN`)
- `easy_aerobic` — generic easy aerobic
- `recovery` — 20-min jog at <70 % LTHR (`恢复跑`)
- `long_run_easy` — 16 km steady (`16K轻松跑`)
- `long_run_race_specific` — 20-21 km progressive tempo (`半马训练`, `2K+8K+10K`)
- `long_run_extended` — 26 km steady at 70 % LTHR (winter only)
- `speed_alactic_strides` — long warmup + escalating short repeats (`速度训练`,
  `速度训练 6x200`, `40min+200x5`, `10K+5x200m`, `8K+200x5`)
- `tempo_combo` — short tempo blocks like `1K+2K`, `1K+2Kx2`, `1Kx2+2Kx2`,
  `5K+2K`
- `sustained_tempo_strides` — 30-40 min easy + structured strides
  (`30min+(800+1500)`, `40min+200x5`, `30min +2K`)
- `strength` — winter-only 47-min strength session

All intensities are stored as `%LTHR`. Absolute paces are recomputed at
plan-generation time using the target athlete's threshold pace, so the
templates are portable across athletes (after individual fitness adjustment).

## When this skill is appropriate

- Sport = marathon
- 12 – 24 week training windows
- Athlete has a sustainable lifestyle volume floor of at least 30 km/week
- Athlete prefers session length under ~2.5 hours
- Athlete has access to LTHR or LTSP (from COROS dashboard) for accurate
  pace prescription; without it, paces fall back to assessment-derived ranges

## Future personalization

Per-athlete tuning happens in the orchestrator before the skill runs:

- LTHR-based pace conversion (athlete's threshold → absolute pace per template)
- Volume scaling based on athlete's safe weekly distance band
- Quality density throttle based on years_running and recovery markers
- Skip strength when `availability.strength_training_enabled = false`
