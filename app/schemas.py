from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import (
    AdjustmentStatus,
    AthleteLevel,
    DeviceType,
    PlanStatus,
    RaceGoalStatus,
    SportType,
    SyncStatus,
    TrainingGoal,
    TrainingMode,
    WorkoutStatus,
)


class AthleteCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    sport: SportType
    level: AthleteLevel = AthleteLevel.BEGINNER
    weekly_training_days: int = Field(default=4, ge=2, le=7)
    weekly_training_hours: int | None = Field(default=None, ge=1, le=30)
    notes: str | None = None


class AthleteOut(AthleteCreate):
    id: int

    model_config = {"from_attributes": True}


class TrainingMethodOut(BaseModel):
    id: int
    sport: SportType
    name: str
    summary: str
    focus: str
    default_mode: TrainingMode

    model_config = {"from_attributes": True}


class ModeRecommendationOut(BaseModel):
    mode: TrainingMode
    description: str
    suitable_goals: list[TrainingGoal]
    rationale: str


class PlanGenerateRequest(BaseModel):
    athlete_id: int
    sport: SportType | None = None
    goal: TrainingGoal
    weeks: int = Field(ge=4, le=24)
    mode: TrainingMode | None = None
    weekly_days: int | None = Field(default=None, ge=2, le=7)


class TrainingSessionOut(BaseModel):
    id: int
    week_index: int
    day_index: int
    discipline: str
    session_type: str
    duration_min: int
    intensity: str
    notes: str | None

    model_config = {"from_attributes": True}


class TrainingPlanOut(BaseModel):
    id: int
    athlete_id: int
    sport: SportType
    goal: TrainingGoal
    mode: TrainingMode
    weeks: int
    status: PlanStatus
    created_at: datetime
    updated_at: datetime
    sessions: list[TrainingSessionOut]

    model_config = {"from_attributes": True}


class PlanStatusUpdate(BaseModel):
    status: PlanStatus


class DeviceConnectRequest(BaseModel):
    athlete_id: int
    device_type: DeviceType
    external_user_id: str = Field(min_length=1, max_length=120)


class DeviceAccountOut(BaseModel):
    id: int
    athlete_id: int
    device_type: DeviceType
    external_user_id: str
    username: str | None = None
    auth_status: str = "disconnected"
    last_login_at: datetime | None = None
    last_import_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SyncPlanRequest(BaseModel):
    device_type: DeviceType


class SyncTaskOut(BaseModel):
    id: int
    plan_id: int
    device_type: DeviceType
    status: SyncStatus
    details: str | None
    synced_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class CorosConnectRequest(BaseModel):
    athlete_id: int
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=240)


class CorosStatusOut(BaseModel):
    athlete_id: int
    connected: bool
    auth_status: str
    automation_mode: str = "fake"
    username: str | None = None
    last_login_at: datetime | None = None
    last_import_at: datetime | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None


class HistoryImportRequest(BaseModel):
    device_type: DeviceType = DeviceType.COROS


class HistoryImportOut(BaseModel):
    athlete_id: int
    provider: str
    imported_count: int
    updated_count: int
    metric_count: int = 0
    message: str


class CorosSyncStartRequest(BaseModel):
    athlete_id: int


class ProviderSyncJobOut(BaseModel):
    id: int
    athlete_id: int
    provider: str
    status: str
    phase: str
    message: str | None = None
    total_count: int = 0
    processed_count: int = 0
    imported_count: int = 0
    updated_count: int = 0
    metric_count: int = 0
    failed_count: int = 0
    raw_record_count: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderSyncEventOut(BaseModel):
    id: int
    job_id: int
    level: str
    phase: str
    message: str
    processed_count: int | None = None
    total_count: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CalendarDayOut(BaseModel):
    date: str                      # YYYY-MM-DD
    status: str                    # completed | partial | miss | unmatched | planned
    title: str | None = None
    sport: str | None = None       # discipline: run | cycle | strength
    workout_type: str | None = None
    activity_id: int | None = None
    workout_id: int | None = None
    distance_km: float | None = None
    duration_min: int | None = None


class AthleteActivityOut(BaseModel):
    id: int
    athlete_id: int
    provider: str
    provider_activity_id: str
    sport: str
    discipline: str
    started_at: datetime
    duration_sec: int
    distance_m: float
    elevation_gain_m: float | None = None
    avg_pace_sec_per_km: float | None = None
    avg_hr: float | None = None
    training_load: float | None = None
    perceived_effort: int | None = None
    feedback_text: str | None = None
    matched_workout_id: int | None = None
    matched_workout_title: str | None = None
    match_status: str = "unmatched"  # completed | partial | miss | rest | unmatched
    delta_summary: str | None = None

    model_config = {"from_attributes": True}


