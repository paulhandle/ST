# Technical Design: COROS-First Marathon MVP

## Current Repository Baseline

The existing codebase is a FastAPI backend with SQLAlchemy and SQLite. It already has coarse concepts for athletes, training plans, training sessions, device accounts, and sync tasks.

Before implementation, fix the current import blocker:

- `app/models.py:75` has invalid syntax in `AthleteProfile.weekly_training_hours`.
- The existing test references history import and assessment endpoints that are not implemented yet.
- The local default `python3` is 3.9.6 while the project requires Python 3.11+.

## Architecture Overview

Add a closed-loop training system around five subsystems:

1. COROS automation.
2. Activity and health data ingestion.
3. Athlete assessment.
4. Structured plan generation and adjustment.
5. COROS workout synchronization.

Suggested module layout:

```text
app/
  coros/
    automation.py
    client.py
    credentials.py
    parsers.py
    sync.py
  ingestion/
    service.py
    dedupe.py
    normalizers.py
  assessment/
    running.py
    readiness.py
    risk.py
  planning/
    marathon.py
    constraints.py
    workout_builder.py
    adjustment.py
  api/
    routes.py
  models.py
  schemas.py
```

Keep provider-specific behavior in `app/coros/`. Keep training decisions provider-neutral in `app/assessment/` and `app/planning/`.

## COROS Automation Strategy

Because this is personal use, the first version can use username/password web automation. The implementation should still avoid careless credential handling.

Recommended runtime:

- Playwright for browser automation.
- Headless mode for scheduled jobs.
- Headed mode or screenshot/debug artifacts for local troubleshooting.
- Persistent browser context or session cookies where practical.

Automation flows:

1. Login.
2. Import activity list and details.
3. Import dashboard/performance metrics.
4. Import workout feedback if visible.
5. Create structured workouts.
6. Place workouts on the calendar.

Failure handling:

- Invalid credentials: mark connection failed and ask for updated credentials.
- MFA/CAPTCHA/risk challenge: pause and require user intervention.
- Page structure changed: mark automation failed, keep previous data, and expose diagnostic screenshots/logs.
- Partial import: commit successfully parsed items and record skipped items.

Do not implement:

- CAPTCHA bypass.
- MFA bypass.
- Aggressive retry loops.
- Silent destructive calendar changes.

## Credential Storage

For personal-use MVP:

- Store COROS username.
- Store encrypted COROS password.
- Store provider connection status.
- Store last successful login/import/sync timestamps.

Suggested approach:

- Use symmetric encryption with an environment-provided key such as `ST_SECRET_KEY`.
- Do not log plaintext credentials.
- Do not return passwords through API responses.
- Allow credential deletion.

If no encryption key is configured in local development, the app should fail clearly for credential-saving endpoints rather than silently storing plaintext.

## Data Model

Add provider-neutral normalized tables plus raw-source capture.

### DeviceAccount

Extend existing device account:

- `device_type`: `coros`
- `username`
- `encrypted_password`
- `auth_status`
- `last_login_at`
- `last_import_at`
- `last_sync_at`
- `last_error`

### AthleteActivity

Normalized activity record:

- `id`
- `athlete_id`
- `provider`
- `provider_activity_id`
- `sport`
- `discipline`
- `started_at`
- `timezone`
- `duration_sec`
- `moving_duration_sec`
- `distance_m`
- `elevation_gain_m`
- `avg_pace_sec_per_km`
- `avg_hr`
- `max_hr`
- `avg_cadence`
- `avg_power`
- `training_load`
- `perceived_effort`
- `feedback_text`
- `raw_payload_json`
- `created_at`
- `updated_at`

Unique key:

- `(provider, provider_activity_id)`

### ActivityLap

Optional details:

- `activity_id`
- `lap_index`
- `duration_sec`
- `distance_m`
- `avg_pace_sec_per_km`
- `avg_hr`
- `elevation_gain_m`

### AthleteMetricSnapshot

Provider metrics over time:

- `athlete_id`
- `provider`
- `measured_at`
- `metric_type`
- `value`
- `unit`
- `raw_payload_json`

Examples:

- `marathon_level`
- `fatigue`
- `running_performance`
- `vo2max`
- `threshold_pace`
- `threshold_hr`
- `race_predictor_marathon`
- `recovery_status`

