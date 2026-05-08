from __future__ import annotations

from datetime import UTC, date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class SportType(str, Enum):
    MARATHON = "marathon"
    TRAIL_RUNNING = "trail_running"
    TRIATHLON = "triathlon"


class AthleteLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class TrainingGoal(str, Enum):
    FINISH = "finish"
    IMPROVE_PACE = "improve_pace"
    INCREASE_ENDURANCE = "increase_endurance"
    RACE_SPECIFIC = "race_specific"


class TrainingMode(str, Enum):
    POLARIZED = "polarized"
    PYRAMIDAL = "pyramidal"
    THRESHOLD_FOCUSED = "threshold_focused"
    BASE_BUILD_PEAK = "base_build_peak"


class PlanStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DeviceType(str, Enum):
    GARMIN = "garmin"
    COROS = "coros"


class SyncStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"


class AuthProvider(str, Enum):
    PHONE = "phone"
    EMAIL = "email"
    GOOGLE = "google"
    PASSKEY = "passkey"


class AuthChallengePurpose(str, Enum):
    OTP_SEND = "otp_send"
    OTP_VERIFY_FAIL = "otp_verify_fail"
    PASSKEY_REGISTER = "passkey_register"
    PASSKEY_LOGIN = "passkey_login"


class RaceGoalStatus(str, Enum):
    DRAFT = "draft"
    ACCEPTED = "accepted"
    WARNING = "warning"
    REJECTED = "rejected"


