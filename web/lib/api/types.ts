/* ────────────────────────────────────────────────────────────
   TypeScript types mirroring the Pydantic schemas in app/schemas.py
   Run `scripts/gen_ts_types.py` to regenerate from source.
   ──────────────────────────────────────────────────────────── */

/* ── Shared ──────────────────────────────────────────────── */

export type MatchStatus = 'completed' | 'partial' | 'miss' | 'rest' | 'unmatched'

export type DayStatus = 'completed' | 'partial' | 'miss' | 'rest' | 'future'

/* ── Skills ──────────────────────────────────────────────── */

export interface SkillManifestOut {
  slug: string
  name: string
  version: string
  sport: string
  author: string | null
  tags: string[]
  description: string
  is_active: boolean
}

export interface SkillDetailOut extends SkillManifestOut {
  methodology_md: string | null
}

/* ── Workout steps ───────────────────────────────────────── */

export interface WorkoutStepOut {
  step_type: string
  duration_min: number
  distance_m: number | null
  intensity_type: string
  target_min: number | null
  target_max: number | null
  rpe_min: number | null
  rpe_max: number | null
  description: string | null
}

/* ── Structured workout ──────────────────────────────────── */

export interface StructuredWorkoutOut {
  id: number
  week_index: number
  weekday: number
  discipline: string
  workout_type: string
  title: string
  purpose: string
  duration_min: number
  distance_m: number | null
  target_intensity_type: string
  target_min: number | null
  target_max: number | null
  rpe_min: number | null
  rpe_max: number | null
  adaptation_notes: string | null
  steps: WorkoutStepOut[]
}

/* ── Today endpoint ──────────────────────────────────────── */

export interface TodayMatchedActivity {
  id: number
  distance_m: number
  duration_sec: number
  avg_pace_sec_per_km: number | null
  status: MatchStatus
}

export interface TodayOut {
  plan_id: number
  week_index: number
  workout: StructuredWorkoutOut | null
  matched_activity: TodayMatchedActivity | null
  yesterday_workout: StructuredWorkoutOut | null
  yesterday_activity: TodayMatchedActivity | null
  recovery_recommendation: RecoveryRecommendation | null
}

export interface RecoveryRecommendation {
  degraded_workout: Partial<StructuredWorkoutOut>
  ethos_quote: string
}

/* ── Week endpoint ───────────────────────────────────────── */

export interface WeekDay {
  date: string          // ISO date
  weekday: number       // 0=Mon … 6=Sun
  title: string | null
  distance_km: number | null
  duration_min: number | null
  status: DayStatus
}

export interface WeekOut {
  plan_id: number
  week_index: number
  total_weeks: number
  phase: string | null
  is_recovery: boolean
  days: WeekDay[]
  completed_km: number
  planned_km: number
  completed_quality: number
  planned_quality: number
}

/* ── Activity history ────────────────────────────────────── */

export interface AthleteActivityOut {
  id: number
  athlete_id?: number
  provider?: string
  provider_activity_id?: string
  sport?: string
  discipline?: string
  started_at: string
  title?: string
  distance_km?: number
  duration_min?: number
  distance_m?: number
  duration_sec?: number
  elevation_gain_m?: number | null
  avg_pace_sec_per_km: number | null
  avg_hr: number | null
  training_load?: number | null
  perceived_effort?: number | null
  feedback_text?: string | null
  matched_workout_title: string | null
  matched_workout_planned_distance_m?: number | null
  match_status: MatchStatus
  delta_summary: string | null
}

export interface ActivityDetailSampleOut {
  sample_index: number
  timestamp: string
  elapsed_sec: number | null
  distance_m: number | null
  latitude: number | null
  longitude: number | null
  altitude_m: number | null
  heart_rate: number | null
  cadence: number | null
  speed_mps: number | null
  pace_sec_per_km: number | null
  power_w: number | null
  temperature_c: number | null
}

