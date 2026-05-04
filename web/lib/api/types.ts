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
  started_at: string
  title: string
  distance_km: number
  duration_min: number
  avg_pace_sec_per_km: number | null
  avg_hr: number | null
  matched_workout_title: string | null
  matched_workout_planned_distance_m: number | null
  match_status: MatchStatus
  delta_summary: string | null
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

export interface HistoryImportOut {
  athlete_id: number
  provider: string
  imported_count: number
  updated_count: number
  metric_count: number
  message: string
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
