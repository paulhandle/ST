from __future__ import annotations

import json
import logging
import os
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AthleteActivity, AthleteMetricSnapshot, StructuredWorkout, TrainingPlan

log = logging.getLogger(__name__)


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_latest_plan(db: Session) -> TrainingPlan | None:
    return db.execute(
        select(TrainingPlan).order_by(TrainingPlan.id.desc())
    ).scalars().first()


def get_upcoming_workouts(db: Session, plan_id: int, days: int = 14) -> list[dict]:
    today = date.today()
    cutoff = today + timedelta(days=days)
    rows = db.execute(
        select(StructuredWorkout)
        .where(StructuredWorkout.plan_id == plan_id)
        .where(StructuredWorkout.scheduled_date >= today)
        .where(StructuredWorkout.scheduled_date <= cutoff)
        .order_by(StructuredWorkout.scheduled_date)
    ).scalars().all()
    return [_workout_to_dict(w) for w in rows]


def get_recent_activities(db: Session, athlete_id: int, days: int = 10) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    rows = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.discipline == "run")
        .where(AthleteActivity.started_at >= since)
        .order_by(AthleteActivity.started_at.desc())
    ).scalars().all()
    return [_activity_to_dict(a) for a in rows]


def get_rich_training_context(db: Session, athlete_id: int) -> dict:
    """Pull LTHR, recent weekly volumes, and notable long runs for LLM context."""
    from collections import defaultdict

    now = datetime.now(UTC)

    # LTHR + LTSP
    lthr = _latest_metric(db, athlete_id, "lthr")
    ltsp = _latest_metric(db, athlete_id, "ltsp")

    # 8-week volumes
    activities = db.execute(
        select(AthleteActivity)
        .where(AthleteActivity.athlete_id == athlete_id)
        .where(AthleteActivity.discipline == "run")
        .where(AthleteActivity.started_at >= now - timedelta(days=56))
        .order_by(AthleteActivity.started_at.asc())
    ).scalars().all()

    by_week: dict[tuple, float] = defaultdict(float)
    for a in activities:
        by_week[a.started_at.isocalendar()[:2]] += a.distance_m / 1000

    weekly_km = [round(v, 1) for v in sorted(by_week.items(), key=lambda x: x[0])[-8:]]

    # Recent long runs (≥ 15 km)
    long_runs = [a for a in reversed(activities) if a.distance_m >= 15_000][:5]
    long_run_lines = []
    for a in reversed(long_runs):
        if not a.avg_pace_sec_per_km:
            continue
        pace = f"{int(a.avg_pace_sec_per_km//60)}:{int(a.avg_pace_sec_per_km%60):02d}"
        hr_str = f" avg HR {int(a.avg_hr)}" if a.avg_hr else ""
        long_run_lines.append(
            f"{a.started_at.strftime('%Y-%m-%d')}: {a.distance_m/1000:.1f} km @ {pace}/km{hr_str}"
        )

    return {
        "lthr": lthr,
        "ltsp": ltsp,
        "weekly_km_last_8w": weekly_km,
        "recent_long_runs": long_run_lines,
    }


def apply_adjustments(db: Session, adjustments: list[dict]) -> list[str]:
    """Write plan changes to DB. Returns human-readable descriptions of what changed."""
    applied: list[str] = []
    for adj in adjustments:
        wid = adj.get("workout_id")
        if not wid:
            continue
        workout = db.execute(
            select(StructuredWorkout).where(StructuredWorkout.id == int(wid))
        ).scalar_one_or_none()
        if not workout:
            log.warning("Adjustment references unknown workout_id=%s — skipped", wid)
            continue

        field = adj.get("field", "")
        new_val = adj.get("new_value")
        reason = adj.get("reason", "")
        d = workout.scheduled_date

        if field == "skip":
            old_title = workout.title
            workout.distance_m = 0
            workout.purpose = f"[SKIPPED] {workout.purpose or ''}"
            applied.append(f"⏭  {d} {old_title} → SKIPPED  ({reason})")

        elif field == "distance_m":
            old_km = workout.distance_m / 1000
            workout.distance_m = float(new_val)
            new_km = float(new_val) / 1000
            applied.append(f"📏  {d} {workout.workout_type}: {old_km:.1f}km → {new_km:.1f}km  ({reason})")

        elif field == "duration_min":
            old = workout.duration_min
            workout.duration_min = int(new_val)
            applied.append(f"⏱  {d} {workout.workout_type}: {old}min → {int(new_val)}min  ({reason})")

        elif field == "workout_type":
            old = workout.workout_type
            workout.workout_type = str(new_val)
            applied.append(f"🔄  {d}: {old} → {new_val}  ({reason})")

    if applied:
        db.commit()
    return applied


# ── LLM checkin ───────────────────────────────────────────────────────────────

