# PRD: COROS-First Marathon Training MVP

## Objective

Build a personal-use training planning product for COROS users preparing for a full marathon. The product should automatically read COROS data, assess the athlete's current road-running ability, generate a structured full-marathon plan, sync confirmed workouts into COROS, monitor execution, and recommend plan adjustments over time.

The first-stage product is not a public commercial COROS integration. It is a personal-use automation-first system optimized for proving the training intelligence loop.

## Product Thesis

The core product value is not "generate a schedule." The value is a closed-loop training decision system:

1. Understand the athlete from real history.
2. Judge whether the marathon goal is realistic and safe.
3. Generate a structured plan that fits available time and ability.
4. Put confirmed workouts into COROS automatically.
5. Monitor completed training and feedback.
6. Recommend adjustments before the plan becomes stale or unsafe.

## Target User

Primary first-stage user:

- Uses COROS as the main training device.
- Is preparing for a full marathon.
- Has a concrete goal such as finishing, sub-4:00, or another target time.
- Wants structured training rather than a generic text calendar.
- Is willing to provide COROS username/password for personal-use automation.
- Wants the product to make professional recommendations and reject unsafe goals when needed.

## First-Stage Scope

In scope:

- COROS username/password connection.
- Simple encrypted credential storage.
- Manual one-click COROS import.
- Scheduled background COROS import.
- Pull all accessible COROS web data where technically available:
  - Activity list.
  - Activity detail.
  - Running distance, duration, pace, heart rate, cadence, elevation, training load, and route-derived data where available.
  - COROS performance indicators such as marathon level, fatigue, running performance, race predictor, threshold-related values, and recovery-related values where available.
  - User workout feedback, including voice/text feedback where available.
- Road-running ability assessment.
- Full-marathon goal evaluation.
- Full-marathon structured plan generation.
- User-selectable training duration, with warnings or rejection when too short.
- User-provided weekly availability, with system-recommended safer ranges.
- Structured workout model with warmup, work, recovery, repeats, cooldown, intensity targets, and notes.
- User-confirmed sync of future workouts into the COROS calendar.
- Manual sync and scheduled sync.
- Weekly adjustment recommendations.
- Immediate warning for severe fatigue, pain, or obvious risk signals.
- User confirmation before plan changes are applied and synced.
- Triathlon-ready underlying data model, while the first product behavior remains road running.

Out of scope for first stage:

- Public commercial launch.
- Official COROS API partnership.
- Coach/team product surface.
- Multi-user coach dashboard.
- Garmin, Strava, or other provider integration.
- Full triathlon plan generation.
- Automatic bypass of CAPTCHA, MFA, or platform risk controls.
- Medical diagnosis or injury treatment recommendations.
- Fully autonomous plan changes without user confirmation.

## Core User Flow

### 1. Connect COROS

The user enters COROS username and password. The product stores credentials with simple encryption and attempts to log into COROS Training Hub automation.

Success criteria:

- Login succeeds.
- Session is stored or refreshed as needed.
- The user can trigger "import now."
- The system can run scheduled imports.

Failure behavior:

- If credentials are invalid, ask the user to update them.
- If CAPTCHA, MFA, or risk controls appear, ask for user intervention.
- If page structure changes, mark automation as failed and preserve existing data.

### 2. Import History

The system imports all accessible running history and related performance data from COROS.

Minimum required data:

- Activity date and type.
- Distance.
- Duration.
- Average pace or speed.
- Average heart rate when available.
- Elevation gain when available.
- Training load or equivalent when available.

Desired data:

- Splits/laps.
- Pace zones.
- Heart-rate zones.
- Cadence.
- Power.
- Running performance.
- Marathon level.
- Fatigue.
- Recovery.
- VO2max or equivalent.
- Threshold pace/HR if available.
- User feedback and notes.

Success criteria:

- Duplicate activities are not re-imported.
- Re-import updates changed activity details.
- The system records source, import time, and raw source payload where useful for debugging.

### 3. Assess Running Ability

The system assesses current full-marathon readiness and road-running ability.

Assessment dimensions:

- Training consistency:
  - Runs per week over 4, 8, and 12 weeks.
  - Missed weeks and recent continuity.
- Volume:
  - Weekly distance over 4, 8, and 12 weeks.
  - Peak weekly distance.
  - Monotony and spikes.
- Long-run capacity:
  - Longest run in 4, 8, and 12 weeks.
  - Long-run frequency.
  - Long run as percentage of weekly volume.
- Intensity ability:
  - Recent best efforts over common distances where inferable.
  - Threshold pace estimate.
  - Pace stability at moderate and hard efforts.
- Aerobic efficiency:
  - Pace versus heart rate trends where HR exists.
  - Drift in long efforts where data allows.
- Recovery and risk:
  - Fatigue signals.
  - Training load spikes.
  - Pain or poor feedback.
- Goal-specific readiness:
  - Whether the target marathon time is realistic.
  - Whether the selected training duration is enough.
  - Whether weekly availability can support the goal.

Assessment output:

