from app.models import SportType, TrainingGoal, TrainingMode

TRAINING_METHOD_DEFINITIONS = [
    {
        "sport": SportType.MARATHON,
        "name": "LSD 长距离慢跑",
        "summary": "以低强度长时间跑建立有氧基础和肌耐力，是马拉松训练核心。",
        "focus": "有氧耐力",
        "default_mode": TrainingMode.BASE_BUILD_PEAK,
    },
    {
        "sport": SportType.MARATHON,
        "name": "阈值跑（Tempo）",
        "summary": "接近乳酸阈值强度持续跑，提升配速维持能力。",
        "focus": "配速耐受",
        "default_mode": TrainingMode.PYRAMIDAL,
    },
    {
        "sport": SportType.MARATHON,
        "name": "间歇跑（VO2max）",
        "summary": "短间歇高强度重复，提升最大摄氧与速度上限。",
        "focus": "速度能力",
        "default_mode": TrainingMode.POLARIZED,
    },
    {
        "sport": SportType.TRAIL_RUNNING,
        "name": "爬升重复训练",
        "summary": "在坡道反复上坡跑，强化爬升能力与心肺。",
        "focus": "爬升能力",
        "default_mode": TrainingMode.POLARIZED,
    },
    {
        "sport": SportType.TRAIL_RUNNING,
        "name": "背靠背长距离",
        "summary": "连续两天中长距离，模拟越野后程疲劳状态。",
        "focus": "持续耐力",
        "default_mode": TrainingMode.BASE_BUILD_PEAK,
    },
    {
        "sport": SportType.TRAIL_RUNNING,
        "name": "下坡技术训练",
        "summary": "强化技术下坡中的步频、落点与离心能力。",
        "focus": "技术与抗冲击",
        "default_mode": TrainingMode.PYRAMIDAL,
    },
    {
        "sport": SportType.TRIATHLON,
        "name": "分项基础耐力",
        "summary": "游泳/骑行/跑步分别构建基础耐力，强调均衡发展。",
        "focus": "三项基础",
        "default_mode": TrainingMode.BASE_BUILD_PEAK,
    },
    {
        "sport": SportType.TRIATHLON,
        "name": "Brick 骑跑衔接",
        "summary": "骑行后立即跑步，提升项目转换适应能力。",
        "focus": "转项能力",
        "default_mode": TrainingMode.PYRAMIDAL,
    },
    {
        "sport": SportType.TRIATHLON,
        "name": "阈值骑行与配速泳",
        "summary": "围绕 FTP 与配速泳的中高强度训练，提升比赛速度。",
        "focus": "比赛速度",
        "default_mode": TrainingMode.THRESHOLD_FOCUSED,
    },
]

MODE_DESCRIPTIONS = {
    TrainingMode.POLARIZED: "80% 低强度 + 20% 高强度，强调恢复与关键高强度刺激。",
    TrainingMode.PYRAMIDAL: "低强度占比最高，中强度次之，高强度最少，适合稳步进阶。",
    TrainingMode.THRESHOLD_FOCUSED: "提升阈值能力，适合有一定基础且目标偏成绩提升的运动员。",
    TrainingMode.BASE_BUILD_PEAK: "基础期-强化期-峰值期周期化推进，适合完整备赛流程。",
}

MODE_GOAL_MATRIX = {
    TrainingGoal.FINISH: [TrainingMode.BASE_BUILD_PEAK, TrainingMode.PYRAMIDAL],
    TrainingGoal.IMPROVE_PACE: [TrainingMode.THRESHOLD_FOCUSED, TrainingMode.POLARIZED, TrainingMode.PYRAMIDAL],
    TrainingGoal.INCREASE_ENDURANCE: [TrainingMode.BASE_BUILD_PEAK, TrainingMode.POLARIZED],
    TrainingGoal.RACE_SPECIFIC: [TrainingMode.PYRAMIDAL, TrainingMode.THRESHOLD_FOCUSED, TrainingMode.BASE_BUILD_PEAK],
}


def recommend_modes(sport: SportType, goal: TrainingGoal) -> list[dict]:
    modes = MODE_GOAL_MATRIX.get(goal, [TrainingMode.PYRAMIDAL])

    if sport == SportType.TRAIL_RUNNING and TrainingMode.POLARIZED not in modes:
        modes = [TrainingMode.POLARIZED, *modes]

    return [
        {
            "mode": mode,
            "description": MODE_DESCRIPTIONS[mode],
            "suitable_goals": [goal],
            "rationale": f"针对 {sport.value} 的 {goal.value} 目标推荐此模式。",
        }
        for mode in modes
    ]
