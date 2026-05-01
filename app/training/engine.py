from app.models import SportType, TrainingGoal, TrainingMode


def generate_plan_sessions(
    sport: SportType, mode: TrainingMode, goal: TrainingGoal, weeks: int, weekly_days: int
) -> list[dict]:
    weekly_days = min(max(weekly_days, 2), 7)
    all_sessions: list[dict] = []

    for week in range(1, weeks + 1):
        phase = _week_phase(week, weeks)
        if sport == SportType.MARATHON:
            week_sessions = _marathon_template(phase=phase, mode=mode, weekly_days=weekly_days)
        elif sport == SportType.TRAIL_RUNNING:
            week_sessions = _trail_template(phase=phase, mode=mode, weekly_days=weekly_days)
        else:
            week_sessions = _triathlon_template(phase=phase, mode=mode, weekly_days=weekly_days)

        for day_index, session in enumerate(week_sessions, start=1):
            all_sessions.append(
                {
                    "week_index": week,
                    "day_index": day_index,
                    "discipline": session["discipline"],
                    "session_type": session["session_type"],
                    "duration_min": session["duration_min"],
                    "intensity": session["intensity"],
                    "notes": f"{phase}阶段，目标={goal.value}",
                }
            )

    return all_sessions


def _week_phase(week: int, total_weeks: int) -> str:
    progress = week / total_weeks
    if progress <= 0.5:
        return "base"
    if progress <= 0.85:
        return "build"
    return "taper"


def _quality_type(mode: TrainingMode) -> str:
    if mode == TrainingMode.POLARIZED:
        return "VO2 间歇"
    if mode == TrainingMode.THRESHOLD_FOCUSED:
        return "乳酸阈值跑"
    return "节奏跑"


def _duration_for_long_session(phase: str, base: int = 90) -> int:
    if phase == "base":
        return base
    if phase == "build":
        return base + 30
    return max(base - 20, 50)


def _select_sessions(sessions: list[dict], weekly_days: int, priority_order: list[int]) -> list[dict]:
    if weekly_days >= len(sessions):
        return sessions

    picked = priority_order[:weekly_days]
    return [sessions[i] for i in picked]


def _marathon_template(phase: str, mode: TrainingMode, weekly_days: int) -> list[dict]:
    sessions = [
        {"discipline": "run", "session_type": "轻松跑", "duration_min": 45, "intensity": "low"},
        {"discipline": "run", "session_type": _quality_type(mode), "duration_min": 60, "intensity": "high"},
        {"discipline": "strength", "session_type": "核心与稳定性", "duration_min": 30, "intensity": "low"},
        {"discipline": "run", "session_type": "稳态跑", "duration_min": 55, "intensity": "moderate"},
        {"discipline": "rest", "session_type": "主动恢复", "duration_min": 20, "intensity": "very_low"},
        {
            "discipline": "run",
            "session_type": "长距离跑",
            "duration_min": _duration_for_long_session(phase, 100),
            "intensity": "moderate",
        },
        {"discipline": "run", "session_type": "恢复慢跑", "duration_min": 35, "intensity": "very_low"},
    ]
    priority = [5, 1, 0, 3, 2, 6, 4]
    return _select_sessions(sessions, weekly_days, priority)


def _trail_template(phase: str, mode: TrainingMode, weekly_days: int) -> list[dict]:
    quality = "爬升重复" if mode != TrainingMode.THRESHOLD_FOCUSED else "越野阈值坡跑"
    sessions = [
        {"discipline": "run", "session_type": "技术越野轻松跑", "duration_min": 50, "intensity": "low"},
        {"discipline": "run", "session_type": quality, "duration_min": 65, "intensity": "high"},
        {"discipline": "strength", "session_type": "下肢力量+离心训练", "duration_min": 35, "intensity": "moderate"},
        {"discipline": "run", "session_type": "下坡技术训练", "duration_min": 55, "intensity": "moderate"},
        {
            "discipline": "run",
            "session_type": "越野长距离",
            "duration_min": _duration_for_long_session(phase, 110),
            "intensity": "moderate",
        },
        {
            "discipline": "run",
            "session_type": "背靠背中长距离",
            "duration_min": _duration_for_long_session(phase, 80),
            "intensity": "moderate",
        },
        {"discipline": "rest", "session_type": "恢复与拉伸", "duration_min": 25, "intensity": "very_low"},
    ]
    priority = [4, 1, 5, 0, 3, 2, 6]
    return _select_sessions(sessions, weekly_days, priority)


def _triathlon_template(phase: str, mode: TrainingMode, weekly_days: int) -> list[dict]:
    bike_quality = "FTP 阈值骑行" if mode == TrainingMode.THRESHOLD_FOCUSED else "高踏频间歇骑行"
    run_quality = "节奏跑" if mode != TrainingMode.POLARIZED else "短间歇跑"
    sessions = [
        {"discipline": "swim", "session_type": "技术泳+配速组", "duration_min": 60, "intensity": "moderate"},
        {"discipline": "bike", "session_type": bike_quality, "duration_min": 75, "intensity": "high"},
        {"discipline": "run", "session_type": run_quality, "duration_min": 50, "intensity": "moderate"},
        {"discipline": "brick", "session_type": "骑跑衔接训练", "duration_min": 80, "intensity": "high"},
        {
            "discipline": "bike",
            "session_type": "长距离骑行",
            "duration_min": _duration_for_long_session(phase, 120),
            "intensity": "moderate",
        },
        {
            "discipline": "run",
            "session_type": "长距离跑",
            "duration_min": _duration_for_long_session(phase, 85),
            "intensity": "moderate",
        },
        {"discipline": "rest", "session_type": "恢复游/拉伸", "duration_min": 30, "intensity": "very_low"},
    ]
    priority = [4, 3, 1, 0, 5, 2, 6]
    return _select_sessions(sessions, weekly_days, priority)