export interface ActivityDetailLapOut {
  lap_index: number
  start_time: string | null
  end_time: string | null
  duration_sec: number | null
  distance_m: number | null
  avg_hr: number | null
  max_hr: number | null
  min_hr: number | null
  avg_cadence: number | null
  max_cadence: number | null
  avg_speed_mps: number | null
  max_speed_mps: number | null
  avg_power_w: number | null
  elevation_gain_m: number | null
  elevation_loss_m: number | null
  calories: number | null
  avg_temperature_c: number | null
}

export interface ActivityDetailSourceOut {
  source_format: string
  file_size_bytes: number
  payload_hash: string
  file_url_host: string | null
  downloaded_at: string
  parsed_at: string | null
  stored_sample_count: number
  stored_lap_count: number
  warnings: string[]
}

export interface ActivityDetailRouteBoundsOut {
  min_latitude: number | null
  max_latitude: number | null
  min_longitude: number | null
  max_longitude: number | null
}

export interface ActivityDetailInterpretationOut {
  effort_distribution: string
  pace_consistency: string
  heart_rate_drift: string
  data_quality: string
}

export interface ActivityDetailOut {
  activity: AthleteActivityOut
  source: ActivityDetailSourceOut | null
  samples: ActivityDetailSampleOut[]
  laps: ActivityDetailLapOut[]
  route_bounds: ActivityDetailRouteBoundsOut
  interpretation: ActivityDetailInterpretationOut
  returned_sample_count: number
}

/* ── Dashboard aggregate ─────────────────────────────────── */

export interface DashboardAthlete {
  id: number
  name: string
  current_skill: { slug: string; name: string; version: string } | null
}

export interface DashboardGreeting {
  time_of_day: string
  date: string
  weekday_short: string
  week_index: number
  week_phase: string | null
}

export interface DashboardToday {
  plan_id: number
  week_index: number
  workout: StructuredWorkoutOut | null
  matched_activity: TodayMatchedActivity | null
}

export interface DashboardThisWeek {
  plan_id: number
  week_index: number
  total_weeks: number
  phase: string | null
  is_recovery: boolean
  days: WeekDay[]
  completed_km: number
  planned_km: number
  completed_quality: number
  planned_quality: number
}

export interface DashboardGoal {
  label: string
  race_date: string
  days_until: number
  target_time_sec: number
  prediction_history: Array<{ measured_at: string; predicted_time_sec: number }>
  monthly_delta_sec: number
}

export interface DashboardVolumeWeek {
  week_index: number
  week_label: string
  executed_km: number
  planned_km: number
  completion_pct: number
}

export interface DashboardActivity {
  id: number
  started_at: string
  title: string
  distance_km: number
  duration_min: number
  avg_pace_sec_per_km: number | null
  avg_hr: number | null
  match_status: MatchStatus
  delta_summary: string | null
}

export interface DashboardReadiness {
  resting_hr: number | null
  resting_hr_trend: number | null
  weekly_training_load: number | null
  weekly_training_load_trend: number | null
  lthr: number | null
  ltsp_sec_per_km: number | null
}

export interface DashboardMeta {
  skill_slug: string
  skill_name: string
  skill_version: string
  last_sync_at: string | null
  last_sync_status: string | null
}

export interface DashboardOut {
  athlete: DashboardAthlete
  greeting: DashboardGreeting
  pending_adjustment: { id: number; reason_headline: string } | null
  today: DashboardToday
  this_week: DashboardThisWeek
  goal: DashboardGoal | null
  volume_history: DashboardVolumeWeek[]
  recent_activities: DashboardActivity[]
  readiness: DashboardReadiness
  meta: DashboardMeta
}

/* ── Volume curve ────────────────────────────────────────── */

export interface VolumeCurveWeek {
  week_index: number
  week_label: string
  executed_km: number
  planned_km: number
  phase: string | null
  is_recovery: boolean
}

export interface VolumeCurveOut {
  plan_id: number
  weeks: VolumeCurveWeek[]
  peak_planned_km: number
  peak_executed_km: number
}

/* ── Regenerate preview ──────────────────────────────────── */