### RaceGoal

Marathon target:

- `athlete_id`
- `sport`
- `distance`
- `target_type`: `finish` or `target_time`
- `target_time_sec`
- `race_date`
- `training_start_date`
- `plan_weeks`
- `status`

### TrainingAvailability

User constraints:

- `athlete_id`
- `weekly_training_days`
- `preferred_long_run_weekday`
- `unavailable_weekdays`
- `max_weekday_duration_min`
- `max_weekend_duration_min`
- `strength_training_enabled`
- `notes`

### StructuredWorkout

Provider-neutral planned workout:

- `plan_id`
- `scheduled_date`
- `discipline`
- `workout_type`
- `title`
- `purpose`
- `duration_min`
- `distance_m`
- `target_intensity_type`
- `target_pace_min_sec_per_km`
- `target_pace_max_sec_per_km`
- `target_hr_min`
- `target_hr_max`
- `rpe_min`
- `rpe_max`
- `status`

### WorkoutStep

Structured workout steps:

- `workout_id`
- `step_index`
- `step_type`: `warmup`, `work`, `recovery`, `cooldown`, `repeat`
- `duration_sec`
- `distance_m`
- `target_type`
- `target_min`
- `target_max`
- `repeat_count`
- `notes`

### ProviderSyncRecord

Sync tracking:

- `athlete_id`
- `plan_id`
- `workout_id`
- `provider`
- `provider_workout_id`
- `provider_calendar_item_id`
- `sync_status`
- `attempted_at`
- `synced_at`
- `error_message`
- `raw_payload_json`

## Ingestion Pipeline

Pipeline:

1. Fetch activity list from COROS.
2. For each new or changed item, fetch detail.
3. Normalize provider fields to `AthleteActivity`.
4. Store raw payload for debugging.
5. Upsert by provider activity ID.
6. Import laps/splits where available.
7. Import metric snapshots from dashboard/performance pages.
8. Recalculate assessment inputs.

Idempotency rules:

- Same provider activity ID should update existing records.
- If provider ID is unavailable for some UI item, derive a stable fallback from start time, sport, distance, and duration.
- Avoid creating duplicates when re-running a failed import.

## Running Assessment

Assessment service input:

- Last 4/8/12/24 weeks of activities.
- COROS performance metrics where available.
- User goal.
- User availability.
- User feedback and pain/fatigue signals.

Compute:

- Weekly distance trend.
- Weekly run count trend.
- Longest run and long-run distribution.
- Recent acute load and chronic load.
- Load spike risk.
- Consistency score.
- Endurance score.
- Intensity score.
- Recovery risk score.
- Goal feasibility.
- Data confidence.

Output schema:

```json
{
  "overall_score": 72,
  "readiness_level": "moderate",
  "safe_weekly_distance_range_km": [42, 58],
  "safe_training_days_range": [4, 6],
  "long_run_capacity_km": 24,
  "estimated_marathon_time_range_sec": [14300, 15400],
  "goal_status": "accept_with_warning",
  "limiting_factors": ["long_run_capacity", "recent_volume"],
  "warnings": [],
  "confidence": "medium",
  "summary": "Current data supports a sub-4:00 attempt with a 16-20 week plan if weekly volume progresses conservatively."
}
```

Goal feasibility statuses:

- `accept`
- `accept_with_warning`
- `recommend_adjustment`
- `reject`

## Marathon Plan Generation

Inputs:

- Assessment.
- Race goal.
- Training availability.
- Race date or plan weeks.
- Historical load.

Outputs:

- Plan phases.
- Weekly targets.
- Structured workouts.
- Safety warnings.

Plan rules:

- Use current safe weekly range as the starting point.
- Progress volume gradually.
- Insert down weeks.
- Cap long-run growth.
- Prefer one long run and one quality workout per week for lower/mid-level athletes.
- Add second quality workout only when consistency and recovery support it.
- Use target marathon pace only after enough base exists.
- Keep hard sessions away from long runs unless explicitly intended.
- Respect unavailable days and max session durations.

For a sub-4:00 target:

- Goal pace is about 5:41/km.
- Workouts should include easy pace, marathon pace, threshold, long run, and recovery targets.
- If the assessment does not support this goal, return a safer target or longer timeline recommendation.

## Plan Adjustment

After each import:

