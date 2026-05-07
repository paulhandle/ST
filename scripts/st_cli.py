#!/usr/bin/env python3
"""
ST Training Planner — CLI

Commands:
  setup     Build your athlete profile (one-time)
  plan      Pull COROS history and generate a marathon plan
  checkin   Daily/weekly check-in chat to adapt the plan

Usage:
  uv run python scripts/st_cli.py setup
  uv run python scripts/st_cli.py plan --goal 4:00 --weeks 8
  uv run python scripts/st_cli.py plan --goal 4:00 --weeks 8 --sync
  uv run python scripts/st_cli.py checkin
  uv run python scripts/st_cli.py checkin --sync  # pull fresh COROS data first
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
from app.core.profile import (
    AthleteProfileData,
    PROFILE_PATH,
    load_profile,
    profile_to_prompt_block,
    save_profile,
)
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
from app.tools.coros.automation import RealCorosAutomationClient
from app.ingestion.service import import_provider_history
from app.kb.running_assessment import assess_running_ability
from app.core.orchestrator import generate_plan_via_skill
from app.core.checkin import (
    apply_adjustments,
    get_latest_plan,
    get_recent_activities,
    get_rich_training_context,
    get_upcoming_workouts,
    interpret_checkin,
)

# ── ANSI ─────────────────────────────────────────────────────────────────────
B = "\033[1m"
G = "\033[32m"
Y = "\033[33m"
C = "\033[36m"
R = "\033[31m"
D = "\033[2m"
X = "\033[0m"
_PHASE_COLOR = {"base": "\033[34m", "build": "\033[33m", "peak": "\033[31m", "taper": "\033[32m"}
_TYPE_LABEL = {
    "easy_run": "Easy Run", "long_run": "Long Run",
    "marathon_pace": "Marathon Pace", "threshold": "Threshold",
}

# ── formatting ────────────────────────────────────────────────────────────────

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

def _sep(char="─", width=68): print(f"{D}{char * width}{X}")
def _header(title: str, width=68):
    print(); _sep("═", width)
    pad = (width - len(title) - 2) // 2
    print(f"{B}{'═'*pad} {title} {'═'*(width-pad-len(title)-2)}{X}")
    _sep("═", width)
def _step(n, t, msg):  print(f"\n{B}[{n}/{t}]{X} {msg}", flush=True)
def _ok(msg=""):   print(f"  {G}✓{X} {msg}", flush=True)
def _warn(msg=""):  print(f"  {Y}⚠ {msg}{X}", flush=True)
def _err(msg=""):   print(f"  {R}✗ {msg}{X}", flush=True)
def _info(msg=""):  print(f"  {D}{msg}{X}", flush=True)

# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_or_create_athlete(db: Session, name: str) -> AthleteProfile:
    a = db.execute(select(AthleteProfile).limit(1)).scalar_one_or_none()
    if a is None:
        a = AthleteProfile(name=name, sport=SportType.MARATHON,
                           level=AthleteLevel.INTERMEDIATE, weekly_training_days=5)
        db.add(a); db.commit(); db.refresh(a)
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
        db.add(acc); db.commit(); db.refresh(acc)
    return acc

def _collect_plan(db: Session, plan_id: int) -> dict:
    plan = db.execute(select(TrainingPlan).where(TrainingPlan.id == plan_id)).scalar_one()
    workouts = db.execute(
        select(StructuredWorkout)
        .where(StructuredWorkout.plan_id == plan_id)
        .order_by(StructuredWorkout.scheduled_date)
    ).scalars().all()
    return {
        "id": plan.id, "title": plan.title, "weeks": plan.weeks,
        "start_date": plan.start_date, "race_date": plan.race_date,
        "target_time_sec": plan.target_time_sec,
        "workouts": [
            {"week_index": w.week_index, "scheduled_date": w.scheduled_date,
             "workout_type": w.workout_type, "title": w.title,
             "distance_m": w.distance_m, "duration_min": w.duration_min,
             "target_pace_min_sec_per_km": w.target_pace_min_sec_per_km,
             "target_pace_max_sec_per_km": w.target_pace_max_sec_per_km,
             "rpe_min": w.rpe_min, "rpe_max": w.rpe_max}
            for w in workouts
        ],
    }

# ── display ───────────────────────────────────────────────────────────────────

def _print_assessment(a: dict, target_sec: int):
    print()
    sc = G if a["overall_score"] >= 70 else Y if a["overall_score"] >= 50 else R
    print(f"  {B}Fitness Score    :{X} {sc}{a['overall_score']}/100{X}  "
          f"({a['readiness_level']} · {a['confidence']} confidence)")
    lo, hi = a["estimated_marathon_time_range_sec"]
    print(f"  {B}Marathon estimate:{X} {C}{_fmt_time(lo)} – {_fmt_time(hi)}{X}")
    print(f"  {B}Your goal        :{X} {C}{_fmt_time(target_sec)}{X}")
    wl, wh = a["safe_weekly_distance_range_km"]
    print(f"  {B}Safe weekly vol  :{X} {wl:.0f}–{wh:.0f} km  │  Long run capacity: {a['long_run_capacity_km']:.1f} km")
    for w in a["warnings"]: _warn(w)
    if a["limiting_factors"]: _info("Limiting: " + ", ".join(a["limiting_factors"]))
    _sep()

def _print_plan(plan_info: dict):
    _header(f"{plan_info['title']}  │  {plan_info['weeks']} weeks", width=68)
    tgt = plan_info["target_time_sec"]
    if tgt:
        print(f"  Goal  : {_fmt_time(tgt)}   Target pace: {_fmt_pace(tgt / 42.195)}/km")
    print(f"  Start : {plan_info['start_date']}   Race : {plan_info['race_date']}\n")

    by_week: dict[int, list] = defaultdict(list)
    for w in plan_info["workouts"]:
        by_week[w["week_index"]].append(w)

    for wk in sorted(by_week):
        ws = by_week[wk]
        total_km = sum(w["distance_m"] for w in ws) / 1000
        ph = _phase(wk, plan_info["weeks"])
        pc = _PHASE_COLOR.get(ph, "")
        print(f"  {B}Week {wk:2d}{X}  {pc}{ph.upper():5s}{X}  {total_km:5.1f} km")
        for w in sorted(ws, key=lambda x: x["scheduled_date"]):
            d = w["scheduled_date"]
            day = d.strftime("%a %m/%d") if hasattr(d, "strftime") else str(d)
            label = _TYPE_LABEL.get(w["workout_type"], w["workout_type"].replace("_", " ").title())
            km = w["distance_m"] / 1000
            dur = _fmt_dur(w["duration_min"])
            pm = _fmt_pace(w["target_pace_min_sec_per_km"]) if w.get("target_pace_min_sec_per_km") else "—"
            px = _fmt_pace(w["target_pace_max_sec_per_km"]) if w.get("target_pace_max_sec_per_km") else "—"
            print(f"    {D}{day}{X}  {label:<16s}  {km:5.1f} km  {dur}  {D}[{pm}–{px}]{X}  {D}RPE {w.get('rpe_min','?')}-{w.get('rpe_max','?')}{X}")
        print()

def _sync_to_coros(client, plan_info: dict, username: str):
    total = len(plan_info["workouts"])
    print(f"  Pushing {total} workouts to COROS…", flush=True)
    synced = failed = 0
    for w in sorted(plan_info["workouts"], key=lambda x: x["scheduled_date"]):
        d = w["scheduled_date"]
        date_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
        try:
            client.sync_workouts(username, [{
                "id": f"st-{plan_info['id']}-w{w['week_index']}-{w['workout_type']}",
                "title": w["title"], "scheduled_date": date_str,
                "workout_type": w["workout_type"], "duration_sec": w["duration_min"] * 60,
            }])
            synced += 1; print(f"  {G}✓{X} {date_str}  {w['title']}", flush=True)
        except Exception as exc:
            failed += 1; print(f"  {R}✗{X} {date_str}  {w['title']}  — {exc}", flush=True)
    if failed == 0: _ok(f"All {synced} workouts synced to COROS!")
    else: _warn(f"{synced} synced, {failed} failed.")

def _next_monday() -> date:
    today = date.today()
    days = (7 - today.weekday()) % 7
    return today + timedelta(days=days or 7)


# ── cmd: setup ────────────────────────────────────────────────────────────────

def cmd_setup(_args):
    _header("ST Athlete Setup", width=68)
    print(f"  Building your training profile. Press {D}Enter{X} to skip any field.\n")

    def ask(prompt: str, default=None, choices: list[str] | None = None) -> str:
        hint = f" [{'/'.join(choices)}]" if choices else (f" [{default}]" if default else "")
        while True:
            raw = input(f"  {prompt}{hint}: ").strip()
            if not raw:
                return default or ""
            if choices and raw not in choices:
                print(f"  {Y}Please choose from: {', '.join(choices)}{X}")
                continue
            return raw

    def ask_num(prompt: str, default=None, typ=float):
        raw = ask(prompt, str(default) if default else None)
        if not raw:
            return default
        try:
            return typ(raw)
        except ValueError:
            return default

    p = load_profile()  # start from existing if any

    print(f"  {B}Basic info{X}")
    p.name           = ask("Your name", p.name or "Athlete")
    p.age            = ask_num("Age", p.age, int)
    p.sex            = ask("Sex", p.sex, ["male", "female", "other"])
    p.height_cm      = ask_num("Height (cm)", p.height_cm)
    p.weight_kg      = ask_num("Weight (kg)", p.weight_kg)
    p.years_running  = ask_num("Years running", p.years_running, int)

    print(f"\n  {B}Health & lifestyle{X}")
    p.injury_history   = ask("Injury history (or 'none')", p.injury_history or "none")
    if p.injury_history == "none":
        p.injury_history = ""
    p.avg_sleep_hours = ask_num("Average sleep hours/night", p.avg_sleep_hours)
    p.work_stress     = ask("Life/work stress level", p.work_stress, ["low", "moderate", "high"])
    p.resting_hr      = ask_num("Resting heart rate (bpm)", p.resting_hr, int)

    print(f"\n  {B}Recent race performance{X}")
    p.last_race_distance = ask("Last race distance", p.last_race_distance,
                               ["marathon", "half_marathon", "10k", "5k", "other"])
    p.last_race_time     = ask("Last race finishing time (H:MM or MM:SS)", p.last_race_time)
    p.last_race_date     = ask("Last race date (YYYY-MM)", p.last_race_date)

    print(f"\n  {B}Anything else for your coach?{X}")
    p.notes = ask("Notes (injuries, constraints, preferences)", p.notes)

    save_profile(p)
    print()
    _ok(f"Profile saved → {PROFILE_PATH}")
    print(f"\n  {D}Run 'st_cli.py plan' to generate your training plan.{X}\n")


# ── cmd: plan ─────────────────────────────────────────────────────────────────

def cmd_plan(args):
    try:
        target_sec = int(args.goal.split(":")[0]) * 3600 + int(args.goal.split(":")[1]) * 60
    except (ValueError, IndexError):
        _err(f"Invalid --goal '{args.goal}'. Use H:MM, e.g. 4:00"); sys.exit(1)

    username = os.environ.get("COROS_USERNAME", "")
    password = os.environ.get("COROS_PASSWORD", "")
    if not username or not password:
        _err("Export COROS_USERNAME / COROS_PASSWORD in the current shell for this CLI run"); sys.exit(1)

    profile = load_profile()
    athlete_name = profile.name if profile.name and profile.name != "Athlete" else args.athlete_name

    total = 5 if args.sync else 4
    _header("ST Training Planner — Full Marathon", width=68)
    print(f"  Athlete : {B}{athlete_name}{X}  ({username})")
    print(f"  Goal    : {C}{args.goal} full marathon{X}   Plan: {args.weeks} weeks")
    if PROFILE_PATH.exists():
        _info(f"Profile loaded from {PROFILE_PATH}")
    else:
        _warn("No profile found — run 'st_cli.py setup' for a better plan")

    # 1. Login
    _step(1, total, "Connecting to COROS…")
    client = RealCorosAutomationClient()
    r = client.login(username, password)
    if not r.ok: _err(f"Login failed: {r.message}"); sys.exit(1)
    _ok(r.message)

    # 2. Import
    _step(2, total, f"Importing {args.days_history} days of running history…")
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        athlete = _get_or_create_athlete(db, athlete_name)
        _get_or_create_device_account(db, athlete, username)
        history = client.fetch_history(username, days_back=args.days_history)
        stats = import_provider_history(db=db, athlete=athlete, provider="coros",
                                        activities=history["activities"], metrics=history["metrics"])
    _ok(f"{stats['imported_count']} new + {stats['updated_count']} updated  │  {stats['metric_count']} metrics")
    _info(f"Total pulled: {len(history['activities'])} activities")

    # 3. Assess
    _step(3, total, "Assessing running ability…")
    with Session(engine) as db:
        athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one()
        assessment = assess_running_ability(db=db, athlete_id=athlete.id,
                                            target_time_sec=target_sec, plan_weeks=args.weeks,
                                            requested_training_days=args.training_days)
        rich_ctx = get_rich_training_context(db, athlete.id)
    _print_assessment(assessment, target_sec)

    if assessment["goal_status"] == "reject":
        _err("Goal rejected. Try --weeks 12 or a slower --goal."); sys.exit(1)
    if assessment["goal_status"] in {"accept_with_warning", "recommend_adjustment"}:
        _warn("Goal accepted with caution — plan will be conservative.")

    # 4. Generate
    _step(4, total, "Generating plan with LLM…")
    start_date = _next_monday()
    race_date  = start_date + timedelta(weeks=args.weeks)
    request = SimpleNamespace(
        target_time_sec=target_sec, race_date=race_date,
        training_start_date=start_date, plan_weeks=args.weeks,
        availability=SimpleNamespace(
            weekly_training_days=args.training_days,
            preferred_long_run_weekday=args.long_run_day,
            unavailable_weekdays=[], max_weekday_duration_min=90,
            max_weekend_duration_min=180, strength_training_enabled=False, notes="",
        ),
        profile_block=profile_to_prompt_block(profile),
        rich_context=rich_ctx,
    )

    plan_id: int
    with Session(engine) as db:
        athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one()
        plan, rejection = generate_plan_via_skill(
            db=db, athlete=athlete, request=request, skill_slug="marathon_st_default",
        )
        if plan is None: _err(f"Plan rejected: {rejection}"); sys.exit(1)
        plan_id = plan.id

    with Session(engine) as db:
        plan_info = _collect_plan(db, plan_id)

    _print_plan(plan_info)
    _ok(f"Plan saved to DB  (id={plan_id})")

    # 5. Sync (optional)
    if args.sync:
        _step(5, total, "Syncing to COROS calendar…")
        _warn(f"Will make {len(plan_info['workouts'])} API calls (one per workout).")
        _sync_to_coros(client, plan_info, username)
    else:
        print(); _info("Tip: run with --sync to push the plan to your COROS calendar.")

    _header("Done", width=68); print()


# ── cmd: checkin ──────────────────────────────────────────────────────────────

def cmd_checkin(args):
    profile = load_profile()
    profile_block = profile_to_prompt_block(profile)

    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine)

    # Optional: pull fresh COROS data first
    if args.sync:
        username = os.environ.get("COROS_USERNAME", "")
        password = os.environ.get("COROS_PASSWORD", "")
        if username and password:
            print(f"\n{B}Syncing COROS…{X}", flush=True)
            client = RealCorosAutomationClient()
            r = client.login(username, password)
            if r.ok:
                with Session(engine) as db:
                    athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one_or_none()
                    if athlete:
                        history = client.fetch_history(username, days_back=14)
                        stats = import_provider_history(db=db, athlete=athlete, provider="coros",
                                                        activities=history["activities"],
                                                        metrics=history["metrics"])
                        _ok(f"Synced {stats['imported_count']} new + {stats['updated_count']} updated")
            else:
                _warn(f"COROS sync failed: {r.message}")

    # Load plan + context from DB
    with Session(engine) as db:
        plan = get_latest_plan(db)
        if plan is None:
            _err("No training plan found. Run 'st_cli.py plan --goal 4:00 --weeks 8' first.")
            sys.exit(1)

        athlete = db.execute(select(AthleteProfile).limit(1)).scalar_one()
        upcoming = get_upcoming_workouts(db, plan.id, days=14)
        recent   = get_recent_activities(db, athlete.id, days=10)
        plan_title = plan.title or "Training Plan"

        # Current week
        if plan.start_date:
            days_in = (date.today() - plan.start_date).days
            current_week = max(1, min(plan.weeks, days_in // 7 + 1))
        else:
            current_week = 1

    # Print status header
    _header("Training Check-in", width=68)
    print(f"  {B}Plan   :{X} {plan_title}")
    print(f"  {B}Today  :{X} {date.today().strftime('%Y-%m-%d %A')}   (Week {current_week} of {plan.weeks})")

    if profile.name and profile.name != "Athlete":
        print(f"  {B}Athlete:{X} {profile.name}")

    print(f"\n  {B}Upcoming workouts (next 14 days):{X}")
    if upcoming:
        for w in upcoming:
            pm = w.get("pace_min") or "—"
            px = w.get("pace_max") or "—"
            print(f"    {D}{w['date']} ({w['day']}){X}  {w['title']:<20s}  {w['distance_km']} km  {D}[{pm}–{px}/km]{X}")
    else:
        print(f"    {D}No upcoming workouts in the next 14 days.{X}")

    print(f"\n  {B}Recent COROS activities (last 10 days):{X}")
    if recent:
        for a in recent:
            pace_str = f" @ {a['pace']}/km" if a.get("pace") else ""
            hr_str   = f"  HR {a['avg_hr']}" if a.get("avg_hr") else ""
            note_str = f"  [{a['notes']}]" if a.get("notes") else ""
            print(f"    {D}{a['date']} ({a['day']}){X}  {a['distance_km']} km{pace_str}{D}{hr_str}{note_str}{X}")
    else:
        print(f"    {D}No recent activities. Run 'st_cli.py checkin --sync' to pull latest data.{X}")

    _sep()
    print(f"  {D}Tell your coach how training is going. Type 'quit' to exit.{X}")
    print(f"  {D}用中文或英文都可以。输入 'quit' 退出。{X}\n")

    # ── Conversation loop ─────────────────────────────────────────────────────
    conversation_history: list[dict] = []

    while True:
        try:
            user_input = input(f"{B}You:{X} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break

        if user_input.lower() in ("quit", "exit", "q", "退出", "结束", "bye"):
            break
        if not user_input:
            continue

        # Get LLM response
        try:
            result = interpret_checkin(
                user_message=user_input,
                upcoming_workouts=upcoming,
                recent_activities=recent,
                profile_block=profile_block,
                conversation_history=conversation_history,
                plan_title=plan_title,
            )
        except Exception as exc:
            _err(f"Coach unavailable: {exc}")
            conversation_history.append({"role": "user", "content": user_input})
            continue

        # Show reply
        print(f"\n{G}Coach:{X} {result['reply']}\n")

        # Handle adjustments
        adjs = result.get("adjustments") or []
        adjs = [a for a in adjs if a.get("workout_id") or a.get("field") == "skip"]
        if adjs:
            print(f"  {B}Suggested adjustments:{X}")
            for adj in adjs:
                wid   = adj.get("workout_id", "?")
                field = adj.get("field", "")
                val   = adj.get("new_value", "")
                rsn   = adj.get("reason", "")
                d     = adj.get("date", "")
                if field == "distance_m" and isinstance(val, (int, float)):
                    val_str = f"{float(val)/1000:.1f} km"
                else:
                    val_str = str(val)
                print(f"  • [{d}] workout #{wid}: {field} → {val_str}  {D}({rsn}){X}")

            print()
            if result.get("needs_confirmation", True):
                try:
                    ans = input(f"  Apply these adjustments? [{G}Y{X}/n]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    ans = "n"

                if ans in ("", "y", "yes", "是", "好", "好的"):
                    with Session(engine) as db:
                        applied = apply_adjustments(db, adjs)
                    for a in applied:
                        _ok(a)
                    # Refresh upcoming after changes
                    with Session(engine) as db:
                        upcoming = get_upcoming_workouts(db, plan.id, days=14)
                    print()
                else:
                    _info("Adjustments skipped.")
            print()

        # Update conversation history (keep last 10 messages = 5 exchanges)
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": result["reply"]})
        if len(conversation_history) > 10:
            conversation_history = conversation_history[-10:]

    print(f"\n  {D}Session ended. Keep training! 💪{X}\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="st_cli.py",
        description="ST Marathon Training Planner — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Commands:
  setup     Build your athlete profile (one-time, ~2 minutes)
  plan      Pull COROS history and generate a marathon training plan
  checkin   Check-in chat to adapt the plan based on how training is going

Examples:
  uv run python scripts/st_cli.py setup
  uv run python scripts/st_cli.py plan --goal 4:00 --weeks 8
  uv run python scripts/st_cli.py checkin
  uv run python scripts/st_cli.py checkin --sync
""",
    )
    sub = parser.add_subparsers(dest="command")

    # ── setup ──
    sub.add_parser("setup", help="Build your athlete profile (one-time)")

    # ── plan ──
    pp = sub.add_parser("plan", help="Generate a marathon training plan")
    pp.add_argument("--goal", default="4:00", help="Marathon goal time H:MM  (default: 4:00)")
    pp.add_argument("--weeks", type=int, default=8, help="Training weeks  (default: 8)")
    pp.add_argument("--days-history", type=int, default=730, help="Days of COROS history  (default: 730)")
    pp.add_argument("--training-days", type=int, default=5, help="Training days/week  (default: 5)")
    pp.add_argument("--long-run-day", type=int, default=6, help="Long run weekday 0=Mon…6=Sun  (default: 6=Sun)")
    pp.add_argument("--sync", action="store_true", help="Push plan to COROS calendar")
    pp.add_argument("--athlete-name", default="Paul", help="Athlete name  (default: Paul)")

    # ── checkin ──
    cp = sub.add_parser("checkin", help="Check-in chat to adapt the current plan")
    cp.add_argument("--sync", action="store_true", help="Pull fresh COROS data before check-in")

    args = parser.parse_args()

    if args.command == "setup":
        cmd_setup(args)
    elif args.command == "plan":
        cmd_plan(args)
    elif args.command == "checkin":
        cmd_checkin(args)
    else:
        parser.print_help()
        print(f"\n  {D}Tip: start with 'st_cli.py setup' then 'st_cli.py plan'{X}\n")


if __name__ == "__main__":
    main()
