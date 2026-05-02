from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.kb.running_assessment import assess_running_ability
from app.tools.coros.automation import coros_automation_client
from app.tools.coros.credentials import encrypt_secret
from app.tools.coros.sync import sync_confirmed_plan_to_coros
from app.db import get_db
from app.tools.devices.service import sync_plan_to_device
from app.ingestion.service import import_provider_history
from app.models import (
    AdjustmentStatus,
    AthleteActivity,
    AthleteProfile,
    DeviceAccount,
    DeviceType,
    PlanAdjustment,
    PlanStatus,
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
    AthleteActivityOut,
    AthleteCreate,
    AthleteOut,
    CorosConnectRequest,
    CorosStatusOut,
    DeviceAccountOut,
    DeviceConnectRequest,
    HistoryImportOut,
    HistoryImportRequest,
    MarathonGoalCreate,
    MarathonPlanGenerateRequest,
    MarathonPlanOut,
    MatchDiff,
    ModeRecommendationOut,
    PlanAdjustmentOut,
    PlanConfirmOut,
    PlanGenerateRequest,
    PlanStatusUpdate,
    PlanSyncOut,
    ProviderSyncRecordOut,
    RaceGoalOut,
    RegenerateFromTodayOut,
    RegenerateFromTodayRequest,
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
    return {"status": "ok", "service": "ST"}


@router.get("/sports")
def sports() -> list[dict[str, str]]:
    return [
        {"code": SportType.MARATHON.value, "name": "马拉松"},
        {"code": SportType.TRAIL_RUNNING.value, "name": "越野跑"},
        {"code": SportType.TRIATHLON.value, "name": "铁人三项"},
    ]


@router.post("/athletes", response_model=AthleteOut)
def create_athlete(request: AthleteCreate, db: Session = Depends(get_db)):
    athlete = AthleteProfile(**request.model_dump())
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
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    return _training_plan_or_404(db, plan_id)


@router.patch("/plans/{plan_id}/status", response_model=TrainingPlanOut)
def update_plan_status(plan_id: int, request: PlanStatusUpdate, db: Session = Depends(get_db)):
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = request.status
    plan.updated_at = datetime.now(UTC)
    db.commit()
    return _training_plan_or_404(db, plan_id)


@router.post("/devices/connect", response_model=DeviceAccountOut)
def connect_device(request: DeviceConnectRequest, db: Session = Depends(get_db)):
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
def sync_plan(plan_id: int, request: SyncPlanRequest, db: Session = Depends(get_db)):
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
def connect_coros(request: CorosConnectRequest, db: Session = Depends(get_db)):
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
def coros_status(athlete_id: int, db: Session = Depends(get_db)):
    account = _device_account(db, athlete_id, DeviceType.COROS)
    if account is None:
        return CorosStatusOut(athlete_id=athlete_id, connected=False, auth_status="disconnected")
    return CorosStatusOut(
        athlete_id=athlete_id,
        connected=account.auth_status == "connected",
        auth_status=account.auth_status,
        username=account.username,
        last_login_at=account.last_login_at,
        last_import_at=account.last_import_at,
        last_sync_at=account.last_sync_at,
        last_error=account.last_error,
    )


@router.post("/coros/import", response_model=HistoryImportOut)
def import_coros_history(request: HistoryImportRequest, athlete_id: int, db: Session = Depends(get_db)):
    return _import_history(db=db, athlete_id=athlete_id, device_type=DeviceType.COROS)


@router.post("/athletes/{athlete_id}/history/import", response_model=HistoryImportOut)
def import_history(athlete_id: int, request: HistoryImportRequest, db: Session = Depends(get_db)):
    return _import_history(db=db, athlete_id=athlete_id, device_type=request.device_type)


@router.get("/athletes/{athlete_id}/history", response_model=list[AthleteActivityOut])
def get_history(athlete_id: int, db: Session = Depends(get_db)):
    _athlete_or_404(db, athlete_id)
    return db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .order_by(AthleteActivity.started_at.desc())
    ).scalars().all()


@router.get("/athletes/{athlete_id}/assessment", response_model=RunningAssessmentOut)
def get_assessment(athlete_id: int, db: Session = Depends(get_db)):
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
def create_goal(request: MarathonGoalCreate, db: Session = Depends(get_db)):
    athlete = _athlete_or_404(db, request.athlete_id)
    return _orchestrator_create_race_goal(
        db=db, athlete=athlete, request=request, sport=SportType.MARATHON
    )


@router.post("/marathon/plans/generate", response_model=MarathonPlanOut)
def create_marathon_plan(request: MarathonPlanGenerateRequest, db: Session = Depends(get_db)):
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
def get_marathon_plan(plan_id: int, db: Session = Depends(get_db)):
    return _marathon_plan_or_404(db, plan_id)


@router.post("/plans/{plan_id}/confirm", response_model=PlanConfirmOut)
def confirm_plan(plan_id: int, db: Session = Depends(get_db)):
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
def sync_plan_to_coros(plan_id: int, db: Session = Depends(get_db)):
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
def evaluate_adjustment(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(TrainingPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return evaluate_plan_adjustment(db=db, plan=plan)


@router.post("/plan-adjustments/{adjustment_id}/confirm", response_model=PlanAdjustmentOut)
def confirm_plan_adjustment(adjustment_id: int, db: Session = Depends(get_db)):
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
        if account is None:
            account = DeviceAccount(
                athlete_id=athlete_id,
                device_type=DeviceType.COROS,
                external_user_id=f"coros_user_{athlete_id}",
                username=f"coros_user_{athlete_id}",
                encrypted_password=encrypt_secret("local-fake-password"),
                auth_status="connected",
            )
            db.add(account)
            db.flush()
        client = coros_automation_client()
        history = client.fetch_history(account.username or account.external_user_id)
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
        select(DeviceAccount).where(
            DeviceAccount.athlete_id == athlete_id,
            DeviceAccount.device_type == device_type,
        )
    ).scalar_one_or_none()


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
def get_today(athlete_id: int, db: Session = Depends(get_db)) -> TodayOut:
    _athlete_or_404(db, athlete_id)
    plan = _active_or_draft_plan_for_athlete(db, athlete_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="No active or draft plan for this athlete")

    today = date.today()
    workout: StructuredWorkout | None = next(
        (w for w in plan.structured_workouts if w.scheduled_date == today),
        None,
    )

    matched_activity_id: int | None = None
    workout_out: StructuredWorkoutOut | None = None
    if workout is not None:
        workout_out = StructuredWorkoutOut.model_validate(workout)
        activity = match_workout_to_activity(db, workout)
        if activity is not None:
            matched_activity_id = activity.id

    return TodayOut(
        plan_id=plan.id,
        plan_title=plan.title,
        skill_slug=plan.active_skill_slug,
        week_index=workout.week_index if workout else None,
        workout=workout_out,
        matched_activity_id=matched_activity_id,
    )


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
        unavailable_weekdays = (
            [int(v) for v in (row.unavailable_weekdays or "").split(",") if v.strip().isdigit()]
            if row
            else []
        )
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
        matched_out = AthleteActivityOut.model_validate(activity)
        diff = MatchDiff(**compute_match_diff(workout, activity))
    return WorkoutMatchStatusOut(workout_id=workout.id, matched_activity=matched_out, diff=diff)