- Overall readiness score.
- Current safe weekly running range.
- Current long-run capacity.
- Estimated marathon capability range.
- Goal feasibility status:
  - Accept.
  - Accept with warning.
  - Recommend lower target.
  - Reject as unsafe/unrealistic.
- Key limiting factors.
- Data confidence.
- Plain-language rationale.

### 4. Define Goal And Constraints

The user defines:

- Goal type:
  - Finish.
  - Target time, such as sub-4:00.
- Race date or training duration.
- Weekly available training days.
- Preferred long-run day.
- Unavailable days.
- Maximum weekday session duration.
- Maximum weekend session duration.
- Injury or pain constraints.
- Preference for strength training and cross-training.

System behavior:

- Recommend a weekly training-day range.
- Warn if chosen availability is too low for the goal.
- Warn if chosen availability is too high relative to recent training.
- Warn or reject if training duration is too short.

### 5. Generate Plan

The system generates a structured full-marathon plan using the current assessment, goal, timeline, and constraints.

Plan phases:

- Base.
- Build.
- Peak.
- Taper.
- Recovery or adaptation weeks where needed.

Workout types:

- Easy run.
- Long run.
- Marathon-pace run.
- Tempo or threshold run.
- Interval session.
- Recovery run.
- Strides.
- Strength or mobility.
- Rest.

Each workout should include:

- Date.
- Discipline.
- Purpose.
- Duration or distance.
- Intensity target:
  - Pace range, HR zone, RPE, or effort description depending on available data.
- Structured steps:
  - Warmup.
  - Repeats.
  - Recoveries.
  - Cooldown.
- Adaptation notes.
- Sync status.

Plan safety rules:

- Weekly load should progress gradually.
- Down weeks should be inserted when progression requires them.
- Long run should not jump beyond current safe capacity.
- High-intensity sessions should be limited based on level and fatigue.
- Goal pace work should only appear when the athlete has enough base.
- The plan should reject impossible combinations rather than silently generating a dangerous plan.

### 6. Confirm And Sync To COROS

After plan generation, the user reviews and confirms. The product syncs confirmed future workouts into COROS.

MVP sync success:

- Confirmed future workouts appear on the COROS calendar.
- Workouts can reach the COROS app/watch through normal COROS behavior.

Sync behavior:

- Manual sync now.
- Scheduled sync for future confirmed plan updates.
- Allow multiple workouts on the same day because COROS supports that behavior.
- Record sync attempts, status, errors, and source workout IDs.

### 7. Monitor And Adjust

The system imports new COROS data after training completion and updates status.

Monitoring signals:

- Workout completed, missed, partially completed, or overdone.
- Planned versus actual distance/duration/intensity.
- Training load deviation.
- Pace and HR response.
- Fatigue/recovery indicators.
- User feedback and pain signals.

Adjustment cadence:

- Update internal state after each import.
- Generate formal adjustment suggestions weekly.
- Trigger immediate warnings for severe fatigue, pain, or unsafe load spikes.

Adjustment actions:

- Reduce intensity.
- Reduce duration.
- Move workout dates.
- Add recovery day.
- Replace workout with easy run.
- Recalculate goal pace.
- Recommend target downgrade.
- Rebuild future 7-14 days.

User confirmation:

- The product should not apply plan adjustments automatically.
- The user must confirm changes before they are synced to COROS.

## Safety And Rejection Rules

The system may reject or downgrade a goal when:

- The training window is too short for the target.
- Recent weekly volume is far below what the target requires.
- Long-run capacity is insufficient.
- Recent fatigue or pain signals are high.
- Training consistency is too low.
- The requested weekly training schedule is too aggressive.
- The target pace is far beyond estimated current capacity.

The system should explain rejection clearly and offer a safer alternative.

Example:

```text
The current data does not support a sub-4:00 marathon in 8 weeks. Recent weekly mileage is 22 km and the longest run in the last 8 weeks is 14 km. A safer target is finishing comfortably or extending the plan to 16-20 weeks.
```

## Acceptance Criteria

The MVP is acceptable when:

- A COROS account can be connected with username/password.
- Historical running data can be automatically imported from COROS.
- Repeated imports are idempotent.
- The system produces a road-running/full-marathon assessment with readiness, risks, and confidence.
- The user can enter a full-marathon target such as sub-4:00.
- The system warns or rejects unsafe goal/timeline/training availability combinations.
- The system generates a structured full-marathon plan.
- The user can confirm the plan.
- Confirmed future workouts are automatically created in the COROS calendar.
- New completed workouts can be imported after execution.
- The system compares planned versus actual training.
- The system generates weekly adjustment suggestions.
- Confirmed adjustments sync back into COROS.

## Open Implementation Questions

- Exact COROS web selectors, endpoints, and session behavior must be discovered during implementation.
- Whether COROS voice feedback is exposed as text in Training Hub must be verified.
- Whether all desired health and fatigue data are accessible from the web UI must be verified.
- The exact workout creation flow in COROS Training Hub must be mapped through automation.
- A secure-enough local encryption key strategy must be chosen for personal use.
