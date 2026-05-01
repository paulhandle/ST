# ST - Athlete Training Planner

`ST` 是一个面向耐力运动员的训练任务规划后端 MVP，当前重点是 COROS-first 的全马训练闭环：

1. COROS 历史运动数据导入与能力评估
2. 全马目标可行性判断，例如 sub-4:00
3. 结构化全马训练计划生成
4. 用户确认后同步到 COROS 日历（当前为 fake COROS 自动化适配器）
5. 训练执行后的周度调整建议

旧版通用训练方法、Garmin/COROS mock 同步接口仍保留兼容。

## 架构

```
app/
├── core/        Platform: 数据契约 + 编排（SkillContext, orchestrator, adjustment, checkin, profile, config）
├── skills/      训练方法论（每个 skill 一个目录：skill.md + spec.yaml + skill.py + code/）
│   └── marathon_st_default/   ST 自带的全马 skill，作为 fallback
├── kb/          运动专项知识库（distance constants、running assessment 等）
├── tools/       平台拥有的外部集成
│   ├── coros/   COROS Training Hub 直 API client + sync
│   └── devices/ 兼容旧版 Garmin/COROS mock 适配器
├── ingestion/   历史活动 + 指标的统一写入
├── api/         FastAPI 路由
├── training/    旧版通用训练计划方法元数据 / 模式推荐
├── models.py    SQLAlchemy ORM
└── schemas.py   Pydantic schema
```

**核心原则**：

- **Skills 是纯函数**：吃 `SkillContext`，吐 `PlanDraft`；不碰 DB、不调外部 API
- **Tools 归平台**：所有外部集成（COROS、Garmin、Strava 等）由平台拥有；Skill 通过 SkillContext 拿数据
- **同周期一个 Skill**：训练科学约束，不允许同周期混用 skill；不同周期可切换
- **Skill 文件化**：每个 skill 一个目录，含 `skill.md`（人读说明）+ `spec.yaml`（机读规格）+ `skill.py`（实现）

加新 skill：

1. 在 `app/skills/<slug>/` 下放 `skill.md`、`spec.yaml`、`skill.py`
2. `skill.py` 必须导出 `skill` 实例，实现 `Skill` Protocol（`manifest`、`applicable(ctx)`、`generate_plan(ctx)`）
3. 用 `app.skills.load_skill("<slug>")` 加载，路由通过 orchestrator 调用即可

## 技术栈

- Python 3.11+
- FastAPI
- SQLAlchemy + SQLite
- httpx（FastAPI TestClient 测试依赖）
- Playwright（真实 COROS Training Hub 探测）

## 快速启动

```bash
cd /Users/paul/Work/ST
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

服务默认地址：`http://127.0.0.1:8000`

## 本地 COROS 配置

复制 `.env.example` 为 `.env`，填入本地账号。`.env` 已被 `.gitignore` 忽略，不要把账号密码写进聊天或提交记录。

```bash
cp .env.example .env
```

关键变量：

- `ST_SECRET_KEY`：本地凭据加密密钥
- `COROS_AUTOMATION_MODE=fake|real`：默认 `fake`
- `COROS_USERNAME` / `COROS_PASSWORD`：真实 COROS 账号密码，仅供本地探测使用
- `COROS_TRAINING_HUB_URL`：默认 `https://training.coros.com`
- `COROS_HEADLESS=false`：探测阶段建议保留可视浏览器

真实页面探测：

```bash
uv run python scripts/probe_coros_training_hub.py
```

如首次使用 Playwright 需要安装浏览器：

```bash
uv run playwright install chromium
```

探测结果会写入 `var/coros_probe/`，该目录已被忽略。

## 关键 API

- `GET /sports`：支持运动类型
- `GET /training/methods?sport=marathon`：按运动查看训练方法
- `GET /training/modes?sport=marathon&goal=improve_pace`：训练模式推荐
- `POST /athletes`：创建运动员画像
- `POST /plans/generate`：生成训练计划
- `GET /plans/{id}`：查看训练计划与课表
- `PATCH /plans/{id}/status`：更新计划状态
- `POST /devices/connect`：绑定 Garmin/COROS 账号
- `POST /plans/{id}/sync`：同步计划到设备（mock）
- `GET /sync-tasks?plan_id=1`：查看同步记录
- `POST /coros/connect`：连接 COROS 账号（MVP 为本地 fake 自动化）
- `POST /coros/import?athlete_id=1`：导入 COROS 历史数据
- `POST /athletes/{id}/assessment/run`：按目标重新计算路跑/全马能力评估
- `POST /marathon/plans/generate`：生成结构化全马计划
- `POST /plans/{id}/confirm`：确认计划并锁定待同步训练
- `POST /plans/{id}/sync/coros`：同步确认后的未来训练到 COROS 日历
- `POST /plans/{id}/adjustments/evaluate`：生成周度调整建议

## 示例流程

1) 创建运动员：

```bash
curl -X POST http://127.0.0.1:8000/athletes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Paul",
    "sport": "marathon",
    "level": "intermediate",
    "weekly_training_days": 5
  }'
```

2) COROS-first 全马闭环：

```bash
curl -X POST http://127.0.0.1:8000/coros/connect \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 1,
    "username": "paul@example.com",
    "password": "secret"
  }'

curl -X POST 'http://127.0.0.1:8000/coros/import?athlete_id=1' \
  -H "Content-Type: application/json" \
  -d '{"device_type": "coros"}'

curl -X POST 'http://127.0.0.1:8000/athletes/1/assessment/run?target_time_sec=14400&plan_weeks=16&weekly_training_days=5'

curl -X POST http://127.0.0.1:8000/marathon/plans/generate \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 1,
    "target_time_sec": 14400,
    "plan_weeks": 16,
    "availability": {
      "weekly_training_days": 5,
      "preferred_long_run_weekday": 6,
      "unavailable_weekdays": [0],
      "max_weekday_duration_min": 90,
      "max_weekend_duration_min": 210,
      "strength_training_enabled": true
    }
  }'

curl -X POST http://127.0.0.1:8000/plans/1/confirm
curl -X POST http://127.0.0.1:8000/plans/1/sync/coros
curl -X POST http://127.0.0.1:8000/plans/1/adjustments/evaluate
```

3) 旧版通用计划生成：

```bash
curl -X POST http://127.0.0.1:8000/plans/generate \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 1,
    "goal": "improve_pace",
    "weeks": 12
  }'
```

4) 旧版设备绑定并同步：

```bash
curl -X POST http://127.0.0.1:8000/devices/connect \
  -H "Content-Type: application/json" \
  -d '{
    "athlete_id": 1,
    "device_type": "garmin",
    "external_user_id": "garmin_user_001"
  }'

curl -X POST http://127.0.0.1:8000/plans/1/sync \
  -H "Content-Type: application/json" \
  -d '{
    "device_type": "garmin"
  }'
```

## 后续可扩展方向

- 接入真实 COROS Training Hub 浏览器自动化选择器与会话管理
- 接入真实 Garmin / COROS OAuth 与官方 API
- 引入伤病风险评估、疲劳模型（HRV/TSS/CTL）
- 增加 Web/移动端可视化训练日历与训练完成回写

## 验证

```bash
uv run python -m py_compile $(find app -name "*.py")
uv run python -m unittest discover -s tests -v

# Skill 注册器冒烟测试
uv run python -c "from app.skills import list_skills; print([m.slug for m in list_skills()])"
```