class ActivityDetailSampleOut(BaseModel):
    sample_index: int
    timestamp: datetime
    elapsed_sec: float | None = None
    distance_m: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    altitude_m: float | None = None
    heart_rate: float | None = None
    cadence: float | None = None
    speed_mps: float | None = None
    pace_sec_per_km: float | None = None
    power_w: float | None = None
    temperature_c: float | None = None

    model_config = {"from_attributes": True}


class ActivityDetailLapOut(BaseModel):
    lap_index: int
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_sec: float | None = None
    distance_m: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    min_hr: float | None = None
    avg_cadence: float | None = None
    max_cadence: float | None = None
    avg_speed_mps: float | None = None
    max_speed_mps: float | None = None
    avg_power_w: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    calories: float | None = None
    avg_temperature_c: float | None = None

    model_config = {"from_attributes": True}


class ActivityDetailSourceOut(BaseModel):
    source_format: str
    file_size_bytes: int
    payload_hash: str
    file_url_host: str | None = None
    downloaded_at: datetime
    parsed_at: datetime | None = None
    stored_sample_count: int
    stored_lap_count: int
    warnings: list[str] = []


class ActivityDetailRouteBoundsOut(BaseModel):
    min_latitude: float | None = None
    max_latitude: float | None = None
    min_longitude: float | None = None
    max_longitude: float | None = None


class ActivityDetailInterpretationOut(BaseModel):
    effort_distribution: str
    pace_consistency: str
    heart_rate_drift: str
    data_quality: str


class ActivityDetailOut(BaseModel):
    activity: AthleteActivityOut
    source: ActivityDetailSourceOut | None = None
    samples: list[ActivityDetailSampleOut] = []
    laps: list[ActivityDetailLapOut] = []
    route_bounds: ActivityDetailRouteBoundsOut
    interpretation: ActivityDetailInterpretationOut
    returned_sample_count: int


class RunningAssessmentOut(BaseModel):
    athlete_id: int
    overall_score: int
    readiness_level: str
    safe_weekly_distance_range_km: list[float]
    safe_training_days_range: list[int]
    long_run_capacity_km: float
    estimated_marathon_time_range_sec: list[int]
    goal_status: str
    limiting_factors: list[str]
    warnings: list[str]
    confidence: str
    summary: str


class TrainingAvailabilityIn(BaseModel):
    weekly_training_days: int = Field(default=5, ge=2, le=7)
    preferred_long_run_weekday: int = Field(default=6, ge=0, le=6)
    unavailable_weekdays: list[int] = Field(default_factory=list)
    max_weekday_duration_min: int | None = Field(default=None, ge=20, le=240)
    max_weekend_duration_min: int | None = Field(default=None, ge=30, le=420)
    strength_training_enabled: bool = True
    notes: str | None = None


class TrainingAvailabilityOut(BaseModel):
    id: int
    athlete_id: int
    weekly_training_days: int
    preferred_long_run_weekday: int
    unavailable_weekdays: str | None
    max_weekday_duration_min: int | None
    max_weekend_duration_min: int | None
    strength_training_enabled: bool
    notes: str | None

    model_config = {"from_attributes": True}


class MarathonGoalCreate(BaseModel):
    athlete_id: int
    target_time_sec: int | None = Field(default=None, ge=7200, le=28800)
    race_date: date | None = None
    training_start_date: date | None = None
    plan_weeks: int = Field(default=16, ge=4, le=30)
    availability: TrainingAvailabilityIn = Field(default_factory=TrainingAvailabilityIn)


class RaceGoalOut(BaseModel):
    id: int
    athlete_id: int
    sport: SportType
    distance: str
    target_type: str
    target_time_sec: int | None
    race_date: date | None
    training_start_date: date | None
    plan_weeks: int
    status: RaceGoalStatus
    feasibility_summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class WorkoutStepOut(BaseModel):
    id: int
    step_index: int
    step_type: str
    duration_sec: int | None
    distance_m: float | None
    target_type: str
    target_min: float | None
    target_max: float | None
    repeat_count: int | None
    notes: str | None

    model_config = {"from_attributes": True}


class StructuredWorkoutOut(BaseModel):
    id: int
    scheduled_date: date
    week_index: int
    day_index: int
    discipline: str
    workout_type: str
    title: str
    purpose: str
    duration_min: int
    distance_m: float | None
    target_intensity_type: str
    target_pace_min_sec_per_km: float | None
    target_pace_max_sec_per_km: float | None
    status: WorkoutStatus
    adaptation_notes: str | None
    steps: list[WorkoutStepOut] = []

    model_config = {"from_attributes": True}