- Match completed COROS activities to planned workouts.
- Mark planned workouts as completed, missed, partial, or overdone.
- Update load and fatigue state.
- Store deviations.

Weekly:

- Generate adjustment recommendation for the next 7-14 days.
- Explain why the adjustment is recommended.
- Wait for user confirmation.
- On confirmation, modify future workouts and sync changes to COROS.

Immediate warning triggers:

- Pain feedback.
- Severe fatigue.
- Acute load spike.
- Multiple missed workouts.
- Long run significantly over target.
- Heart-rate drift or unusual HR response if data supports it.

## COROS Sync Pipeline

Sync target:

- Create confirmed future structured workouts in COROS.
- Place them on the COROS calendar.

Pipeline:

1. Select confirmed unsynced future workouts.
2. Open COROS Training Hub.
3. Create or update workout in library.
4. Add workout to calendar date.
5. Record provider workout/calendar IDs if visible.
6. Mark sync status.
7. On failure, preserve local plan and expose retry.

MVP behavior:

- Do not remove existing COROS items.
- Do not block multiple workouts on one date.
- If update is difficult, create a new versioned workout title and mark the old local sync record superseded.

Workout naming convention:

```text
W05D2 Marathon Pace
W05D4 Easy Run
W05D7 Long Run
```

This makes manually inspecting COROS calendar easier.

## API Surface

Suggested endpoints:

- `POST /coros/connect`
- `POST /coros/import`
- `GET /coros/status`
- `POST /athletes/{athlete_id}/assessment/run`
- `GET /athletes/{athlete_id}/assessment/latest`
- `POST /marathon/goals`
- `POST /marathon/plans/generate`
- `POST /plans/{plan_id}/confirm`
- `POST /plans/{plan_id}/sync/coros`
- `POST /plans/{plan_id}/adjustments/evaluate`
- `POST /plan-adjustments/{adjustment_id}/confirm`

Keep older generic endpoints only if they remain consistent with the new model.

## Jobs

Scheduled jobs:

- Daily COROS import.
- Daily sync retry for confirmed unsynced future workouts.
- Weekly adjustment evaluation.

Manual jobs:

- Import now.
- Sync now.
- Recompute assessment.
- Regenerate plan.

For the personal-use MVP, jobs can be implemented as direct API-triggered functions first. A scheduler can come later once the core flows are stable.

## Verification Strategy

Minimum tests:

- Credential encryption round trip.
- Activity upsert idempotency.
- Running assessment with synthetic history.
- Unsafe sub-4:00 target rejection.
- Safe sub-4:00 target acceptance or warning.
- Structured workout generation shape.
- Plan confirmation state transition.
- COROS sync service records success/failure using a fake automation client.
- Adjustment recommendation after missed workouts or high fatigue.

Manual verification:

- Connect to COROS test/personal account.
- Import history twice and confirm no duplicates.
- Generate a sub-4:00 plan.
- Confirm plan.
- Sync future 7 days to COROS.
- Confirm workouts appear in COROS calendar.
- Complete or simulate activity import and verify planned versus actual matching.

## Implementation Sequence

1. Repair current import blocker in `app/models.py`.
2. Establish Python 3.11+ local environment.
3. Add normalized activity, metric, goal, availability, structured workout, and sync record models.
4. Add credential encryption.
5. Add fake COROS automation interface and tests.
6. Implement ingestion pipeline against fake COROS data.
7. Implement running assessment.
8. Implement full-marathon goal feasibility.
9. Implement structured marathon plan generation.
10. Implement plan confirmation and sync records.
11. Implement real COROS login/import automation.
12. Implement real COROS workout/calendar sync automation.
13. Implement monitoring and weekly adjustment recommendations.

## Main Risks

- COROS page automation may break when the web app changes.
- COROS may require MFA/CAPTCHA or trigger risk controls.
- Some desired health/feedback data may not be visible or parseable.
- COROS workout creation may require complex UI interactions.
- Storing credentials, even for personal use, increases security risk.
- Training recommendations can be unsafe if assessment confidence is low and the system does not reject aggressively enough.

## Design Principle

Do not let COROS automation details leak into training logic. COROS is the first provider, but the core product should model activities, metrics, goals, workouts, and adjustments independently so later Garmin, Strava, and triathlon support do not require a rewrite.
