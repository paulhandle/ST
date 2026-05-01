#!/usr/bin/env python3
"""
ST Training Planner CLI

Pulls all COROS history, assesses running ability, and generates a
personalized marathon training plan using LLM.

Usage:
    uv run python scripts/st_cli.py
    uv run python scripts/st_cli.py --goal 3:45 --weeks 12
    uv run python scripts/st_cli.py --goal 4:00 --weeks 8 --sync
    uv run python scripts/st_cli.py --help
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.core.config import load_local_env

load_local_env()

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import DATABASE_URL
from app.models import (
    AthleteLevel,
    AthleteProfile,
    Base,
    DeviceAccount,
    DeviceType,
    SportType,
    StructuredWorkout,
    TrainingPlan,
)
from app.coros.automation import RealCorosAutomationClient
from app.ingestion.service import import_provider_history
from app.assessment.running import assess_running_ability
from app.planning.marathon import generate_marathon_plan

# ── ANSI ─────────────────────────────────────────────────────────────────────
B = "\033[1m"
G = "\033[32m"
Y = "\033[33m"
C = "\033[36m"
R = "\033[31m"
D = "\033[2m"
X = "\033[0m"

_PHASE_COLOR = {"base": "\033[34m", "build": "\033[33m", "peak": "\033[31m", "taper": "\033[32m"}
_TYPE_LABEL  = {"easy_run": "Easy Run", "long_run": "Long Run",
                "marathon_pace": "Marathon Pace", "threshold": "Threshold"}


# ── formatting helpers ────────────────────────────────────────────────────────

def _fmt_time(sec: int) -> str:
    return f"{sec // 3600}:{(sec % 3600) // 60:02d}"

def _fmt_pace(sec_per_km: float) -> str:
    return f"{int(sec_per_km // 60)}:{int(sec_per_km % 60):02d}"

def _fmt_dur(minutes: int) -> str:
    if minutes >= 60:
        h, m = divmod(minutes, 60)
        return f"{h}h{m:02d}m" if m else f"{h}h    "
    return f"{minutes:3d}min"

def _phase(week_idx: int, total: int) -> str:
    p = week_idx / total
    return "base" if p <= 0.50 else "build" if p <= 0.82 else "peak" if p <= 0.94 else "taper"

def _sep(char="─", width=68):
    print(f"{D}{char * width}{X}")

def _header(title: str, width=68):
    print()
    _sep("═", width)
    pad = (width - len(title) - 2) // 2
    print(f"{B}{'═' * pad} {title} {'═' * (width - pad - len(title) - 2)}{X}")
    _sep("═", width)

def _step(n: int, total: int, msg: str):
    print(f"\n{B}[{n}/{total}]{X} {msg}", flush=True)

def _ok(msg=""):    print(f"  {G}✓{X} {msg}", flush=True)
def _warn(msg=""):  print(f"  {Y}⚠ {msg}{X}", flush=True)
def _err(msg=""):   print(f"  {R}✗ {msg}{X}", flush=True)
def _info(msg=""):  print(f"  {D}{msg}{X}", flush=True)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_or_create_athlete(db: Session, name: str) -> AthleteProfile:
    a = db.execute(select(AthleteProfile).limit(1)).scalar_one_or_none()
    if a is None:
        a = AthleteProfile(name=name, sport=SportType.RUNNING,
                           level=AthleteLevel.INTERMEDIATE, weekly_training_days=5)
        db.add(a)
        db.commit()
        db.refresh(a)
    return a

def _get_or_create_device_account(db: Session, athlete: AthleteProfile, username: str):
    acc = db.execute(
        select(DeviceAccount).where(
            DeviceAccount.athlete_id == athlete.id,
            DeviceAccount.device_type == DeviceType.COROS,
        )
    ).scalar_one_or_none()
    if acc is None:
        acc = DeviceAccount(athlete_id=athlete.id, device_type=DeviceType.COROS,
                            username=username, auth_status="connected")
        db.add(acc)
        db.commit()
        db.refresh(acc)
    return acc


# ── display ───────────────────────────────────────────────────────────────────

def _print_assessment(a: dict, target_sec: int):
    print()
    score = a["overall_score"]
    sc = G if score >= 70 else Y if score >= 50 else R
    print(f"  {B}Fitness Score   :{X} {sc}{score}/100{X}  "
          f"({a['readiness_level']} readiness · {a['confidence']} confidence)")
    lo, hi = a["estimated_marathon_time_range_sec"]
    print(f"  {B}Marathon estimate:{X} {C}{_fmt_time(lo)} – {_fmt_time(hi)}{X}")
    print(f"  {B}Your goal        :{X} {C}{_fmt_time(target_sec)}{X}")
    wl, wh = a["safe_weekly_distance_range_km"]
    print(f"  {B}Safe weekly vol  :{X} {wl:.0f}–{wh:.0f} km  "
          f"│  Long run capacity: {a['long_run_capacity_km']:.1f} km")
    for w in a["warnings"]:
        _warn(w)
    if a["limiting_factors"]:
        _info("Limiting: " + ", ".join(a["limiting_factors"]))
    _sep()


def _print_plan(plan_info: dict):
    _header(f"{plan_info['title']}  │  {plan_info['weeks']} weeks")
    tgt = plan_info["target_time_sec"]
    target_pace = tgt / 42.195 if tgt else None
    print(f"  Start : {plan_info['start_date']}   Race : {plan_info['race_date']}")
    if target_pace:
        print(f"  Goal  : {_fmt_time(tgt)}   Target pace: {_fmt_pace(target_pace)}/km")
    print()

    by_week: dict[int, list[dict]] = defaultdict(list)
    for w in plan_info["workouts"]:
        by_week[w["week_index"]].append(w)

    total_weeks = plan_info["weeks"]
    for wk in sorted(by_week):
        workouts = by_week[wk]
        total_km = sum(w["distance_m"] for w in workouts) / 1000
        ph = _phase(wk, total_weeks)
        pc = _PHASE_COLOR.get(ph, "")
        print(f"  {B}Week {wk:2d}{X}  {pc}{ph.upper():5s}{X}  {total_km:5.1f} km")
        for w in sorted(workouts, key=lambda x: x["scheduled_date"]):
            d = w["scheduled_date"]
            day = d.strftime("%a %m/%d") if hasattr(d, "strftime") else str(d)
            label = _TYPE_LABEL.get(w["workout_type"], w["workout_type"].replace("_", " ").title())
            km = w["distance_m"] / 1000
            dur = _fmt_dur(w["duration_min"])
            pm = _fmt_pace(w["target_pace_min_sec_per_km"]) if w.get("target_pace_min_sec_per_km") else "—"
            px = _fmt_pace(w["target_pace_max_sec_per_km"]) if w.get("target_pace_max_sec_per_km") else "—"
            rpe = f"RPE {w.get('rpe_min', '?')}-{w.get('rpe_max', '?')}"
            print(f"    {D}{day}{X}  {label:<16s}  {km:5.1f} km  {dur}  {D}[{pm}–{px}]{X}  {D}{rpe}{X}")
        print()


def _collect_plan(db: Session, plan_id: int) -> dict:
    plan = db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id)).scalar_one()
    workouts = db.execute(
        select(StructuredWorkout)
        .where(StructuredWorkout.plan_id == plan_id)
        .order_by(StructuredWorkout.scheduled_date)
    ).scalars().all()
    return {
        "id": plan.id,
        "title": plan.title,
        "weeks": plan.weeks,
        "start_date": plan.start_date,
        "race_date": plan.race_date,
        "target_time_sec": plan.target_time_sec,
        "workouts": [
            {
                "week_index": w.week_index,
                "scheduled_date": w.scheduled_date,
                "workout_type": w.workout_type,
                "title": w.title,
                "distance_m": w.distance_m,
                "duration_min": w.duration_min,
                "target_pace_min_sec_per_km": w.target_pace_min_sec_per_km,
                "target_pace_max_sec_per_km": w.target_pace_max_sec_per_km,
                "rpe_min": w.rpe_min,
                "rpe_max": w.rpe_max,
            }
            for w in workouts
        ],
    }


# ── sync ──────────────────────────────────────────────────────────────────────

def _sync_to_coros(client: RealCorosAutomationClient, plan_info: dict, username: str):
    print()
    total = len(plan_info["workouts"])
    print(f"  Pushing {total} workouts to COROS calendar…", flush=True)
    synced = failed = 0
    for w in sorted(plan_info["workouts"], key=lambda x: x["scheduled_date"]):
        d = w["scheduled_date"]
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
        try:
            client.sync_workouts(username, [{
                "id": f"st-{plan_info['id']}-{w['week_index']}-{w['workout_type']}",
                "title": w["title"],
                "scheduled_date": date_str,
                "workout_type": w["workout_type"],
                "duration_sec": w["duration_min"] * 60,
            }])
            synced += 1
            print(f"  {G}✓{X} {date_str}  {w['title']}", flush=True)
        except Exception as exc:
            failed += 1
            print(f"  {R}✗{X} {date_str}  {w['title']}  — {exc}", flush=True)
    if failed == 0:
        _ok(f"All {synced} workouts synced to COROS!")
    else:
        _warn(f"{synced} synced, {failed} failed.")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ST Marathon Training Planner — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  uv run python scripts/st_cli.py
  uv run python scripts/st_cli.py --goal 3:45 --weeks 12
  uv run python scripts/st_cli.py --goal 4:00 --weeks 8 --sync
""",
    )
    parser.add_argument("--goal", default="4:00",
                        help="Marathon goal time H:MM  (default: 4:00)")
    parser.add_argument("--weeks", type=int, default=8,
                        help="Training weeks  (default: 8)")
    parser.add_argument("--days-history", type=int, default=730,
                        help="Days of COROS history to pull  (default: 730 = 2 years)")
    parser.add_argument("--training-days", type=int, default=5,
                        help="Training days per week  (default: 5)")
    parser.add_argument("--long-run-day", type=int, default=6,
                        help="Preferred long run weekday 0=Mon…6=Sun  (default: 6=Sun)")
    parser.add_argument("--sync", action="store_true",
                        help="Push plan to COROS calendar after generation")
    parser.add_argument("--athlete-name", default="Paul",
                        help="Athlete display name  (default: Paul)")
    args = parser.parse_args()

    try:
        target_sec = int(args.goal.split(":")[0]) * 3600 + int(args.goal.split(":")[1]) * 60
    except (ValueError, IndexError):
        _err(f"Invalid --goal '{args.goal}'. Use H:MM format, e.g. 4:00")
        sys.exit(1)

    username = os.environ.get("COROS_USERNAME", "")
    password = os.environ.get("COROS_PASSWORD", "")
    if not username or not password:
        _err("COROS_USERNAME / COROS_PASSWORD not set — add them to .env")
        sys.exit(1)

    total_steps = 5 if args.sync else 4

    _header("ST Training Planner — Full Marathon", width=68)
    print(f"  Athlete : {B}{args.athlete_name}{X}  ({username})")
    print(f"  Goal    : {C}{args.goal} full marathon{X}   Plan: {args.weeks} weeks")
    print(f"  History : last {args.days_history} days   Training days: {args.training_days}/week")

    # ── 1. Login ──────────────────────────────────────────────────────────────
    _step(1, total_steps, "Connecting to COROS…")
    client = RealCorosAutomationClient()
    result = client.login(username, password)
    if not result.ok:
        _err(f"Login failed: {result.message}")
        sys.exit(1)
    _ok(result.message)

    # ── 2. Import history ─────────────────────────────────────────────────────
    _step(2, total_steps, f"Importing {args.days_history} days of running history…")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        athlete = _get_or_create_athlete(db, args.athlete_name)
        _get_or_create_device_account(db, athlete, username)
        history = client.fetch_history(username, days_back=args.days_history)
        stats = import_provider_history(
            db=db,
            athlete=athlete,
            provider="coros",
            activities=history["activities"],
            metrics=history["metrics"],
        )
    _ok(
        f"{stats['imported_count']} new + {stats['updated_count']} updated activities  │"
        f"  {stats['metric_count']} metrics"
    )
    _info(f"Total activities pulled: {len(history['activities'])}")

    # ── 3. Assess ─────────────────────────────────────────────────────────────
    _step(3, total_steps, "Assessing running ability…")
    with Session(engine) as db:
        athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one()
        assessment = assess_running_ability(
            db=db,
            athlete_id=athlete.id,
            target_time_sec=target_sec,
            plan_weeks=args.weeks,
            requested_training_days=args.training_days,
        )
    _print_assessment(assessment, target_sec)

    if assessment["goal_status"] == "reject":
        _err("Goal rejected as unsafe or unrealistic. Try --weeks 12 or a slower --goal.")
        sys.exit(1)
    if assessment["goal_status"] in {"accept_with_warning", "recommend_adjustment"}:
        _warn("Goal accepted with caution — plan will be conservative.")

    # ── 4. Generate plan ──────────────────────────────────────────────────────
    _step(4, total_steps, "Generating plan with LLM…")

    start_date = _next_monday()
    race_date = start_date + timedelta(weeks=args.weeks)

    request = SimpleNamespace(
        target_time_sec=target_sec,
        race_date=race_date,
        training_start_date=start_date,
        plan_weeks=args.weeks,
        availability=SimpleNamespace(
            weekly_training_days=args.training_days,
            preferred_long_run_weekday=args.long_run_day,
            unavailable_weekdays=[],
            max_weekday_duration_min=90,
            max_weekend_duration_min=180,
            strength_training_enabled=False,
            notes="",
        ),
    )

    plan_id: int
    with Session(engine) as db:
        athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one()
        plan, rejection_reason = generate_marathon_plan(db, athlete, request)
        if plan is None:
            _err(f"Plan rejected: {rejection_reason}")
            sys.exit(1)
        plan_id = plan.id

    with Session(engine) as db:
        plan_info = _collect_plan(db, plan_id)

    _print_plan(plan_info)
    _ok(f"Plan saved to DB  (id={plan_id})")

    # ── 5. Sync (optional) ────────────────────────────────────────────────────
    if args.sync:
        _step(5, total_steps, "Syncing to COROS calendar…")
        _warn(f"This will make {len(plan_info['workouts'])} API calls — one per workout.")
        _sync_to_coros(client, plan_info, username)
    else:
        print()
        _info("Tip: run with --sync to push the plan to your COROS calendar.")

    _header("Done", width=68)
    print()


def _next_monday() -> date:
    today = date.today()
    days = (7 - today.weekday()) % 7
    return today + timedelta(days=days or 7)


if __name__ == "__main__":
    main()