class MarathonPlanGenerateRequest(BaseModel):
    athlete_id: int
    race_goal_id: int | None = None
    target_time_sec: int | None = Field(default=None, ge=7200, le=28800)
    race_date: date | None = None
    training_start_date: date | None = None
    plan_weeks: int = Field(default=16, ge=4, le=30)
    availability: TrainingAvailabilityIn = Field(default_factory=TrainingAvailabilityIn)
    skill_slug: str = Field(default="marathon_st_default", min_length=1, max_length=120)


class MarathonPlanOut(BaseModel):
    id: int
    athlete_id: int
    race_goal_id: int | None
    title: str | None
    sport: SportType
    goal: TrainingGoal
    mode: TrainingMode
    weeks: int
    status: PlanStatus
    start_date: date | None
    race_date: date | None
    target_time_sec: int | None
    is_confirmed: bool
    created_at: datetime
    updated_at: datetime
    structured_workouts: list[StructuredWorkoutOut] = []

    model_config = {"from_attributes": True}


class PlanConfirmOut(BaseModel):
    plan_id: int
    confirmed: bool
    confirmed_workout_count: int


class ProviderSyncRecordOut(BaseModel):
    id: int
    athlete_id: int
    plan_id: int
    workout_id: int | None
    provider: str
    provider_workout_id: str | None
    provider_calendar_item_id: str | None
    sync_status: SyncStatus
    attempted_at: datetime
    synced_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class PlanSyncOut(BaseModel):
    plan_id: int
    provider: str
    synced_count: int
    failed_count: int
    records: list[ProviderSyncRecordOut]


class PlanAdjustmentOut(BaseModel):
    id: int
    athlete_id: int
    plan_id: int
    status: AdjustmentStatus
    reason: str
    recommendation: str
    effective_start_date: date | None
    effective_end_date: date | None
    created_at: datetime
    confirmed_at: datetime | None

    model_config = {"from_attributes": True}


# ── Block A schemas ──────────────────────────────────────────────────────────


class SkillManifestOut(BaseModel):
    slug: str
    name: str
    version: str
    sport: str
    supported_goals: list[str]
    description: str
    author: str = ""
    tags: list[str] = []
    requires_llm: bool = False


class SkillDetailOut(SkillManifestOut):
    methodology_md: str


class TodayOut(BaseModel):
    plan_id: int | None
    plan_title: str | None
    skill_slug: str | None
    week_index: int | None
    workout: StructuredWorkoutOut | None
    matched_activity_id: int | None
    yesterday_workout: StructuredWorkoutOut | None = None
    yesterday_activity: AthleteActivityOut | None = None
    recovery_recommendation: dict | None = None


class WeekOut(BaseModel):
    plan_id: int
    week_index: int
    phase: str  # "base" | "block" | "taper" | "unknown"
    is_recovery: bool
    total_distance_m: float
    total_duration_min: int
    quality_count: int
    workouts: list[StructuredWorkoutOut]


class WorkoutFeedbackIn(BaseModel):
    status: str = Field(min_length=1)
    rpe: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=500)


class WorkoutFeedbackOut(BaseModel):
    id: int
    workout_id: int
    status: str
    rpe: int | None
    note: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RegenerateFromTodayRequest(BaseModel):
    skill_slug: str = Field(min_length=1, max_length=120)


class RegenerateFromTodayOut(BaseModel):
    plan_id: int
    frozen_count: int
    regenerated_count: int
    new_skill_slug: str


class MatchDiff(BaseModel):
    distance_pct: float | None
    duration_pct: float | None
    avg_pace_diff_sec_per_km: float | None


class WorkoutMatchStatusOut(BaseModel):
    workout_id: int
    matched_activity: AthleteActivityOut | None
    diff: MatchDiff | None


# ── Block A1 schemas ─────────────────────────────────────────────────────────


class DashboardAthleteRef(BaseModel):
    id: int
    name: str
    current_skill: SkillManifestOut | None = None


class DashboardGreeting(BaseModel):
    time_of_day: str  # "morning" | "afternoon" | "evening"
    date: str  # ISO YYYY-MM-DD
    weekday_short: str  # Mon..Sun
    week_index: int | None = None
    week_phase: str | None = None


class DashboardTodaySection(BaseModel):
    plan_id: int | None = None
    week_index: int | None = None
    workout: StructuredWorkoutOut | None = None
    matched_activity: AthleteActivityOut | None = None
    match_status: str | None = None  # completed | partial | miss | rest | unmatched | null


class DashboardWeekDay(BaseModel):
    date: date
    weekday: int  # 0=Mon..6=Sun
    title: str | None = None
    distance_km: float = 0.0
    duration_min: int = 0
    status: str  # done | partial | miss | today | plan | rest


class DashboardThisWeek(BaseModel):
    plan_id: int | None = None
    week_index: int | None = None
    total_weeks: int | None = None
    phase: str | None = None
    is_recovery: bool = False
    days: list[DashboardWeekDay] = []
    completed_km: float = 0.0
    planned_km: float = 0.0
    completed_quality: int = 0
    planned_quality: int = 0