export interface RegeneratePreviewOut {
  frozen_completed: number
  frozen_missed: number
  regenerated_count: number
  weeks_affected: number
  applicable: boolean
  applicability_reason: string
}

/* ── Adjustment ──────────────────────────────────────────── */

export interface AffectedWorkout {
  workout_id: number
  date: string
  title: string
  change_summary: string
  before: Record<string, unknown>
  after: Record<string, unknown>
}

export interface PlanAdjustmentOut {
  id: number
  reason_headline: string
  recommendation_text: string | null
  affected_workouts: AffectedWorkout[]
  status: string
  created_at: string
}

/* ── Coach messages ──────────────────────────────────────── */

export interface SuggestedAction {
  label: string
  action_type: string
  payload: Record<string, unknown> | null
}

export interface CoachMessage {
  id: number
  athlete_id: number
  role: 'user' | 'coach'
  text: string
  suggested_actions: SuggestedAction[]
  created_at: string
}

export interface CoachMessageIn {
  athlete_id: number
  text: string
}

/* ── Workout feedback ────────────────────────────────────── */

export interface WorkoutFeedbackIn {
  status: 'completed' | 'partial' | 'skipped'
  rpe_actual: number | null
  notes: string | null
}

export interface WorkoutFeedbackOut {
  id: number
  workout_id: number
  status: string
  rpe_actual: number | null
  notes: string | null
  recorded_at: string
}

/* ── Helpers ─────────────────────────────────────────────── */

export function formatPace(secPerKm: number | null): string {
  if (!secPerKm) return '--'
  const m = Math.floor(secPerKm / 60)
  const s = Math.round(secPerKm % 60)
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatTime(sec: number): string {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = Math.round(sec % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function formatKm(m: number | null): string {
  if (!m) return '--'
  return (m / 1000).toFixed(1)
}

/* ── Running assessment ──────────────────────────────────── */

export interface RunningAssessmentOut {
  athlete_id: number
  overall_score: number
  readiness_level: string
  safe_weekly_distance_range_km: number[]
  safe_training_days_range: number[]
  long_run_capacity_km: number
  estimated_marathon_time_range_sec: number[]
  goal_status: string
  limiting_factors: string[]
  warnings: string[]
  confidence: string
  summary: string
}

/* ── COROS import result ─────────────────────────────────── */

export interface CorosStatusOut {
  athlete_id: number
  connected: boolean
  auth_status: string
  automation_mode: string
  username: string | null
  last_login_at: string | null
  last_import_at: string | null
  last_sync_at: string | null
  last_error: string | null
}

export interface DeviceAccountOut {
  id: number
  athlete_id: number
  device_type: string
  external_user_id: string
  username: string | null
  auth_status: string
  last_login_at: string | null
  last_import_at: string | null
  last_sync_at: string | null
  last_error: string | null
  created_at: string
}

export interface HistoryImportOut {
  athlete_id: number
  provider: string
  imported_count: number
  updated_count: number
  metric_count: number
  message: string
}

export interface ProviderSyncJobOut {
  id: number
  athlete_id: number
  provider: string
  status: string
  phase: string
  message: string | null
  total_count: number
  processed_count: number
  imported_count: number
  updated_count: number
  metric_count: number
  failed_count: number
  raw_record_count: number
  sync_days_back: number | null
  started_at: string | null
  completed_at: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ProviderSyncEventOut {
  id: number
  job_id: number
  level: string
  phase: string
  message: string
  processed_count: number | null
  total_count: number | null
  created_at: string
}

/* ── Calendar ────────────────────────────────────────────── */

export type CalendarStatus = 'completed' | 'partial' | 'miss' | 'unmatched' | 'planned'

export interface CalendarDay {
  date: string               // YYYY-MM-DD
  status: CalendarStatus
  title: string | null
  sport: string | null       // discipline: run | cycle | strength
  workout_type: string | null
  activity_id: number | null
  workout_id: number | null
  distance_km: number | null
  duration_min: number | null
}
