from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

import json
import os

from app.kb.running_assessment import assess_running_ability
from app.tools.coros.automation import coros_automation_client
from app.tools.coros.credentials import decrypt_secret, encrypt_secret
from app.tools.coros.full_sync import ACTIVE_SYNC_STATUSES, run_coros_full_sync_job
from app.tools.coros.sync import sync_confirmed_plan_to_coros
from app.core.auth import get_current_user
from app.models import User  # noqa: F401 – used in TYPE_CHECKING context via string annotation
from app.db import get_db
from app.tools.devices.service import sync_plan_to_device
from app.ingestion.service import import_provider_history
from app.models import (
    AdjustmentStatus,
    ActivityDetailExport,
    ActivityDetailLap,
    ActivityDetailSample,
    AthleteActivity,
    AthleteMetricSnapshot,
    AthleteProfile,
    CoachMessage,
    DeviceAccount,
    DeviceType,
    PlanAdjustment,
    PlanStatus,
    ProviderSyncEvent,
    ProviderSyncJob,
    RaceGoal,
    SportType,
    StructuredWorkout,
    SyncTask,
    TrainingGoal,
    TrainingMethod,
    TrainingPlan,
    TrainingSession,
    WorkoutFeedback,
    WorkoutStatus,
    WorkoutStep,
)
from app.core.orchestrator import (
    create_race_goal as _orchestrator_create_race_goal,
    generate_plan_via_skill,
)
from app.core.adjustment import confirm_adjustment, evaluate_plan_adjustment
from app.core.matching import (
    compute_match_diff,
    match_workout_to_activity,
)
from app.schemas import (
    AdjustmentAffectedWorkout,
    ActivityDetailInterpretationOut,
    ActivityDetailLapOut,
    ActivityDetailOut,
    ActivityDetailRouteBoundsOut,
    ActivityDetailSampleOut,
    ActivityDetailSourceOut,
    AthleteActivityOut,
    CalendarDayOut,
    AthleteCreate,
    AthleteOut,
    CoachMessageOut,
    CoachMessageRequest,
    CoachMessageResponse,
    CorosConnectRequest,
    CorosSyncStartRequest,
    CorosStatusOut,
    DashboardAthleteRef,
    DashboardGoal,
    DashboardGreeting,
    DashboardMeta,
    DashboardOut,
    DashboardReadiness,
    DashboardRecentActivity,
    DashboardThisWeek,
    DashboardTodaySection,
    DashboardVolumeWeek,
    DashboardWeekDay,
    DeviceAccountOut,
    DeviceConnectRequest,
    HistoryImportOut,
    HistoryImportRequest,
    MarathonGoalCreate,
    MarathonPlanGenerateRequest,
    MarathonPlanOut,
    MatchDiff,
    ModeRecommendationOut,
    PlanAdjustmentApplyRequest,
    PlanAdjustmentDetailOut,
    PlanAdjustmentOut,
    PlanConfirmOut,
    PlanGenerateRequest,
    PlanStatusUpdate,
    PlanSyncOut,
    PlanVolumeCurveOut,
    PlanVolumeCurvePoint,
    ProviderSyncEventOut,
    ProviderSyncJobOut,
    ProviderSyncRecordOut,
    RaceGoalOut,
    RegenerateFromTodayOut,
    RegenerateFromTodayRequest,
    RegeneratePreviewOut,
    RunningAssessmentOut,
    SkillDetailOut,
    SkillManifestOut,
    StructuredWorkoutOut,
    SyncPlanRequest,
    SyncTaskOut,
    TodayOut,
    TrainingMethodOut,
    TrainingPlanOut,
    WeekOut,
    WorkoutFeedbackIn,
    WorkoutFeedbackOut,
    WorkoutMatchStatusOut,
)
from app.skills import list_skills, load_skill, load_skill_methodology
from app.training.engine import generate_plan_sessions
from app.training.knowledge_base import recommend_modes

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "PerformanceProtocol"}


@router.get("/sports")
def sports() -> list[dict[str, str]]:
    return [
        {"code": SportType.MARATHON.value, "name": "马拉松"},
        {"code": SportType.TRAIL_RUNNING.value, "name": "越野跑"},
        {"code": SportType.TRIATHLON.value, "name": "铁人三项"},
    ]