class WorkoutStatus(str, Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    SYNCED = "synced"
    COMPLETED = "completed"
    MISSED = "missed"


class AdjustmentStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"


class TrainingMethod(Base):
    __tablename__ = "training_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    sport: Mapped[SportType] = mapped_column(SqlEnum(SportType), index=True)
    name: Mapped[str] = mapped_column(String(120))
    summary: Mapped[str] = mapped_column(Text)
    focus: Mapped[str] = mapped_column(String(120))
    default_mode: Mapped[TrainingMode] = mapped_column(SqlEnum(TrainingMode))


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    _legacy_phone: Mapped[Optional[str]] = mapped_column("phone", String(20), unique=True, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    athletes: Mapped[list["AthleteProfile"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    account_aliases: Mapped[list["AccountAlias"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def _alias_for(self, provider: AuthProvider) -> Optional["AccountAlias"]:
        for alias in self.account_aliases:
            if alias.provider == provider:
                return alias
        return None

    @property
    def phone(self) -> Optional[str]:
        alias = self._alias_for(AuthProvider.PHONE)
        return alias.provider_subject if alias else self._legacy_phone

    @property
    def email(self) -> Optional[str]:
        alias = self._alias_for(AuthProvider.EMAIL) or self._alias_for(AuthProvider.GOOGLE)
        return alias.email or alias.provider_subject if alias else None

    @property
    def display_name(self) -> Optional[str]:
        for provider in (AuthProvider.GOOGLE, AuthProvider.EMAIL, AuthProvider.PHONE):
            alias = self._alias_for(provider)
            if alias and alias.display_name:
                return alias.display_name
        return None

    @property
    def avatar_url(self) -> Optional[str]:
        alias = self._alias_for(AuthProvider.GOOGLE)
        return alias.avatar_url if alias else None


class AccountAlias(Base):
    __tablename__ = "account_aliases"
    __table_args__ = (UniqueConstraint("provider", "provider_subject", name="uq_account_alias_provider_subject"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    provider: Mapped[AuthProvider] = mapped_column(SqlEnum(AuthProvider), index=True)
    provider_subject: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="account_aliases")


class WebAuthnCredential(Base):
    __tablename__ = "webauthn_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True)
    credential_id: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="webauthn_credentials")


class AuthChallenge(Base):
    __tablename__ = "auth_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    purpose: Mapped[AuthChallengePurpose] = mapped_column(SqlEnum(AuthChallengePurpose), index=True)
    subject: Mapped[str] = mapped_column(String(255), index=True)
    challenge: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(80), index=True, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    code: Mapped[str] = mapped_column(String(6))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class AthleteProfile(Base):
    __tablename__ = "athlete_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    sport: Mapped[SportType] = mapped_column(SqlEnum(SportType), index=True)
    level: Mapped[AthleteLevel] = mapped_column(SqlEnum(AthleteLevel), default=AthleteLevel.BEGINNER)
    weekly_training_days: Mapped[int] = mapped_column(Integer, default=4)
    weekly_training_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    device_accounts: Mapped[list["DeviceAccount"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    activities: Mapped[list["AthleteActivity"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    activity_detail_exports: Mapped[list["ActivityDetailExport"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    metric_snapshots: Mapped[list["AthleteMetricSnapshot"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    provider_raw_records: Mapped[list["ProviderRawRecord"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    provider_sync_jobs: Mapped[list["ProviderSyncJob"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    race_goals: Mapped[list["RaceGoal"]] = relationship(back_populates="athlete", cascade="all, delete-orphan")
    availability: Mapped[Optional["TrainingAvailability"]] = relationship(
        back_populates="athlete", cascade="all, delete-orphan"
    )
    user: Mapped[Optional["User"]] = relationship(back_populates="athletes")


class TrainingPlan(Base):
    __tablename__ = "training_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    race_goal_id: Mapped[Optional[int]] = mapped_column(ForeignKey("race_goals.id"), nullable=True)
    sport: Mapped[SportType] = mapped_column(SqlEnum(SportType), index=True)
    goal: Mapped[TrainingGoal] = mapped_column(SqlEnum(TrainingGoal))
    mode: Mapped[TrainingMode] = mapped_column(SqlEnum(TrainingMode))
    weeks: Mapped[int] = mapped_column(Integer)
    status: Mapped[PlanStatus] = mapped_column(SqlEnum(PlanStatus), default=PlanStatus.DRAFT)
    title: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    race_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    target_time_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    active_skill_slug: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="plans")
    race_goal: Mapped[Optional["RaceGoal"]] = relationship(back_populates="plans")
    sessions: Mapped[list["TrainingSession"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="TrainingSession.id"
    )
    structured_workouts: Mapped[list["StructuredWorkout"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="StructuredWorkout.scheduled_date"
    )
    sync_tasks: Mapped[list["SyncTask"]] = relationship(back_populates="plan", cascade="all, delete-orphan")
    provider_sync_records: Mapped[list["ProviderSyncRecord"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    adjustments: Mapped[list["PlanAdjustment"]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="PlanAdjustment.id"
    )


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id"), index=True)
    week_index: Mapped[int] = mapped_column(Integer)
    day_index: Mapped[int] = mapped_column(Integer)
    discipline: Mapped[str] = mapped_column(String(40))
    session_type: Mapped[str] = mapped_column(String(120))
    duration_min: Mapped[int] = mapped_column(Integer)
    intensity: Mapped[str] = mapped_column(String(32))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="sessions")


class DeviceAccount(Base):
    __tablename__ = "device_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    device_type: Mapped[DeviceType] = mapped_column(SqlEnum(DeviceType))
    external_user_id: Mapped[str] = mapped_column(String(120), default="")
    username: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    encrypted_password: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auth_status: Mapped[str] = mapped_column(String(40), default="disconnected")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_import_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="device_accounts")


class SyncTask(Base):
    __tablename__ = "sync_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id"), index=True)
    device_type: Mapped[DeviceType] = mapped_column(SqlEnum(DeviceType))
    status: Mapped[SyncStatus] = mapped_column(SqlEnum(SyncStatus), default=SyncStatus.PENDING)
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    plan: Mapped["TrainingPlan"] = relationship(back_populates="sync_tasks")


class AthleteActivity(Base):
    __tablename__ = "athlete_activities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_activity_id", name="uq_activity_provider_activity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_activity_id: Mapped[str] = mapped_column(String(160), index=True)
    sport: Mapped[str] = mapped_column(String(40), default="running")
    discipline: Mapped[str] = mapped_column(String(40), default="run")
    started_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer)
    moving_duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float] = mapped_column(Float)
    elevation_gain_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_pace_sec_per_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_cadence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_power: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_load: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    perceived_effort: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matched_workout_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("structured_workouts.id"), nullable=True, index=True
    )
    raw_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="activities")
    laps: Mapped[list["ActivityLap"]] = relationship(back_populates="activity", cascade="all, delete-orphan")
    detail_exports: Mapped[list["ActivityDetailExport"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="ActivityDetailExport.id"
    )
    detail_samples: Mapped[list["ActivityDetailSample"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="ActivityDetailSample.sample_index"
    )
    detail_laps: Mapped[list["ActivityDetailLap"]] = relationship(
        back_populates="activity", cascade="all, delete-orphan", order_by="ActivityDetailLap.lap_index"
    )
    matched_workout: Mapped[Optional["StructuredWorkout"]] = relationship(foreign_keys=[matched_workout_id])


class ActivityLap(Base):
    __tablename__ = "activity_laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("athlete_activities.id"), index=True)
    lap_index: Mapped[int] = mapped_column(Integer)
    duration_sec: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[float] = mapped_column(Float)
    avg_pace_sec_per_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    activity: Mapped["AthleteActivity"] = relationship(back_populates="laps")


class ActivityDetailExport(Base):
    __tablename__ = "activity_detail_exports"
    __table_args__ = (
        UniqueConstraint("activity_id", "source_format", name="uq_activity_detail_export_format"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("athlete_activities.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_activity_id: Mapped[str] = mapped_column(String(160), index=True)
    source_format: Mapped[str] = mapped_column(String(20), default="fit")
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    payload_hash: Mapped[str] = mapped_column(String(64), default="")
    file_url_host: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    lap_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_file_bytes: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="activity_detail_exports")
    activity: Mapped["AthleteActivity"] = relationship(back_populates="detail_exports")


class ActivityDetailSample(Base):
    __tablename__ = "activity_detail_samples"
    __table_args__ = (
        UniqueConstraint("activity_id", "sample_index", name="uq_activity_detail_sample_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("athlete_activities.id"), index=True)
    sample_index: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    elapsed_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cadence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    speed_mps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pace_sec_per_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    power_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    activity: Mapped["AthleteActivity"] = relationship(back_populates="detail_samples")


class ActivityDetailLap(Base):
    __tablename__ = "activity_detail_laps"
    __table_args__ = (
        UniqueConstraint("activity_id", "lap_index", name="uq_activity_detail_lap_index"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    activity_id: Mapped[int] = mapped_column(ForeignKey("athlete_activities.id"), index=True)
    lap_index: Mapped[int] = mapped_column(Integer)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_sec: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    min_hr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_cadence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_cadence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_speed_mps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_speed_mps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_power_w: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_gain_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    elevation_loss_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    activity: Mapped["AthleteActivity"] = relationship(back_populates="detail_laps")


class AthleteMetricSnapshot(Base):
    __tablename__ = "athlete_metric_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    metric_type: Mapped[str] = mapped_column(String(80), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    raw_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="metric_snapshots")


class ProviderSyncJob(Base):
    __tablename__ = "provider_sync_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), default="queued", index=True)
    phase: Mapped[str] = mapped_column(String(80), default="queued")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    metric_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_record_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="provider_sync_jobs")
    events: Mapped[list["ProviderSyncEvent"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", order_by="ProviderSyncEvent.id"
    )
    raw_records: Mapped[list["ProviderRawRecord"]] = relationship(back_populates="sync_job")


class ProviderSyncEvent(Base):
    __tablename__ = "provider_sync_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("provider_sync_jobs.id"), index=True)
    level: Mapped[str] = mapped_column(String(20), default="info")
    phase: Mapped[str] = mapped_column(String(80), default="running")
    message: Mapped[str] = mapped_column(Text)
    processed_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)

    job: Mapped["ProviderSyncJob"] = relationship(back_populates="events")


class ProviderRawRecord(Base):
    __tablename__ = "provider_raw_records"
    __table_args__ = (
        UniqueConstraint("provider", "record_type", "provider_record_id", name="uq_provider_raw_record"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    sync_job_id: Mapped[Optional[int]] = mapped_column(ForeignKey("provider_sync_jobs.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    record_type: Mapped[str] = mapped_column(String(80), index=True)
    provider_record_id: Mapped[str] = mapped_column(String(220), index=True)
    endpoint: Mapped[Optional[str]] = mapped_column(String(240), nullable=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="provider_raw_records")
    sync_job: Mapped[Optional["ProviderSyncJob"]] = relationship(back_populates="raw_records")


class RaceGoal(Base):
    __tablename__ = "race_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    sport: Mapped[SportType] = mapped_column(SqlEnum(SportType), default=SportType.MARATHON)
    distance: Mapped[str] = mapped_column(String(40), default="marathon")
    target_type: Mapped[str] = mapped_column(String(40), default="target_time")
    target_time_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    race_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    training_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    plan_weeks: Mapped[int] = mapped_column(Integer, default=16)
    status: Mapped[RaceGoalStatus] = mapped_column(SqlEnum(RaceGoalStatus), default=RaceGoalStatus.DRAFT)
    feasibility_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="race_goals")
    plans: Mapped[list["TrainingPlan"]] = relationship(back_populates="race_goal")


class TrainingAvailability(Base):
    __tablename__ = "training_availability"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), unique=True, index=True)
    weekly_training_days: Mapped[int] = mapped_column(Integer, default=5)
    preferred_long_run_weekday: Mapped[int] = mapped_column(Integer, default=6)
    unavailable_weekdays: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    max_weekday_duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    max_weekend_duration_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strength_training_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    athlete: Mapped["AthleteProfile"] = relationship(back_populates="availability")


class StructuredWorkout(Base):
    __tablename__ = "structured_workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id"), index=True)
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    week_index: Mapped[int] = mapped_column(Integer)
    day_index: Mapped[int] = mapped_column(Integer)
    discipline: Mapped[str] = mapped_column(String(40), default="run")
    workout_type: Mapped[str] = mapped_column(String(80))
    title: Mapped[str] = mapped_column(String(160))
    purpose: Mapped[str] = mapped_column(Text)
    duration_min: Mapped[int] = mapped_column(Integer)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_intensity_type: Mapped[str] = mapped_column(String(40), default="pace")
    target_pace_min_sec_per_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_pace_max_sec_per_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_hr_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_hr_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpe_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rpe_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[WorkoutStatus] = mapped_column(SqlEnum(WorkoutStatus), default=WorkoutStatus.DRAFT)
    adaptation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    plan: Mapped["TrainingPlan"] = relationship(back_populates="structured_workouts")
    steps: Mapped[list["WorkoutStep"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", order_by="WorkoutStep.step_index"
    )
    provider_sync_records: Mapped[list["ProviderSyncRecord"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan"
    )
    feedback: Mapped[Optional["WorkoutFeedback"]] = relationship(
        back_populates="workout", cascade="all, delete-orphan", uselist=False
    )


class WorkoutStep(Base):
    __tablename__ = "workout_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workout_id: Mapped[int] = mapped_column(ForeignKey("structured_workouts.id"), index=True)
    step_index: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[str] = mapped_column(String(40))
    duration_sec: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_type: Mapped[str] = mapped_column(String(40), default="effort")
    target_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    target_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    repeat_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workout: Mapped["StructuredWorkout"] = relationship(back_populates="steps")


class ProviderSyncRecord(Base):
    __tablename__ = "provider_sync_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id"), index=True)
    workout_id: Mapped[Optional[int]] = mapped_column(ForeignKey("structured_workouts.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(40), index=True)
    provider_workout_id: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    provider_calendar_item_id: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    sync_status: Mapped[SyncStatus] = mapped_column(SqlEnum(SyncStatus), default=SyncStatus.PENDING)
    attempted_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="provider_sync_records")
    workout: Mapped[Optional["StructuredWorkout"]] = relationship(back_populates="provider_sync_records")


class WorkoutFeedback(Base):
    __tablename__ = "workout_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_id: Mapped[int] = mapped_column(
        ForeignKey("structured_workouts.id"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20))  # "completed" | "partial" | "skipped"
    rpe: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    workout: Mapped["StructuredWorkout"] = relationship(back_populates="feedback")


class PlanAdjustment(Base):
    __tablename__ = "plan_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("training_plans.id"), index=True)
    status: Mapped[AdjustmentStatus] = mapped_column(SqlEnum(AdjustmentStatus), default=AdjustmentStatus.PROPOSED)
    reason: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(Text)
    effective_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    effective_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    affected_workouts_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    plan: Mapped["TrainingPlan"] = relationship(back_populates="adjustments")


class CoachMessage(Base):
    __tablename__ = "coach_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athlete_profiles.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # "user" | "coach"
    text: Mapped[str] = mapped_column(Text)
    suggested_actions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), index=True)