def interpret_checkin(
    user_message: str,
    upcoming_workouts: list[dict],
    recent_activities: list[dict],
    profile_block: str,
    conversation_history: list[dict],
    plan_title: str = "",
) -> dict:
    """
    Send athlete check-in message to LLM. Returns:
    {
        "reply": str,
        "adjustments": list[dict],
        "needs_confirmation": bool,
    }
    """
    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL", "https://us.api.xianfeiglobal.com/v1"),
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    upcoming_str = "\n".join(
        f"  [id={w['id']}] {w['date']} ({w['day']}): {w['title']}  {w['distance_km']}km"
        + (f"  [{w['pace_min']}–{w['pace_max']}/km]" if w.get("pace_min") else "")
        for w in upcoming_workouts
    ) or "  (no upcoming workouts in the next 14 days)"

    recent_str = "\n".join(
        f"  {a['date']} ({a['day']}): {a['distance_km']}km"
        + (f" @ {a['pace']}/km" if a.get("pace") else "")
        + (f"  HR {a['avg_hr']}" if a.get("avg_hr") else "")
        + (f"  load {int(a['training_load'])}" if a.get("training_load") else "")
        + (f"  [{a['notes']}]" if a.get("notes") else "")
        for a in recent_activities
    ) or "  (no recent COROS activities synced)"

    system = f"""You are an expert running coach reviewing an athlete's training check-in.

CURRENT PLAN: {plan_title}

ATHLETE PROFILE:
{profile_block}

UPCOMING WORKOUTS (next 14 days, with workout IDs):
{upcoming_str}

RECENT COROS ACTIVITIES (last 10 days):
{recent_str}

YOUR ROLE:
1. Listen to what the athlete reports. Be conversational and empathetic.
2. Identify signals: fatigue, pain, missed sessions, overperformance, motivation issues.
3. Propose specific, actionable plan adjustments if the data warrants it.
4. Keep replies concise — 2–4 sentences of coaching, then the adjustment block.

LANGUAGE: Reply in the same language the athlete uses (Chinese or English).

FORMAT: After your coaching reply, append this block (always, even if empty):
<adjustments>
{{
  "adjustments": [
    {{
      "workout_id": <integer id from upcoming list, or null>,
      "date": "YYYY-MM-DD",
      "field": "distance_m|duration_min|workout_type|skip",
      "new_value": <number or string>,
      "reason": "one-line reason"
    }}
  ],
  "needs_confirmation": true
}}
</adjustments>

Use distance_m values (not km). If no changes needed, use empty adjustments list."""

    messages = [{"role": "system", "content": system}]
    messages.extend(conversation_history[-10:])  # keep last 5 exchanges
    messages.append({"role": "user", "content": user_message})

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.4,
        timeout=30,
    )
    full = resp.choices[0].message.content or ""

    # Extract adjustments JSON block
    adj_data: dict = {"adjustments": [], "needs_confirmation": False}
    if "<adjustments>" in full and "</adjustments>" in full:
        try:
            raw = full.split("<adjustments>")[1].split("</adjustments>")[0].strip()
            adj_data = json.loads(raw)
        except Exception as exc:
            log.warning("Failed to parse adjustments JSON: %s", exc)

    display_reply = full.split("<adjustments>")[0].strip()

    return {
        "reply": display_reply,
        "adjustments": adj_data.get("adjustments", []),
        "needs_confirmation": adj_data.get("needs_confirmation", True),
    }


# ── internal helpers ──────────────────────────────────────────────────────────

def _latest_metric(db: Session, athlete_id: int, metric_type: str) -> float | None:
    row = db.execute(
        select(AthleteMetricSnapshot)
        .where(AthleteMetricSnapshot.athlete_id == athlete_id)
        .where(AthleteMetricSnapshot.metric_type == metric_type)
        .order_by(AthleteMetricSnapshot.measured_at.desc())
    ).scalars().first()
    return float(row.value) if row else None


def _workout_to_dict(w: StructuredWorkout) -> dict:
    return {
        "id": w.id,
        "date": w.scheduled_date.strftime("%Y-%m-%d"),
        "day": w.scheduled_date.strftime("%a"),
        "workout_type": w.workout_type,
        "title": w.title,
        "distance_km": round(w.distance_m / 1000, 1),
        "duration_min": w.duration_min,
        "pace_min": _fmt_pace(w.target_pace_min_sec_per_km),
        "pace_max": _fmt_pace(w.target_pace_max_sec_per_km),
    }


def _activity_to_dict(a: AthleteActivity) -> dict:
    return {
        "date": a.started_at.strftime("%Y-%m-%d"),
        "day": a.started_at.strftime("%a"),
        "distance_km": round(a.distance_m / 1000, 1),
        "duration_min": a.duration_sec // 60,
        "pace": _fmt_pace(a.avg_pace_sec_per_km),
        "avg_hr": int(a.avg_hr) if a.avg_hr else None,
        "training_load": a.training_load,
        "notes": a.feedback_text or "",
    }


def _fmt_pace(sec: float | None) -> str | None:
    if sec is None:
        return None
    return f"{int(sec // 60)}:{int(sec % 60):02d}"