@router.post("/athletes", response_model=AthleteOut)
def create_athlete(request: AthleteCreate, db: Session = Depends(get_db), current_user: "User" = Depends(get_current_user)):
    athlete = AthleteProfile(**request.model_dump(), user_id=current_user.id)
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get("/training/methods", response_model=list[TrainingMethodOut])
def list_training_methods(
    sport: SportType | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(TrainingMethod)
    if sport:
        stmt = stmt.where(TrainingMethod.sport == sport)
    stmt = stmt.order_by(TrainingMethod.id.asc())
    return db.execute(stmt).scalars().all()


@router.get("/training/modes", response_model=list[ModeRecommendationOut])
def list_training_modes(sport: SportType, goal: TrainingGoal):
    return recommend_modes(sport=sport, goal=goal)


@router.post("/plans/generate", response_model=TrainingPlanOut)
def generate_plan(request: PlanGenerateRequest, db: Session = Depends(get_db)):
    athlete = _athlete_or_404(db, request.athlete_id)
    sport = request.sport or athlete.sport
    weekly_days = request.weekly_days or athlete.weekly_training_days

    mode = request.mode
    if mode is None:
        mode = recommend_modes(sport=sport, goal=request.goal)[0]["mode"]

    sessions_data = generate_plan_sessions(
        sport=sport,
        mode=mode,
        goal=request.goal,
        weeks=request.weeks,
        weekly_days=weekly_days,
    )

    plan = TrainingPlan(
        athlete_id=athlete.id,
        sport=sport,
        goal=request.goal,
        mode=mode,
        weeks=request.weeks,
        status=PlanStatus.DRAFT,
    )
    db.add(plan)
    db.flush()

    for item in sessions_data:
        db.add(TrainingSession(plan_id=plan.id, **item))

    db.commit()
    return _training_plan_or_404(db, plan.id)


@router.get("/plans", response_model=list[TrainingPlanOut])
def list_plans(
    athlete_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(TrainingPlan).options(selectinload(TrainingPlan.sessions)).order_by(TrainingPlan.id.desc())
    if athlete_id is not None:
        stmt = stmt.where(TrainingPlan.athlete_id == athlete_id)
    return db.execute(stmt).scalars().all()


@router.get("/plans/{plan_id}", response_model=TrainingPlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    return _training_plan_or_404(db, plan_id)


@router.patch("/plans/{plan_id}/status", response_model=TrainingPlanOut)
def update_plan_status(plan_id: int, request: PlanStatusUpdate, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = request.status
    plan.updated_at = datetime.now(UTC)
    db.commit()
    return _training_plan_or_404(db, plan_id)


@router.post("/devices/connect", response_model=DeviceAccountOut)
def connect_device(request: DeviceConnectRequest, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    _athlete_or_404(db, request.athlete_id)
    account = _device_account(db, request.athlete_id, request.device_type)
    if account:
        account.external_user_id = request.external_user_id
        account.auth_status = "connected"
        db.commit()
        db.refresh(account)
        return account

    account = DeviceAccount(**request.model_dump(), auth_status="connected")
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.post("/plans/{plan_id}/sync", response_model=SyncTaskOut)
def sync_plan(plan_id: int, request: SyncPlanRequest, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(selectinload(TrainingPlan.sessions))
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    account = _device_account(db, plan.athlete_id, request.device_type)
    if account is None:
        raise HTTPException(status_code=400, detail="Device not connected for this athlete")

    return sync_plan_to_device(db=db, plan=plan, device_type=request.device_type)


@router.get("/sync-tasks", response_model=list[SyncTaskOut])
def list_sync_tasks(
    plan_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    stmt = select(SyncTask).order_by(SyncTask.id.desc())
    if plan_id is not None:
        stmt = stmt.where(SyncTask.plan_id == plan_id)
    return db.execute(stmt).scalars().all()


@router.post("/coros/connect", response_model=DeviceAccountOut)
def connect_coros(request: CorosConnectRequest, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    _athlete_or_404(db, request.athlete_id)
    client = coros_automation_client()
    login = client.login(request.username, request.password)
    account = _device_account(db, request.athlete_id, DeviceType.COROS)
    if account is None:
        account = DeviceAccount(
            athlete_id=request.athlete_id,
            device_type=DeviceType.COROS,
            external_user_id=request.username,
        )
        db.add(account)

    account.username = request.username
    account.external_user_id = request.username
    account.encrypted_password = encrypt_secret(request.password)
    account.auth_status = "connected" if login.ok else "failed"
    account.last_login_at = datetime.now(UTC) if login.ok else None
    account.last_error = None if login.ok else login.message
    db.commit()
    db.refresh(account)
    return account


@router.get("/coros/status", response_model=CorosStatusOut)
def coros_status(athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    mode = os.environ.get("COROS_AUTOMATION_MODE", "real").strip().lower() or "real"
    account = _device_account(db, athlete_id, DeviceType.COROS)
    if account is None:
        return CorosStatusOut(
            athlete_id=athlete_id,
            connected=False,
            auth_status="disconnected",
            automation_mode=mode,
        )
    return CorosStatusOut(
        athlete_id=athlete_id,
        connected=account.auth_status == "connected",
        auth_status=account.auth_status,
        automation_mode=mode,
        username=account.username,
        last_login_at=account.last_login_at,
        last_import_at=account.last_import_at,
        last_sync_at=account.last_sync_at,
        last_error=account.last_error,
    )


@router.post("/coros/import", response_model=HistoryImportOut)
def import_coros_history(request: HistoryImportRequest, athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    return _import_history(db=db, athlete_id=athlete_id, device_type=DeviceType.COROS)


@router.post("/coros/sync/start", response_model=ProviderSyncJobOut)
def start_coros_full_sync(
    request: CorosSyncStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
):
    _athlete_or_404(db, request.athlete_id)
    account = _device_account(db, request.athlete_id, DeviceType.COROS)
    if account is None or account.auth_status != "connected" or not account.encrypted_password:
        raise HTTPException(status_code=400, detail="COROS account not connected")

    active_job = db.execute(
        select(ProviderSyncJob)
        .where(
            ProviderSyncJob.athlete_id == request.athlete_id,
            ProviderSyncJob.provider == "coros",
            ProviderSyncJob.status.in_(ACTIVE_SYNC_STATUSES),
        )
        .order_by(ProviderSyncJob.id.desc())
        .limit(1)
    ).scalars().first()
    if active_job is not None:
        return active_job

    job = ProviderSyncJob(
        athlete_id=request.athlete_id,
        provider="coros",
        status="queued",
        phase="queued",
        message=_coros_sync_window_message(request.days_back),
        sync_days_back=request.days_back,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(run_coros_full_sync_job, job.id)
    return job


@router.get("/coros/sync/jobs/{job_id}", response_model=ProviderSyncJobOut)
def get_coros_sync_job(job_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    job = db.get(ProviderSyncJob, job_id)
    if job is None or job.provider != "coros":
        raise HTTPException(status_code=404, detail="Sync job not found")
    return job


@router.get("/coros/sync/jobs/{job_id}/events", response_model=list[ProviderSyncEventOut])
def get_coros_sync_events(
    job_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
):
    job = db.get(ProviderSyncJob, job_id)
    if job is None or job.provider != "coros":
        raise HTTPException(status_code=404, detail="Sync job not found")
    return db.execute(
        select(ProviderSyncEvent)
        .where(ProviderSyncEvent.job_id == job_id)
        .order_by(ProviderSyncEvent.id.desc())
        .limit(limit)
    ).scalars().all()


@router.post("/athletes/{athlete_id}/history/import", response_model=HistoryImportOut)
def import_history(athlete_id: int, request: HistoryImportRequest, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    return _import_history(db=db, athlete_id=athlete_id, device_type=request.device_type)


def _coros_sync_window_message(days_back: int | None) -> str:
    if not days_back:
        return "Queued COROS full sync"
    if days_back >= 3650:
        return "Queued COROS all-history sync"
    return f"Queued COROS sync for the last {days_back} days"


@router.get("/athletes/{athlete_id}/history", response_model=list[AthleteActivityOut])
def get_history(athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    _athlete_or_404(db, athlete_id)
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .order_by(AthleteActivity.started_at.desc())
    ).scalars().all()
    return [_activity_with_match(db, a) for a in activities]


@router.get("/athletes/{athlete_id}/activities/{activity_id}", response_model=ActivityDetailOut)
def get_activity_detail(
    athlete_id: int,
    activity_id: int,
    sample_limit: int = Query(default=800, ge=100, le=5000),
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> ActivityDetailOut:
    _athlete_or_404(db, athlete_id)
    activity = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.id == activity_id)
        .where(AthleteActivity.athlete_id == athlete_id)
        .options(selectinload(AthleteActivity.matched_workout))
    ).scalar_one_or_none()
    if activity is None:
        raise HTTPException(status_code=404, detail="Activity not found")

    export = db.execute(
        select(ActivityDetailExport)
        .where(ActivityDetailExport.activity_id == activity.id)
        .where(ActivityDetailExport.source_format == "fit")
        .order_by(ActivityDetailExport.downloaded_at.desc(), ActivityDetailExport.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    sample_rows = db.execute(
        select(ActivityDetailSample)
        .where(ActivityDetailSample.activity_id == activity.id)
        .order_by(ActivityDetailSample.sample_index.asc())
    ).scalars().all()
    lap_rows = db.execute(
        select(ActivityDetailLap)
        .where(ActivityDetailLap.activity_id == activity.id)
        .order_by(ActivityDetailLap.lap_index.asc())
    ).scalars().all()
    selected_samples = _downsample_samples(sample_rows, sample_limit)
    return ActivityDetailOut(
        activity=_activity_with_match(db, activity),
        source=_activity_detail_source(export),
        samples=[ActivityDetailSampleOut.model_validate(sample) for sample in selected_samples],
        laps=[ActivityDetailLapOut.model_validate(lap) for lap in lap_rows],
        route_bounds=_route_bounds(sample_rows),
        interpretation=_activity_interpretation(activity, sample_rows, lap_rows, export),
        returned_sample_count=len(selected_samples),
    )


@router.get("/athletes/{athlete_id}/assessment", response_model=RunningAssessmentOut)
def get_assessment(athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    _athlete_or_404(db, athlete_id)
    return assess_running_ability(db=db, athlete_id=athlete_id)


@router.post("/athletes/{athlete_id}/assessment/run", response_model=RunningAssessmentOut)
def run_assessment(
    athlete_id: int,
    target_time_sec: int | None = None,
    plan_weeks: int | None = None,
    weekly_training_days: int | None = None,
    db: Session = Depends(get_db),
):
    _athlete_or_404(db, athlete_id)
    return assess_running_ability(
        db=db,
        athlete_id=athlete_id,
        target_time_sec=target_time_sec,
        plan_weeks=plan_weeks,
        requested_training_days=weekly_training_days,
    )


@router.post("/marathon/goals", response_model=RaceGoalOut)
def create_goal(request: MarathonGoalCreate, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    athlete = _athlete_or_404(db, request.athlete_id)
    return _orchestrator_create_race_goal(
        db=db, athlete=athlete, request=request, sport=SportType.MARATHON
    )


@router.post("/marathon/plans/generate", response_model=MarathonPlanOut)
def create_marathon_plan(request: MarathonPlanGenerateRequest, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    athlete = _athlete_or_404(db, request.athlete_id)
    race_goal = db.get(RaceGoal, request.race_goal_id) if request.race_goal_id else None
    if request.race_goal_id and race_goal is None:
        raise HTTPException(status_code=404, detail="Race goal not found")

    plan, error = generate_plan_via_skill(
        db=db,
        athlete=athlete,
        request=request,
        skill_slug=request.skill_slug,
        race_goal=race_goal,
    )
    if plan is None:
        raise HTTPException(status_code=422, detail=error)
    plan.active_skill_slug = request.skill_slug
    db.commit()
    return _marathon_plan_or_404(db, plan.id)


@router.get("/marathon/plans/{plan_id}", response_model=MarathonPlanOut)
def get_marathon_plan(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    return _marathon_plan_or_404(db, plan_id)


@router.post("/marathon/plans/{plan_id}/revoke", response_model=MarathonPlanOut)
def revoke_marathon_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: "User" = Depends(get_current_user),
):
    plan = _marathon_plan_or_404(db, plan_id)
    athlete = db.get(AthleteProfile, plan.athlete_id)
    if athlete is None or athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised")
    plan.status = PlanStatus.DRAFT
    plan.is_confirmed = False
    today = date.today()
    for w in plan.structured_workouts:
        if w.scheduled_date >= today:
            w.status = WorkoutStatus.DRAFT
    db.commit()
    db.refresh(plan)
    return _marathon_plan_or_404(db, plan_id)


@router.post("/plans/{plan_id}/confirm", response_model=PlanConfirmOut)
def confirm_plan(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(selectinload(TrainingPlan.structured_workouts))
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.is_confirmed = True
    plan.status = PlanStatus.ACTIVE
    count = 0
    for workout in plan.structured_workouts:
        workout.status = WorkoutStatus.CONFIRMED
        count += 1
    db.commit()
    return PlanConfirmOut(plan_id=plan.id, confirmed=True, confirmed_workout_count=count)


@router.post("/plans/{plan_id}/sync/coros", response_model=PlanSyncOut)
def sync_plan_to_coros(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    plan = _marathon_plan_or_404(db, plan_id)
    if not plan.is_confirmed:
        raise HTTPException(status_code=400, detail="Plan must be confirmed before sync")
    account = _device_account(db, plan.athlete_id, DeviceType.COROS)
    if account is None or not account.encrypted_password:
        raise HTTPException(status_code=400, detail="COROS account not connected")

    result = sync_confirmed_plan_to_coros(db=db, plan=plan, account=account)
    return PlanSyncOut(
        plan_id=plan.id,
        provider="coros",
        synced_count=result["synced_count"],
        failed_count=result["failed_count"],
        records=[ProviderSyncRecordOut.model_validate(record) for record in result["records"]],
    )


@router.post("/plans/{plan_id}/adjustments/evaluate", response_model=PlanAdjustmentOut)
def evaluate_adjustment(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return evaluate_plan_adjustment(db=db, plan=plan)


@router.post("/plan-adjustments/{adjustment_id}/confirm", response_model=PlanAdjustmentOut)
def confirm_plan_adjustment(adjustment_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)):
    adjustment = db.get(PlanAdjustment, adjustment_id)
    if adjustment is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    if adjustment.status != AdjustmentStatus.PROPOSED:
        return adjustment
    return confirm_adjustment(db=db, adjustment=adjustment)


def _import_history(db: Session, athlete_id: int, device_type: DeviceType) -> HistoryImportOut:
    athlete = _athlete_or_404(db, athlete_id)
    provider = device_type.value

    if device_type == DeviceType.COROS:
        account = _device_account(db, athlete_id, DeviceType.COROS)
        if account is None or account.auth_status != "connected" or not account.encrypted_password:
            raise HTTPException(status_code=400, detail="COROS account not connected")
        client = coros_automation_client()
        username = account.username or account.external_user_id
        password = decrypt_secret(account.encrypted_password)
        login = client.login(username, password)
        if not login.ok:
            account.auth_status = "failed"
            account.last_error = login.message
            db.commit()
            raise HTTPException(status_code=400, detail=login.message)
        account.last_login_at = datetime.now(UTC)
        history = client.fetch_history(username)
    else:
        client = coros_automation_client()
        history = client.fetch_history(f"{provider}_user_{athlete_id}")
        provider = device_type.value

    result = import_provider_history(
        db=db,
        athlete=athlete,
        provider=provider,
        activities=history["activities"],
        metrics=history.get("metrics", []),
    )
    account = _device_account(db, athlete_id, device_type)
    if account:
        account.last_import_at = datetime.now(UTC)
        account.last_error = None
        db.commit()

    return HistoryImportOut(
        athlete_id=athlete_id,
        provider=provider,
        imported_count=result["imported_count"],
        updated_count=result["updated_count"],
        metric_count=result["metric_count"],
        message=f"Imported {result['imported_count']} new and updated {result['updated_count']} {provider} activities.",
    )


def _athlete_or_404(db: Session, athlete_id: int) -> AthleteProfile:
    athlete = db.get(AthleteProfile, athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


def _device_account(db: Session, athlete_id: int, device_type: DeviceType) -> DeviceAccount | None:
    return db.execute(
        select(DeviceAccount)
        .where(
            DeviceAccount.athlete_id == athlete_id,
            DeviceAccount.device_type == device_type,
        )
        .order_by(DeviceAccount.id.desc())
        .limit(1)
    ).scalars().first()


def _training_plan_or_404(db: Session, plan_id: int) -> TrainingPlan:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(selectinload(TrainingPlan.sessions))
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


def _marathon_plan_or_404(db: Session, plan_id: int) -> TrainingPlan:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(
            selectinload(TrainingPlan.structured_workouts).selectinload(StructuredWorkout.steps),
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan


# ── Block A: Skills catalog ──────────────────────────────────────────────────


@router.get("/skills", response_model=list[SkillManifestOut])
def list_skills_endpoint() -> list[SkillManifestOut]:
    return [_manifest_to_out(m) for m in list_skills()]


@router.get("/skills/{slug}", response_model=SkillDetailOut)
def get_skill(slug: str) -> SkillDetailOut:
    try:
        skill = load_skill(slug)
    except (FileNotFoundError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {slug}") from exc
    try:
        methodology = load_skill_methodology(slug)
    except FileNotFoundError:
        methodology = ""
    base = _manifest_to_out(skill.manifest)
    return SkillDetailOut(**base.model_dump(), methodology_md=methodology)


def _manifest_to_out(manifest) -> SkillManifestOut:
    return SkillManifestOut(
        slug=manifest.slug,
        name=manifest.name,
        version=manifest.version,
        sport=manifest.sport.value,
        supported_goals=list(manifest.supported_goals),
        description=manifest.description,
        author=manifest.author,
        tags=list(manifest.tags),
        requires_llm=manifest.requires_llm,
    )


# ── Block A: Today / Week views ──────────────────────────────────────────────


def _active_or_draft_plan_for_athlete(db: Session, athlete_id: int) -> TrainingPlan | None:
    stmt = (
        select(TrainingPlan)
        .where(TrainingPlan.athlete_id == athlete_id)
        .where(TrainingPlan.status.in_([PlanStatus.ACTIVE, PlanStatus.DRAFT]))
        .options(
            selectinload(TrainingPlan.structured_workouts).selectinload(StructuredWorkout.steps)
        )
        .order_by(TrainingPlan.id.desc())
    )
    return db.execute(stmt).scalars().first()


@router.get("/athletes/{athlete_id}/today", response_model=TodayOut)
def get_today(athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)) -> TodayOut:
    _athlete_or_404(db, athlete_id)
    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active or draft plan for this athlete")

    today = date.today()
    yesterday = today - timedelta(days=1)
    workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == today),
        None,
    )
    yesterday_workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == yesterday),
        None,
    )

    matched_activity_id: int | None = None
    workout_out: StructuredWorkoutOut | None = None
    if workout is not None:
        workout_out = StructuredWorkoutOut.model_validate(workout)
        activity = match_workout_to_activity(db, workout)
        if activity is not None:
            matched_activity_id = activity.id

    yesterday_workout_out: StructuredWorkoutOut | None = None
    yesterday_activity_out: AthleteActivityOut | None = None
    if yesterday_workout is not None:
        yesterday_workout_out = StructuredWorkoutOut.model_validate(yesterday_workout)
        y_activity = match_workout_to_activity(db, yesterday_workout)
        if y_activity is not None:
            yesterday_activity_out = _activity_with_match(db, y_activity)

    recovery = _compute_recovery_recommendation(db, plan, workout)

    return TodayOut(
        plan_id=plan.id,
        plan_title=plan.title,
        skill_slug=plan.active_skill_slug,
        week_index=workout.week_index if workout else None,
        workout=workout_out,
        matched_activity_id=matched_activity_id,
        yesterday_workout=yesterday_workout_out,
        yesterday_activity=yesterday_activity_out,
        recovery_recommendation=recovery,
    )


@router.get("/athletes/{athlete_id}/workout/{workout_date}", response_model=TodayOut)
def get_workout_by_date(
    athlete_id: int,
    workout_date: str,
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> TodayOut:
    _athlete_or_404(db, athlete_id)
    try:
        target = date.fromisoformat(workout_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")

    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    if plan is None:
        return TodayOut(
            plan_id=None, plan_title=None, skill_slug=None,
            week_index=None, workout=None, matched_activity_id=None,
            yesterday_workout=None, yesterday_activity=None,
            recovery_recommendation=None,
        )

    yesterday = target - timedelta(days=1)
    workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == target), None
    )
    yesterday_workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == yesterday), None
    )

    matched_activity_id: int | None = None
    workout_out: StructuredWorkoutOut | None = None
    if workout is not None:
        workout_out = StructuredWorkoutOut.model_validate(workout)
        activity = match_workout_to_activity(db, workout)
        if activity is not None:
            matched_activity_id = activity.id

    yesterday_workout_out: StructuredWorkoutOut | None = None
    yesterday_activity_out: AthleteActivityOut | None = None
    if yesterday_workout is not None:
        yesterday_workout_out = StructuredWorkoutOut.model_validate(yesterday_workout)
        y_activity = match_workout_to_activity(db, yesterday_workout)
        if y_activity is not None:
            yesterday_activity_out = _activity_with_match(db, y_activity)

    return TodayOut(
        plan_id=plan.id,
        plan_title=plan.title,
        skill_slug=plan.active_skill_slug,
        week_index=workout.week_index if workout else None,
        workout=workout_out,
        matched_activity_id=matched_activity_id,
        yesterday_workout=yesterday_workout_out,
        yesterday_activity=yesterday_activity_out,
        recovery_recommendation=None,
    )


_DISCIPLINE_LABEL: dict[str, str] = {
    "run": "跑步", "cycle": "骑车", "swim": "游泳",
    "strength": "力量", "walk": "步行",
}


@router.get("/athletes/{athlete_id}/calendar", response_model=list[CalendarDayOut])
def get_calendar(
    athlete_id: int,
    from_date: str = Query(...),
    to_date: str = Query(...),
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> list[CalendarDayOut]:
    _athlete_or_404(db, athlete_id)
    try:
        from_d = date.fromisoformat(from_date)
        to_d = date.fromisoformat(to_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format, expected YYYY-MM-DD")

    today = date.today()

    from_dt = datetime.combine(from_d, datetime.min.time())
    to_dt = datetime.combine(to_d, datetime.max.time())
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.started_at >= from_dt)
        .where(AthleteActivity.started_at <= to_dt)
        .options(selectinload(AthleteActivity.matched_workout))
        .order_by(AthleteActivity.started_at)
    ).scalars().all()

    acts_by_date: dict[date, list[AthleteActivity]] = {}
    for act in activities:
        d = act.started_at.date()
        acts_by_date.setdefault(d, []).append(act)

    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    workouts_by_date: dict[date, StructuredWorkout] = {}
    if plan:
        for w in plan.structured_workouts:
            if from_d <= w.scheduled_date <= to_d:
                workouts_by_date[w.scheduled_date] = w

    all_dates = sorted(set(acts_by_date) | set(workouts_by_date))
    result: list[CalendarDayOut] = []

    for d in all_dates:
        acts = acts_by_date.get(d, [])
        workout = workouts_by_date.get(d)

        if acts:
            act = acts[0]
            mw = act.matched_workout
            status = _classify_match_status(mw, act)
            label = _DISCIPLINE_LABEL.get(act.discipline, act.discipline)
            dist_str = f" {act.distance_m / 1000:.1f}km" if act.distance_m else ""
            result.append(CalendarDayOut(
                date=d.isoformat(),
                status=status,
                title=f"{label}{dist_str}",
                sport=act.discipline,
                workout_type=mw.workout_type if mw else None,
                activity_id=act.id,
                workout_id=mw.id if mw else None,
                distance_km=round(act.distance_m / 1000, 2) if act.distance_m else None,
                duration_min=round(act.duration_sec / 60) if act.duration_sec else None,
            ))
        elif workout:
            status = "planned" if d > today else "miss"
            result.append(CalendarDayOut(
                date=d.isoformat(),
                status=status,
                title=workout.title,
                sport=workout.discipline,
                workout_type=workout.workout_type,
                activity_id=None,
                workout_id=workout.id,
                distance_km=round(workout.distance_m / 1000, 2) if workout.distance_m else None,
                duration_min=workout.duration_min,
            ))

    return result


@router.get("/plans/{plan_id}/week", response_model=WeekOut)
def get_plan_week(
    plan_id: int,
    week_index: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> WeekOut:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(
            selectinload(TrainingPlan.structured_workouts).selectinload(StructuredWorkout.steps)
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    workouts = [w for w in plan.structured_workouts if w.week_index == week_index]
    workouts.sort(key=lambda w: (w.scheduled_date, w.day_index))

    total_distance_m = float(sum((w.distance_m or 0.0) for w in workouts))
    total_duration_min = int(sum((w.duration_min or 0) for w in workouts))
    quality_count = sum(1 for w in workouts if _is_quality(w.workout_type))

    phase = _phase_for(week_index, plan.weeks)
    is_recovery = _is_recovery_week(workouts)

    return WeekOut(
        plan_id=plan.id,
        week_index=week_index,
        phase=phase,
        is_recovery=is_recovery,
        total_distance_m=total_distance_m,
        total_duration_min=total_duration_min,
        quality_count=quality_count,
        workouts=[StructuredWorkoutOut.model_validate(w) for w in workouts],
    )


_QUALITY_TYPES = {
    "threshold",
    "tempo",
    "interval",
    "intervals",
    "vo2max",
    "vo2",
    "marathon_pace",
    "race_pace",
    "fartlek",
    "hill",
    "hills",
    "progression",
    "long_run_with_quality",
}


def _is_quality(workout_type: str | None) -> bool:
    if not workout_type:
        return False
    return workout_type.lower() in _QUALITY_TYPES


def _is_recovery_week(workouts: list[StructuredWorkout]) -> bool:
    if not workouts:
        return False
    has_quality = any(_is_quality(w.workout_type) for w in workouts)
    if has_quality:
        return False
    total_distance_m = sum((w.distance_m or 0.0) for w in workouts)
    total_duration_min = sum((w.duration_min or 0) for w in workouts)
    # Heuristic: rest-heavy weeks are below ~30 km / ~3 hours of running.
    return total_distance_m < 30_000 and total_duration_min < 180


def _phase_for(week_index: int, total_weeks: int) -> str:
    if total_weeks <= 0:
        return "unknown"
    ratio = week_index / float(total_weeks)
    if ratio <= 0.65:
        return "base"
    if ratio <= 0.90:
        return "block"
    return "taper"


# ── Block A: Workout feedback ────────────────────────────────────────────────


_FEEDBACK_STATUS = {"completed", "partial", "skipped"}
_FEEDBACK_TO_WORKOUT_STATUS: dict[str, WorkoutStatus] = {
    "completed": WorkoutStatus.COMPLETED,
    "partial": WorkoutStatus.COMPLETED,
    "skipped": WorkoutStatus.MISSED,
}


@router.post("/workouts/{workout_id}/feedback", response_model=WorkoutFeedbackOut)
def post_workout_feedback(
    workout_id: int,
    payload: WorkoutFeedbackIn,
    db: Session = Depends(get_db),
) -> WorkoutFeedbackOut:
    workout = db.get(StructuredWorkout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")

    if payload.status not in _FEEDBACK_STATUS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status; must be one of {sorted(_FEEDBACK_STATUS)}",
        )

    existing = db.execute(
        select(WorkoutFeedback).where(WorkoutFeedback.workout_id == workout_id)
    ).scalar_one_or_none()

    if existing is None:
        feedback = WorkoutFeedback(
            workout_id=workout_id,
            status=payload.status,
            rpe=payload.rpe,
            note=payload.note,
        )
        db.add(feedback)
    else:
        existing.status = payload.status
        existing.rpe = payload.rpe
        existing.note = payload.note
        feedback = existing

    workout.status = _FEEDBACK_TO_WORKOUT_STATUS[payload.status]
    workout.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(feedback)
    return feedback


# ── Block A: Skill switch / regenerate-from-today ────────────────────────────


@router.post("/plans/{plan_id}/regenerate-from-today", response_model=RegenerateFromTodayOut)
def regenerate_plan_from_today(
    plan_id: int,
    payload: RegenerateFromTodayRequest,
    db: Session = Depends(get_db),
) -> RegenerateFromTodayOut:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(
            selectinload(TrainingPlan.structured_workouts).selectinload(StructuredWorkout.steps),
            selectinload(TrainingPlan.sessions),
            selectinload(TrainingPlan.race_goal),
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    athlete = db.get(AthleteProfile, plan.athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    today = date.today()
    frozen_workouts = [w for w in plan.structured_workouts if w.scheduled_date < today]
    future_workouts = [w for w in plan.structured_workouts if w.scheduled_date >= today]

    frozen_count = len(frozen_workouts)
    frozen_week_count = len({w.week_index for w in frozen_workouts}) if frozen_workouts else 0
    remaining_weeks = max(1, plan.weeks - frozen_week_count)

    # Build a derived race goal for the remaining horizon.
    base_goal = plan.race_goal
    derived_goal = RaceGoal(
        athlete_id=plan.athlete_id,
        sport=plan.sport,
        distance=base_goal.distance if base_goal else plan.sport.value,
        target_type=base_goal.target_type if base_goal else (
            "target_time" if plan.target_time_sec else "finish"
        ),
        target_time_sec=plan.target_time_sec,
        race_date=plan.race_date,
        training_start_date=today,
        plan_weeks=remaining_weeks,
        status=base_goal.status if base_goal else None,
        feasibility_summary=base_goal.feasibility_summary if base_goal else None,
    )

    availability = _availability_for(db, plan.athlete_id)

    # Validate skill applicability via a probe context (cheap dry-run).
    try:
        skill = load_skill(payload.skill_slug)
    except (FileNotFoundError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {payload.skill_slug}") from exc

    # Single-transaction regenerate.
    try:
        # 1) Drop future workouts/steps/training-sessions but keep frozen ones intact.
        future_ids = [w.id for w in future_workouts]
        if future_ids:
            db.query(WorkoutStep).filter(WorkoutStep.workout_id.in_(future_ids)).delete(
                synchronize_session=False
            )
            db.query(StructuredWorkout).filter(StructuredWorkout.id.in_(future_ids)).delete(
                synchronize_session=False
            )
        # Drop only future TrainingSessions for this plan (week_index after frozen weeks).
        if frozen_week_count > 0:
            db.query(TrainingSession).filter(
                TrainingSession.plan_id == plan.id,
                TrainingSession.week_index > frozen_week_count,
            ).delete(synchronize_session=False)
        else:
            db.query(TrainingSession).filter(
                TrainingSession.plan_id == plan.id
            ).delete(synchronize_session=False)
        db.flush()

        # 2) Persist derived race goal then run the skill.
        db.add(derived_goal)
        db.flush()

        from app.core.orchestrator import _build_context, _llm_enabled

        ctx = _build_context(
            db=db,
            athlete=athlete,
            availability=availability,
            race_goal=derived_goal,
            start_date=today,
            profile_block="",
            llm_enabled=_llm_enabled(),
        )
        ok, why = skill.applicable(ctx)
        if not ok:
            db.rollback()
            raise HTTPException(
                status_code=422,
                detail=f"Skill {payload.skill_slug} not applicable: {why}",
            )

        draft = skill.generate_plan(ctx)

        # 3) Re-persist new workouts on the same plan, offsetting week_index.
        regenerated_count = 0
        for week in draft.weeks:
            week_sorted = sorted(week, key=lambda w: (w.week_index, w.weekday))
            for day_index, workout in enumerate(week_sorted, start=1):
                effective_week = workout.week_index + frozen_week_count
                week_start = today + timedelta(weeks=workout.week_index - 1)
                scheduled_date = week_start + timedelta(
                    days=(workout.weekday - week_start.weekday()) % 7
                )
                sw = StructuredWorkout(
                    plan_id=plan.id,
                    day_index=day_index,
                    week_index=effective_week,
                    scheduled_date=scheduled_date,
                    discipline=workout.discipline,
                    workout_type=workout.workout_type,
                    title=workout.title,
                    purpose=workout.purpose,
                    duration_min=workout.duration_min,
                    distance_m=workout.distance_m,
                    target_intensity_type=workout.target_intensity_type,
                    target_pace_min_sec_per_km=workout.target_pace_min_sec_per_km,
                    target_pace_max_sec_per_km=workout.target_pace_max_sec_per_km,
                    target_hr_min=workout.target_hr_min,
                    target_hr_max=workout.target_hr_max,
                    rpe_min=workout.rpe_min,
                    rpe_max=workout.rpe_max,
                    adaptation_notes=workout.adaptation_notes,
                )
                db.add(sw)
                db.flush()
                for step_index, step in enumerate(workout.steps, start=1):
                    db.add(
                        WorkoutStep(
                            workout_id=sw.id,
                            step_index=step_index,
                            step_type=step.step_type,
                            duration_sec=step.duration_sec,
                            target_type=step.target_type,
                            target_min=step.target_min,
                            target_max=step.target_max,
                            notes=step.notes,
                        )
                    )
                db.add(
                    TrainingSession(
                        plan_id=plan.id,
                        week_index=effective_week,
                        day_index=day_index,
                        discipline=sw.discipline,
                        session_type=sw.workout_type,
                        duration_min=sw.duration_min,
                        intensity=_intensity_for_label(sw.workout_type),
                        notes=sw.purpose,
                    )
                )
                regenerated_count += 1

        # 4) Update plan metadata.
        plan.active_skill_slug = payload.skill_slug
        if draft.title:
            plan.title = draft.title
        plan.updated_at = datetime.now(UTC)
        plan.weeks = max(plan.weeks, frozen_week_count + len(draft.weeks))
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Regeneration failed: {exc}") from exc

    return RegenerateFromTodayOut(
        plan_id=plan.id,
        frozen_count=frozen_count,
        regenerated_count=regenerated_count,
        new_skill_slug=payload.skill_slug,
    )


def _intensity_for_label(workout_type: str) -> str:
    if workout_type == "threshold":
        return "high"
    if workout_type == "marathon_pace":
        return "moderate"
    return "low"


def _availability_for(db: Session, athlete_id: int):
    """Fetch and adapt the athlete's TrainingAvailability into a request-style object.

    Returns an object exposing the same attributes the orchestrator's
    ``save_availability`` and ``_build_context`` consumers expect.
    """
    from app.models import TrainingAvailability

    row = db.execute(
        select(TrainingAvailability).where(TrainingAvailability.athlete_id == athlete_id)
    ).scalar_one_or_none()

    class _AvailabilityShim:
        weekly_training_days = row.weekly_training_days if row else 5
        preferred_long_run_weekday = row.preferred_long_run_weekday if row else 6
        # Orchestrator's _parse_unavailable expects the raw comma-string.
        unavailable_weekdays = (row.unavailable_weekdays or "") if row else ""
        max_weekday_duration_min = row.max_weekday_duration_min if row else None
        max_weekend_duration_min = row.max_weekend_duration_min if row else None
        strength_training_enabled = row.strength_training_enabled if row else True
        notes = row.notes if row else None

    return _AvailabilityShim()


# ── Block A: Match status ────────────────────────────────────────────────────


@router.get("/workouts/{workout_id}/match-status", response_model=WorkoutMatchStatusOut)
def get_workout_match_status(
    workout_id: int, db: Session = Depends(get_db)
) -> WorkoutMatchStatusOut:
    workout = db.get(StructuredWorkout, workout_id)
    if workout is None:
        raise HTTPException(status_code=404, detail="Workout not found")
    activity = match_workout_to_activity(db, workout)
    diff: MatchDiff | None = None
    matched_out = None
    if activity is not None:
        matched_out = _activity_with_match(db, activity)
        diff = MatchDiff(**compute_match_diff(workout, activity))
    return WorkoutMatchStatusOut(workout_id=workout.id, matched_activity=matched_out, diff=diff)


# ── Block A1: Activity enrichment helpers ────────────────────────────────────


def _format_delta_summary(workout: StructuredWorkout, activity: AthleteActivity) -> str | None:
    """Pick the most-significant single delta and format as a Chinese-friendly string."""
    diff = compute_match_diff(workout, activity)

    pace_diff = diff.get("avg_pace_diff_sec_per_km")
    if pace_diff is not None and abs(pace_diff) >= 3:
        sign = "+" if pace_diff > 0 else ""
        return f"配速 {sign}{int(pace_diff)}s/km"

    if (
        workout.target_hr_min is not None
        and workout.target_hr_max is not None
        and activity.avg_hr is not None
    ):
        target_mid = (workout.target_hr_min + workout.target_hr_max) / 2.0
        hr_diff = activity.avg_hr - target_mid
        if abs(hr_diff) >= 2:
            sign = "+" if hr_diff > 0 else ""
            return f"HR {sign}{int(round(hr_diff))} bpm"

    distance_pct = diff.get("distance_pct")
    if distance_pct is not None and abs(distance_pct) >= 5:
        sign = "+" if distance_pct > 0 else ""
        return f"距离 {sign}{distance_pct:.1f}%"

    duration_pct = diff.get("duration_pct")
    if duration_pct is not None and abs(duration_pct) >= 5:
        sign = "+" if duration_pct > 0 else ""
        return f"时长 {sign}{duration_pct:.1f}%"

    if pace_diff is not None or distance_pct is not None or duration_pct is not None:
        return "执行符合计划"
    return None


def _classify_match_status(workout: StructuredWorkout | None, activity: AthleteActivity) -> str:
    if workout is None:
        return "unmatched"
    diff = compute_match_diff(workout, activity)
    distance_pct = diff.get("distance_pct")
    if distance_pct is None:
        return "completed"
    if distance_pct < -25:
        return "miss"
    if distance_pct < -10:
        return "partial"
    return "completed"


def _activity_with_match(db: Session, activity: AthleteActivity) -> AthleteActivityOut:
    """Build an AthleteActivityOut that also includes match info + delta_summary."""
    base = AthleteActivityOut.model_validate(activity).model_dump()
    matched_workout: StructuredWorkout | None = None
    if activity.matched_workout_id is not None:
        matched_workout = db.get(StructuredWorkout, activity.matched_workout_id)

    if matched_workout is not None:
        base["matched_workout_id"] = matched_workout.id
        base["matched_workout_title"] = matched_workout.title
        base["match_status"] = _classify_match_status(matched_workout, activity)
        base["delta_summary"] = _format_delta_summary(matched_workout, activity)
    else:
        base["matched_workout_id"] = None
        base["matched_workout_title"] = None
        base["match_status"] = "unmatched"
        base["delta_summary"] = None

    return AthleteActivityOut(**base)


def _downsample_samples(samples: list[ActivityDetailSample], limit: int) -> list[ActivityDetailSample]:
    if len(samples) <= limit:
        return samples
    last = len(samples) - 1
    indices = [round(i * last / (limit - 1)) for i in range(limit)]
    return [samples[index] for index in indices]


def _activity_detail_source(export: ActivityDetailExport | None) -> ActivityDetailSourceOut | None:
    if export is None:
        return None
    warnings: list[str] = []
    if export.warnings_json:
        try:
            parsed = json.loads(export.warnings_json)
            if isinstance(parsed, list):
                warnings = [str(item) for item in parsed]
        except json.JSONDecodeError:
            warnings = [export.warnings_json]
    return ActivityDetailSourceOut(
        source_format=export.source_format,
        file_size_bytes=export.file_size_bytes,
        payload_hash=export.payload_hash,
        file_url_host=export.file_url_host,
        downloaded_at=export.downloaded_at,
        parsed_at=export.parsed_at,
        stored_sample_count=export.sample_count,
        stored_lap_count=export.lap_count,
        warnings=warnings,
    )


def _route_bounds(samples: list[ActivityDetailSample]) -> ActivityDetailRouteBoundsOut:
    gps = [sample for sample in samples if sample.latitude is not None and sample.longitude is not None]
    if not gps:
        return ActivityDetailRouteBoundsOut()
    latitudes = [float(sample.latitude) for sample in gps if sample.latitude is not None]
    longitudes = [float(sample.longitude) for sample in gps if sample.longitude is not None]
    return ActivityDetailRouteBoundsOut(
        min_latitude=min(latitudes),
        max_latitude=max(latitudes),
        min_longitude=min(longitudes),
        max_longitude=max(longitudes),
    )


def _activity_interpretation(
    activity: AthleteActivity,
    samples: list[ActivityDetailSample],
    laps: list[ActivityDetailLap],
    export: ActivityDetailExport | None,
) -> ActivityDetailInterpretationOut:
    gps_count = sum(1 for sample in samples if sample.latitude is not None and sample.longitude is not None)
    hr_samples = [float(sample.heart_rate) for sample in samples if sample.heart_rate is not None]
    pace_samples = [
        float(sample.pace_sec_per_km)
        for sample in samples
        if sample.pace_sec_per_km is not None and 120 <= float(sample.pace_sec_per_km) <= 900
    ]
    effort = "No heart-rate stream was parsed from this activity."
    if hr_samples:
        avg_hr = sum(hr_samples) / len(hr_samples)
        max_hr = max(hr_samples)
        effort = f"Average heart rate {avg_hr:.0f} bpm with peak {max_hr:.0f} bpm across {len(hr_samples)} samples."
    consistency = "Pace consistency cannot be calculated without valid pace samples."
    if pace_samples:
        mean_pace = sum(pace_samples) / len(pace_samples)
        variance = sum((value - mean_pace) ** 2 for value in pace_samples) / len(pace_samples)
        spread = variance ** 0.5
        consistency = f"Second-by-second pace variability is {spread:.0f} sec/km around a {mean_pace:.0f} sec/km mean."
    drift = "Heart-rate drift needs both heart-rate and pace streams."
    if len(hr_samples) >= 20 and len(pace_samples) >= 20:
        midpoint = len(samples) // 2
        first_hr = _avg([sample.heart_rate for sample in samples[:midpoint]])
        second_hr = _avg([sample.heart_rate for sample in samples[midpoint:]])
        if first_hr and second_hr:
            drift = f"Heart rate changed from {first_hr:.0f} bpm in the first half to {second_hr:.0f} bpm in the second half."
    quality = (
        f"Parsed {len(samples)} samples, {gps_count} GPS points, and {len(laps)} laps"
        f" from {export.source_format.upper() if export else 'no export'} source."
    )
    if export and export.warnings_json not in (None, "[]"):
        quality += " Parser warnings are available in the source section."
    if not activity.distance_m:
        quality += " Activity summary distance is missing."
    return ActivityDetailInterpretationOut(
        effort_distribution=effort,
        pace_consistency=consistency,
        heart_rate_drift=drift,
        data_quality=quality,
    )


def _avg(values: list[float | None]) -> float | None:
    numeric = [float(value) for value in values if value is not None]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _compute_recovery_recommendation(
    db: Session,
    plan: TrainingPlan,
    today_workout: StructuredWorkout | None,
) -> dict | None:
    """If 4+ workouts in the last 7 days are MISSED, surface a degraded recommendation."""
    today = date.today()
    week_ago = today - timedelta(days=7)
    missed_count = sum(
        1
        for w in plan.structured_workouts
        if week_ago <= w.scheduled_date < today and w.status == WorkoutStatus.MISSED
    )
    if missed_count < 4:
        return None
    return {
        "degraded_workout_title": "20 min 慢跑 · 步频检测",
        "ethos_quote": "缺训不补",
        "original_workout_title": today_workout.title if today_workout else None,
    }


# ── Block A1: Dashboard ──────────────────────────────────────────────────────


def _greeting_for(now: datetime) -> DashboardGreeting:
    hour = now.hour
    if hour < 12:
        tod = "morning"
    elif hour < 18:
        tod = "afternoon"
    else:
        tod = "evening"
    return DashboardGreeting(
        time_of_day=tod,
        date=now.date().isoformat(),
        weekday_short=now.strftime("%a"),
    )


def _label_for_time(target_time_sec: int | None) -> str | None:
    if not target_time_sec:
        return None
    h = target_time_sec // 3600
    m = (target_time_sec % 3600) // 60
    return f"sub-{h}:{m:02d}"


def _week_strip_status(
    workout: StructuredWorkout | None,
    matched: AthleteActivity | None,
    day: date,
    today: date,
) -> str:
    if workout is None:
        return "today" if day == today else "rest"
    if workout.status == WorkoutStatus.COMPLETED:
        if matched is not None:
            cls = _classify_match_status(workout, matched)
            if cls == "completed":
                return "done"
            if cls == "partial":
                return "partial"
            if cls == "miss":
                return "miss"
        return "done"
    if workout.status == WorkoutStatus.MISSED:
        return "miss"
    if day == today:
        return "today"
    if day < today:
        # past but not completed/missed: treat as miss unless an activity matched
        if matched is not None:
            return _classify_match_status(workout, matched)
        return "miss"
    return "plan"


@router.get("/athletes/{athlete_id}/dashboard", response_model=DashboardOut)
def get_athlete_dashboard(athlete_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)) -> DashboardOut:
    athlete = _athlete_or_404(db, athlete_id)
    plan = _active_or_draft_plan_for_athlete(db, athlete_id)

    now = datetime.now(UTC)
    today = date.today()

    greeting = _greeting_for(now)

    # ── Athlete + skill ref ───────────────────────────────────────────────
    current_skill_out: SkillManifestOut | None = None
    skill_slug = plan.active_skill_slug if plan else None
    if skill_slug:
        try:
            skill = load_skill(skill_slug)
            current_skill_out = _manifest_to_out(skill.manifest)
        except (FileNotFoundError, ValueError, AttributeError):
            current_skill_out = None

    athlete_ref = DashboardAthleteRef(
        id=athlete.id, name=athlete.name, current_skill=current_skill_out
    )

    # ── Today section ─────────────────────────────────────────────────────
    today_workout: StructuredWorkout | None = None
    matched_today: AthleteActivity | None = None
    if plan is not None:
        today_workout = next(
            (w for w in plan.structured_workouts if w.scheduled_date == today), None
        )
        if today_workout is not None:
            matched_today = match_workout_to_activity(db, today_workout)
            greeting.week_index = today_workout.week_index
            greeting.week_phase = _phase_for(today_workout.week_index, plan.weeks)

    today_section = DashboardTodaySection(
        plan_id=plan.id if plan else None,
        week_index=today_workout.week_index if today_workout else None,
        workout=StructuredWorkoutOut.model_validate(today_workout) if today_workout else None,
        matched_activity=_activity_with_match(db, matched_today) if matched_today else None,
        match_status=(
            _classify_match_status(today_workout, matched_today)
            if matched_today is not None and today_workout is not None
            else None
        ),
    )

    # ── This week section ─────────────────────────────────────────────────
    this_week = DashboardThisWeek()
    if plan is not None:
        # Anchor week on today_workout's week if available; else find week containing today
        week_index: int | None = today_workout.week_index if today_workout else None
        if week_index is None:
            future = [
                w for w in plan.structured_workouts if w.scheduled_date >= today
            ]
            if future:
                week_index = min(future, key=lambda w: w.scheduled_date).week_index
            elif plan.structured_workouts:
                week_index = plan.structured_workouts[-1].week_index

        if week_index is not None:
            week_workouts = sorted(
                [w for w in plan.structured_workouts if w.week_index == week_index],
                key=lambda w: w.scheduled_date,
            )
            phase = _phase_for(week_index, plan.weeks)
            is_recovery = _is_recovery_week(week_workouts)
            planned_km = sum((w.distance_m or 0) for w in week_workouts) / 1000.0
            planned_quality = sum(1 for w in week_workouts if _is_quality(w.workout_type))

            completed_km = 0.0
            completed_quality = 0
            days: list[DashboardWeekDay] = []

            for w in week_workouts:
                matched = match_workout_to_activity(db, w)
                if matched is not None and w.status == WorkoutStatus.COMPLETED:
                    completed_km += (matched.distance_m or 0) / 1000.0
                    if _is_quality(w.workout_type):
                        completed_quality += 1

                status = _week_strip_status(w, matched, w.scheduled_date, today)
                day_distance_km = ((matched.distance_m if matched else (w.distance_m or 0)) or 0) / 1000.0
                day_duration_min = (
                    (matched.duration_sec // 60) if matched else (w.duration_min or 0)
                )
                days.append(
                    DashboardWeekDay(
                        date=w.scheduled_date,
                        weekday=w.scheduled_date.weekday(),
                        title=w.title,
                        distance_km=round(day_distance_km, 2),
                        duration_min=int(day_duration_min),
                        status=status,
                    )
                )

            this_week = DashboardThisWeek(
                plan_id=plan.id,
                week_index=week_index,
                total_weeks=plan.weeks,
                phase=phase,
                is_recovery=is_recovery,
                days=days,
                completed_km=round(completed_km, 2),
                planned_km=round(planned_km, 2),
                completed_quality=completed_quality,
                planned_quality=planned_quality,
            )

    # ── Goal ──────────────────────────────────────────────────────────────
    goal = DashboardGoal()
    if plan is not None:
        goal.label = _label_for_time(plan.target_time_sec)
        goal.race_date = plan.race_date
        goal.target_time_sec = plan.target_time_sec
        if plan.race_date is not None:
            goal.days_until = (plan.race_date - today).days

    pred_rows = db.execute(
        select(AthleteMetricSnapshot)
        .where(AthleteMetricSnapshot.athlete_id == athlete_id)
        .where(AthleteMetricSnapshot.metric_type == "race_predictor_marathon")
        .order_by(AthleteMetricSnapshot.measured_at.desc())
        .limit(12)
    ).scalars().all()
    pred_rows_asc = list(reversed(pred_rows))
    goal.prediction_history = [
        {
            "measured_at": r.measured_at.isoformat(),
            "predicted_time_sec": int(r.value),
        }
        for r in pred_rows_asc
    ]
    if len(pred_rows_asc) >= 2:
        latest = pred_rows_asc[-1]
        cutoff = latest.measured_at - timedelta(days=28)
        prior = next(
            (r for r in pred_rows_asc if r.measured_at <= cutoff),
            pred_rows_asc[0] if pred_rows_asc[0] is not latest else None,
        )
        if prior is not None and prior is not latest:
            goal.monthly_delta_sec = int(latest.value) - int(prior.value)

    # ── Volume history (last 8 weeks) ─────────────────────────────────────
    volume_history: list[DashboardVolumeWeek] = []
    current_week_index = today_workout.week_index if today_workout else None
    if plan is not None and current_week_index is not None:
        for offset in range(-7, 1):
            wi = current_week_index + offset
            if wi < 1 or wi > plan.weeks:
                continue
            wk_workouts = [w for w in plan.structured_workouts if w.week_index == wi]
            planned_km_w = sum((w.distance_m or 0) for w in wk_workouts) / 1000.0
            if wk_workouts:
                wk_start = min(w.scheduled_date for w in wk_workouts)
                wk_end = max(w.scheduled_date for w in wk_workouts)
                acts = db.execute(
                    select(AthleteActivity)
                    .where(AthleteActivity.athlete_id == athlete_id)
                    .where(AthleteActivity.discipline == "run")
                    .where(AthleteActivity.started_at >= datetime.combine(wk_start, datetime.min.time()))
                    .where(AthleteActivity.started_at <= datetime.combine(wk_end + timedelta(days=1), datetime.min.time()))
                ).scalars().all()
                executed_km_w = sum((a.distance_m or 0) for a in acts) / 1000.0
            else:
                executed_km_w = 0.0
            completion = (executed_km_w / planned_km_w * 100.0) if planned_km_w > 0 else 0.0
            label = "W00" if offset == 0 else (f"W{offset:+d}".replace("+", "+"))
            # Spec says "W-7", "W-6"... "W05" (current). Use a simple prefix.
            if offset == 0:
                label = f"W{wi:02d}"
            else:
                label = f"W{offset}"
            volume_history.append(
                DashboardVolumeWeek(
                    week_index=wi,
                    week_label=label,
                    executed_km=round(executed_km_w, 2),
                    planned_km=round(planned_km_w, 2),
                    completion_pct=round(completion, 1),
                    is_current=(offset == 0),
                )
            )

    # ── Recent activities (last 7) ────────────────────────────────────────
    recent_acts = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .order_by(AthleteActivity.started_at.desc())
        .limit(7)
    ).scalars().all()
    recent_activities: list[DashboardRecentActivity] = []
    for a in recent_acts:
        matched_workout: StructuredWorkout | None = None
        if a.matched_workout_id is not None:
            matched_workout = db.get(StructuredWorkout, a.matched_workout_id)
        title = matched_workout.title if matched_workout is not None else "自由跑"
        match_status = (
            _classify_match_status(matched_workout, a) if matched_workout is not None else "unmatched"
        )
        delta = _format_delta_summary(matched_workout, a) if matched_workout is not None else None
        recent_activities.append(
            DashboardRecentActivity(
                id=a.id,
                started_at=a.started_at,
                title=title,
                distance_km=round((a.distance_m or 0) / 1000.0, 2),
                duration_min=int((a.duration_sec or 0) // 60),
                avg_pace_sec_per_km=a.avg_pace_sec_per_km,
                avg_hr=int(a.avg_hr) if a.avg_hr is not None else None,
                match_status=match_status,
                delta_summary=delta,
            )
        )

    # ── Pending adjustment ────────────────────────────────────────────────
    pending = db.execute(
        select(PlanAdjustment)
        .where(PlanAdjustment.athlete_id == athlete_id)
        .where(PlanAdjustment.status == AdjustmentStatus.PROPOSED)
        .order_by(PlanAdjustment.created_at.desc())
    ).scalars().first()
    pending_dict: dict | None = None
    if pending is not None:
        headline = (pending.reason or "")[:50]
        pending_dict = {"id": pending.id, "reason_headline": headline}

    # ── Readiness ─────────────────────────────────────────────────────────
    readiness = _build_readiness(db, athlete_id)

    # ── Meta ──────────────────────────────────────────────────────────────
    coros_account = _device_account(db, athlete_id, DeviceType.COROS)
    last_sync_at = None
    last_sync_status = "never"
    if coros_account is not None:
        last_sync_at = coros_account.last_import_at or coros_account.last_sync_at
        if last_sync_at is not None:
            last_sync_status = "ok" if not coros_account.last_error else "error"
        elif coros_account.last_error:
            last_sync_status = "error"

    meta = DashboardMeta(
        skill_slug=skill_slug,
        skill_name=current_skill_out.name if current_skill_out else None,
        skill_version=current_skill_out.version if current_skill_out else None,
        last_sync_at=last_sync_at,
        last_sync_status=last_sync_status,
    )

    return DashboardOut(
        athlete=athlete_ref,
        greeting=greeting,
        pending_adjustment=pending_dict,
        today=today_section,
        this_week=this_week,
        goal=goal,
        volume_history=volume_history,
        recent_activities=recent_activities,
        readiness=readiness,
        meta=meta,
    )


def _build_readiness(db: Session, athlete_id: int) -> DashboardReadiness:
    now = datetime.now(UTC)

    def _latest_metric(metric_type: str):
        return db.execute(
            select(AthleteMetricSnapshot)
            .where(AthleteMetricSnapshot.athlete_id == athlete_id)
            .where(AthleteMetricSnapshot.metric_type == metric_type)
            .order_by(AthleteMetricSnapshot.measured_at.desc())
        ).scalars().first()

    rhr_row = _latest_metric("resting_hr")
    rhr = int(rhr_row.value) if rhr_row else None
    rhr_trend: str | None = None
    if rhr_row is not None:
        cutoff = now.replace(tzinfo=None) - timedelta(days=14)
        rows = db.execute(
            select(AthleteMetricSnapshot)
            .where(AthleteMetricSnapshot.athlete_id == athlete_id)
            .where(AthleteMetricSnapshot.metric_type == "resting_hr")
            .where(AthleteMetricSnapshot.measured_at >= cutoff)
        ).scalars().all()
        if rows:
            avg = sum(r.value for r in rows) / len(rows)
            if rhr is not None:
                if rhr < avg - 1:
                    rhr_trend = "down"
                elif rhr > avg + 1:
                    rhr_trend = "up"
                else:
                    rhr_trend = "flat"

    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)
    cur_acts = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.started_at >= week_ago.replace(tzinfo=None))
    ).scalars().all()
    prev_acts = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.started_at >= two_weeks_ago.replace(tzinfo=None))
        .where(AthleteActivity.started_at < week_ago.replace(tzinfo=None))
    ).scalars().all()
    cur_load = sum((a.training_load or 0) for a in cur_acts)
    prev_load = sum((a.training_load or 0) for a in prev_acts)
    weekly_load = int(cur_load) if cur_acts else None
    load_trend: str | None = None
    if cur_acts:
        if cur_load < prev_load - 1:
            load_trend = "down"
        elif cur_load > prev_load + 1:
            load_trend = "up"
        else:
            load_trend = "flat"

    lthr_row = _latest_metric("lthr")
    ltsp_row = _latest_metric("ltsp")

    return DashboardReadiness(
        resting_hr=rhr,
        resting_hr_trend=rhr_trend,
        weekly_training_load=weekly_load,
        weekly_training_load_trend=load_trend,
        lthr=int(lthr_row.value) if lthr_row else None,
        ltsp_sec_per_km=float(ltsp_row.value) if ltsp_row else None,
    )


# ── Block A1: Plan volume curve ──────────────────────────────────────────────


@router.get("/plans/{plan_id}/volume-curve", response_model=PlanVolumeCurveOut)
def get_plan_volume_curve(plan_id: int, db: Session = Depends(get_db), _user: "User" = Depends(get_current_user)) -> PlanVolumeCurveOut:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(selectinload(TrainingPlan.structured_workouts))
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    today = date.today()
    weeks_data: dict[int, list[StructuredWorkout]] = {}
    for w in plan.structured_workouts:
        weeks_data.setdefault(w.week_index, []).append(w)

    current_week_index = None
    for wi, ws in weeks_data.items():
        wk_start = min(w.scheduled_date for w in ws)
        wk_end = max(w.scheduled_date for w in ws)
        if wk_start <= today <= wk_end:
            current_week_index = wi
            break

    points: list[PlanVolumeCurvePoint] = []
    peak_planned = 0.0
    peak_executed = 0.0
    for wi in sorted(weeks_data.keys()):
        ws = weeks_data[wi]
        planned_km = sum((w.distance_m or 0) for w in ws) / 1000.0
        longest = max(((w.distance_m or 0) for w in ws), default=0.0) / 1000.0
        wk_start = min(w.scheduled_date for w in ws)
        wk_end = max(w.scheduled_date for w in ws)
        acts = db.execute(
            select(AthleteActivity)
            .where(AthleteActivity.athlete_id == plan.athlete_id)
            .where(AthleteActivity.discipline == "run")
            .where(AthleteActivity.started_at >= datetime.combine(wk_start, datetime.min.time()))
            .where(
                AthleteActivity.started_at
                <= datetime.combine(wk_end + timedelta(days=1), datetime.min.time())
            )
        ).scalars().all()
        executed_km = sum((a.distance_m or 0) for a in acts) / 1000.0
        peak_planned = max(peak_planned, planned_km)
        peak_executed = max(peak_executed, executed_km)
        points.append(
            PlanVolumeCurvePoint(
                week_index=wi,
                phase=_phase_for(wi, plan.weeks),
                is_recovery=_is_recovery_week(ws),
                is_current=(wi == current_week_index),
                planned_km=round(planned_km, 2),
                executed_km=round(executed_km, 2),
                longest_run_km=round(longest, 2),
            )
        )

    return PlanVolumeCurveOut(
        plan_id=plan.id,
        weeks=points,
        peak_planned_km=round(peak_planned, 2),
        peak_executed_km=round(peak_executed, 2),
    )


# ── Block A1: Regenerate preview ─────────────────────────────────────────────


@router.get("/plans/{plan_id}/regenerate-preview", response_model=RegeneratePreviewOut)
def get_plan_regenerate_preview(
    plan_id: int,
    skill_slug: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
) -> RegeneratePreviewOut:
    plan = db.execute(
        select(TrainingPlan)
        .where(TrainingPlan.id == plan_id)
        .options(
            selectinload(TrainingPlan.structured_workouts),
            selectinload(TrainingPlan.race_goal),
        )
    ).scalar_one_or_none()
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    athlete = db.get(AthleteProfile, plan.athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="Athlete not found")

    try:
        skill = load_skill(skill_slug)
    except (FileNotFoundError, ValueError, AttributeError) as exc:
        raise HTTPException(status_code=404, detail=f"Skill not found: {skill_slug}") from exc

    today = date.today()
    frozen_workouts = [w for w in plan.structured_workouts if w.scheduled_date < today]
    future_workouts = [w for w in plan.structured_workouts if w.scheduled_date >= today]

    frozen_completed = sum(
        1 for w in frozen_workouts if w.status == WorkoutStatus.COMPLETED
    )
    frozen_missed = sum(
        1
        for w in frozen_workouts
        if w.status == WorkoutStatus.MISSED or w.feedback is None
    ) - sum(1 for w in frozen_workouts if w.status == WorkoutStatus.COMPLETED and w.feedback is None)
    # Simpler: missed = MISSED state OR (past and feedback is None and not completed)
    frozen_missed = sum(
        1
        for w in frozen_workouts
        if w.status == WorkoutStatus.MISSED
        or (w.feedback is None and w.status != WorkoutStatus.COMPLETED)
    )

    weeks_affected = len({w.week_index for w in future_workouts})
    days_affected_start = min((w.scheduled_date for w in future_workouts), default=None)
    days_affected_end = max((w.scheduled_date for w in future_workouts), default=None)

    # Build context to ask the skill if it's applicable.
    base_goal = plan.race_goal
    frozen_week_count = len({w.week_index for w in frozen_workouts}) if frozen_workouts else 0
    remaining_weeks = max(1, plan.weeks - frozen_week_count)

    derived_goal = RaceGoal(
        athlete_id=plan.athlete_id,
        sport=plan.sport,
        distance=base_goal.distance if base_goal else plan.sport.value,
        target_type=base_goal.target_type if base_goal else (
            "target_time" if plan.target_time_sec else "finish"
        ),
        target_time_sec=plan.target_time_sec,
        race_date=plan.race_date,
        training_start_date=today,
        plan_weeks=remaining_weeks,
    )

    availability = _availability_for(db, plan.athlete_id)
    from app.core.orchestrator import _build_context, _llm_enabled

    ctx = _build_context(
        db=db,
        athlete=athlete,
        availability=availability,
        race_goal=derived_goal,
        start_date=today,
        profile_block="",
        llm_enabled=_llm_enabled(),
    )
    ok, why = skill.applicable(ctx)

    # Estimate regenerated_count: assume same number as future_workouts when
    # applicable. (The actual generator is what knows the real count, so we
    # use the existing future workouts as a proxy.)
    regenerated_count = len(future_workouts) if ok else 0

    return RegeneratePreviewOut(
        plan_id=plan.id,
        new_skill_slug=skill_slug,
        applicable=ok,
        applicability_reason=why or "ok",
        frozen_completed=frozen_completed,
        frozen_missed=frozen_missed,
        regenerated_count=regenerated_count,
        weeks_affected=weeks_affected,
        days_affected_start=days_affected_start,
        days_affected_end=days_affected_end,
    )


# ── Block A1: Adjustment detail + apply ──────────────────────────────────────


def _adjustment_detail_out(adjustment: PlanAdjustment) -> PlanAdjustmentDetailOut:
    affected: list[AdjustmentAffectedWorkout] = []
    if adjustment.affected_workouts_json:
        try:
            data = json.loads(adjustment.affected_workouts_json)
            for entry in data or []:
                affected.append(AdjustmentAffectedWorkout(**entry))
        except (ValueError, TypeError):
            affected = []
    base = PlanAdjustmentOut.model_validate(adjustment).model_dump()
    return PlanAdjustmentDetailOut(**base, affected_workouts=affected)


@router.get("/plan-adjustments/{adjustment_id}", response_model=PlanAdjustmentDetailOut)
def get_plan_adjustment(
    adjustment_id: int, db: Session = Depends(get_db)
) -> PlanAdjustmentDetailOut:
    adjustment = db.get(PlanAdjustment, adjustment_id)
    if adjustment is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")
    return _adjustment_detail_out(adjustment)


def _format_distance_for_display(distance_m: float | None) -> str:
    if distance_m is None:
        return "0 km"
    return f"{distance_m / 1000.0:.1f} km"


def _parse_distance_to_m(value: str | float | int) -> float:
    """Accept 'NN km' or numeric meters."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s.endswith("km"):
        return float(s[:-2].strip()) * 1000.0
    if s.endswith("m"):
        return float(s[:-1].strip())
    return float(s)


@router.post("/plan-adjustments/{adjustment_id}/apply", response_model=PlanAdjustmentDetailOut)
def apply_plan_adjustment(
    adjustment_id: int,
    payload: PlanAdjustmentApplyRequest,
    db: Session = Depends(get_db),
) -> PlanAdjustmentDetailOut:
    adjustment = db.get(PlanAdjustment, adjustment_id)
    if adjustment is None:
        raise HTTPException(status_code=404, detail="Adjustment not found")

    affected_data: list[dict] = []
    if adjustment.affected_workouts_json:
        try:
            affected_data = json.loads(adjustment.affected_workouts_json) or []
        except (ValueError, TypeError):
            affected_data = []

    selected_ids = payload.selected_workout_ids
    selected_set: set[int] | None = set(selected_ids) if selected_ids is not None else None

    try:
        for entry in affected_data:
            wid = int(entry["workout_id"])
            if selected_set is not None and wid not in selected_set:
                continue
            workout = db.get(StructuredWorkout, wid)
            if workout is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"Affected workout {wid} not found",
                )
            field = entry.get("field")
            after = entry.get("after")
            if field == "distance_m":
                workout.distance_m = _parse_distance_to_m(after)
            elif field == "duration_min":
                workout.duration_min = int(_to_number(after))
            elif field == "skip":
                workout.status = WorkoutStatus.MISSED
                workout.distance_m = 0
            elif field == "workout_type":
                workout.workout_type = str(after)
            else:
                raise HTTPException(
                    status_code=422,
                    detail=f"Unknown affected workout field: {field}",
                )
            workout.updated_at = datetime.now(UTC)

        adjustment.status = AdjustmentStatus.CONFIRMED
        adjustment.confirmed_at = datetime.now(UTC)
        db.commit()
        db.refresh(adjustment)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Apply failed: {exc}") from exc

    return _adjustment_detail_out(adjustment)


def _to_number(value: str | float | int) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s.endswith("min"):
        return float(s[:-3].strip())
    return float(s)


# ── Block A1: Coach chat ─────────────────────────────────────────────────────


_AI_UNAVAILABLE_REPLY = "AI 教练当前不可用，请稍后再试"


@router.post("/coach/message", response_model=CoachMessageResponse)
def post_coach_message(
    payload: CoachMessageRequest,
    db: Session = Depends(get_db),
    _user: "User" = Depends(get_current_user),
) -> CoachMessageResponse:
    athlete = _athlete_or_404(db, payload.athlete_id)

    user_msg = CoachMessage(
        athlete_id=athlete.id, role="user", text=payload.message
    )
    db.add(user_msg)
    db.flush()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    coach_text = _AI_UNAVAILABLE_REPLY
    suggested_actions: list[dict] = []

    if api_key:
        try:
            from app.core.checkin import (
                get_latest_plan,
                get_recent_activities,
                get_upcoming_workouts,
                interpret_checkin,
            )

            plan = get_latest_plan(db)
            upcoming = get_upcoming_workouts(db, plan.id) if plan else []
            recent = get_recent_activities(db, athlete.id)
            history_rows = db.execute(
                select(CoachMessage)
                .where(CoachMessage.athlete_id == athlete.id)
                .order_by(CoachMessage.created_at.asc())
            ).scalars().all()
            conv_history = [
                {
                    "role": ("assistant" if m.role == "coach" else "user"),
                    "content": m.text,
                }
                for m in history_rows
                if m.id != user_msg.id
            ]
            result = interpret_checkin(
                user_message=payload.message,
                upcoming_workouts=upcoming,
                recent_activities=recent,
                profile_block=athlete.notes or "",
                conversation_history=conv_history,
                plan_title=plan.title if plan else "",
            )
            coach_text = result.get("reply") or _AI_UNAVAILABLE_REPLY
            suggested_actions = result.get("adjustments") or []
        except Exception as exc:  # pragma: no cover - LLM failure path
            coach_text = _AI_UNAVAILABLE_REPLY
            suggested_actions = []

    coach_msg = CoachMessage(
        athlete_id=athlete.id,
        role="coach",
        text=coach_text,
        suggested_actions_json=(
            json.dumps(suggested_actions, ensure_ascii=False) if suggested_actions else None
        ),
    )
    db.add(coach_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(coach_msg)

    return CoachMessageResponse(
        user_message=CoachMessageOut.model_validate(user_msg),
        coach_message=CoachMessageOut.model_validate(coach_msg),
    )


@router.get(
    "/coach/conversations/{athlete_id}", response_model=list[CoachMessageOut]
)
def get_coach_conversations(
    athlete_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[CoachMessageOut]:
    _athlete_or_404(db, athlete_id)
    rows = db.execute(
        select(CoachMessage)
        .where(CoachMessage.athlete_id == athlete_id)
        .order_by(CoachMessage.created_at.desc())
        .limit(limit)
    ).scalars().all()
    return [CoachMessageOut.model_validate(r) for r in rows]