class DashboardGoal(BaseModel):
    label: str | None = None  # e.g. "sub-3:30"
    race_date: date | None = None
    days_until: int | None = None
    target_time_sec: int | None = None
    prediction_history: list[dict] = []
    monthly_delta_sec: int | None = None  # negative = faster (good)


class DashboardVolumeWeek(BaseModel):
    week_index: int
    week_label: str
    executed_km: float
    planned_km: float
    completion_pct: float
    is_current: bool


class DashboardRecentActivity(BaseModel):
    id: int
    started_at: datetime
    title: str
    distance_km: float
    duration_min: int
    avg_pace_sec_per_km: float | None = None
    avg_hr: int | None = None
    match_status: str
    delta_summary: str | None = None


class DashboardReadiness(BaseModel):
    resting_hr: int | None = None
    resting_hr_trend: str | None = None  # "down" | "up" | "flat"
    weekly_training_load: int | None = None
    weekly_training_load_trend: str | None = None
    lthr: int | None = None
    ltsp_sec_per_km: float | None = None


class DashboardMeta(BaseModel):
    skill_slug: str | None = None
    skill_name: str | None = None
    skill_version: str | None = None
    last_sync_at: datetime | None = None
    last_sync_status: str | None = None  # ok | error | never


class DashboardOut(BaseModel):
    athlete: DashboardAthleteRef
    greeting: DashboardGreeting
    pending_adjustment: dict | None = None
    today: DashboardTodaySection
    this_week: DashboardThisWeek
    goal: DashboardGoal
    volume_history: list[DashboardVolumeWeek] = []
    recent_activities: list[DashboardRecentActivity] = []
    readiness: DashboardReadiness
    meta: DashboardMeta


class PlanVolumeCurvePoint(BaseModel):
    week_index: int
    phase: str
    is_recovery: bool
    is_current: bool
    planned_km: float
    executed_km: float
    longest_run_km: float


class PlanVolumeCurveOut(BaseModel):
    plan_id: int
    weeks: list[PlanVolumeCurvePoint]
    peak_planned_km: float
    peak_executed_km: float


class RegeneratePreviewOut(BaseModel):
    plan_id: int
    new_skill_slug: str
    applicable: bool
    applicability_reason: str
    frozen_completed: int
    frozen_missed: int
    regenerated_count: int
    weeks_affected: int
    days_affected_start: date | None
    days_affected_end: date | None


class AdjustmentAffectedWorkout(BaseModel):
    workout_id: int
    date: date
    title: str
    field: str  # "distance_m" | "duration_min" | "skip" | "workout_type"
    before: str
    after: str
    note: str | None = None


class PlanAdjustmentDetailOut(PlanAdjustmentOut):
    affected_workouts: list[AdjustmentAffectedWorkout] = []


class PlanAdjustmentApplyRequest(BaseModel):
    selected_workout_ids: list[int] | None = None


class CoachMessageOut(BaseModel):
    id: int
    athlete_id: int
    role: str
    text: str
    suggested_actions_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CoachMessageRequest(BaseModel):
    athlete_id: int
    message: str = Field(min_length=1, max_length=4000)


class CoachMessageResponse(BaseModel):
    user_message: CoachMessageOut
    coach_message: CoachMessageOut


# ── Auth schemas ─────────────────────────────────────────────────────────────

class SendOTPRequest(BaseModel):
    phone: str | None = Field(default=None, min_length=8, max_length=24)
    country_code: str | None = Field(default=None, min_length=2, max_length=5)
    national_number: str | None = Field(default=None, min_length=4, max_length=24)


class SendOTPResponse(BaseModel):
    message: str
    otp_code: int | None = None  # mock-only local/dev convenience


class VerifyOTPRequest(BaseModel):
    phone: str | None = Field(default=None, min_length=8, max_length=24)
    country_code: str | None = Field(default=None, min_length=2, max_length=5)
    national_number: str | None = Field(default=None, min_length=4, max_length=24)
    code: str = Field(min_length=6, max_length=6)


class VerifyOTPResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    is_new_user: bool


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=10)


class PasskeyRegistrationStartResponse(BaseModel):
    options: dict


class PasskeyRegistrationFinishRequest(BaseModel):
    credential: dict
    name: str | None = Field(default=None, max_length=120)


class PasskeyAuthenticationStartRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)


class PasskeyAuthenticationStartResponse(BaseModel):
    options: dict


class PasskeyAuthenticationFinishRequest(BaseModel):
    credential: dict


class PhoneLinkStartRequest(SendOTPRequest):
    pass


class PhoneLinkFinishRequest(VerifyOTPRequest):
    pass


class UserOut(BaseModel):
    id: int
    phone: str | None = None
    email: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None

    model_config = {"from_attributes": True}
