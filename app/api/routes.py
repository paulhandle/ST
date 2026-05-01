from __future__ import annotations

from datetime import UTC, datetime

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
    WorkoutStatus,
)
from app.core.orchestrator import (
    create_race_goal as _orchestrator_create_race_goal,
    generate_plan_via_skill,
)
from app.core.adjustment import confirm_adjustment, evaluate_plan_adjustment
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
    ModeRecommendationOut,
    PlanAdjustmentOut,
    PlanConfirmOut,
    PlanGenerateRequest,
    PlanStatusUpdate,
    PlanSyncOut,
    ProviderSyncRecordOut,
    RaceGoalOut,
    RunningAssessmentOut,
    SyncPlanRequest,
    SyncTaskOut,
    TrainingMethodOut,
    TrainingPlanOut,
)
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
        skill_slug="marathon_st_default",
        race_goal=race_goal,
    )
    if plan is None:
        raise HTTPException(status_code=422, detail=error)
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
