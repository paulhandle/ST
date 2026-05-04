# PerformanceProtocol · 表现提升协议

> 站点：[performanceprotocol.io](https://performanceprotocol.io)
> 内部代号：`ST`（代码层包名仍沿用）

PerformanceProtocol 是一个面向严肃耐力运动员的训练表现提升平台。当前已上线**路跑（全马 / 半马）**完整闭环，规划中：**越野跑、铁人三项、长距离骑行**。

核心闭环（当前 COROS-first，多设备扩展中）：

1. 历史运动数据导入与能力评估（支持真实 COROS 直连 API）
2. 目标可行性判断（如全马 sub-4:00、半马 sub-1:45）
3. 结构化训练计划生成（LLM + 规则回退）
4. 用户确认后同步到 COROS 日历（`COROS_AUTOMATION_MODE=real` 启用真实 API 写入）
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

**后端**
- Python 3.11+、FastAPI、SQLAlchemy + SQLite
- httpx（FastAPI TestClient 测试依赖）
- Playwright（真实 COROS Training Hub 探测，可选）

**前端**（`web/`）
- Next.js 14 App Router + TypeScript + Tailwind CSS
- SWR（数据请求）、Recharts（图表）
- Vitest + React Testing Library（单元测试）
- 运行：`cd web && pnpm dev`（端口 3000，代理 API 到 8000）

## 快速启动

```bash
# 后端
cd /Users/paul/Work/ST
uv run uvicorn app.main:app --reload   # http://127.0.0.1:8000

# 前端（另开终端）
cd web
pnpm install
pnpm dev                               # http://localhost:3000
```

API 文档：`http://127.0.0.1:8000/docs`

## 本地 COROS 配置

复制 `.env.example` 为 `.env`，填入本地账号。`.env` 已被 `.gitignore` 忽略，不要把账号密码写进聊天或提交记录。

```bash
cp .env.example .env
```

关键变量：

- `ST_SECRET_KEY`：JWT 签名密钥（auth 系统使用）及本地凭据加密密钥
- `COROS_AUTOMATION_MODE=fake|real`：默认 `fake`（单元测试强制使用 fake）。设为 `real` 后 API 将使用 `RealCorosAutomationClient`，直接调用 `teamapi.coros.com` + `teamcnapi.coros.com` 完成 MD5 登录、活动分页拉取、日历写入，无需 Playwright
- `COROS_USERNAME` / `COROS_PASSWORD`：真实 COROS 账号密码，仅供本地探测脚本使用（API 层使用 `/coros/connect` 接口存储凭据）
- `COROS_TRAINING_HUB_URL`：默认 `https://training.coros.com`（探测脚本用）
- `COROS_HEADLESS=false`：Playwright 探测阶段建议保留可视浏览器
- `ST_DATABASE_URL`：数据库路径，默认 `sqlite:///st.db`；测试自动设为 `sqlite:///st_test.db` 以隔离生产数据

真实页面探测：

```bash
uv run python scripts/probe_coros_training_hub.py
```

如首次使用 Playwright 需要安装浏览器：

```bash
uv run playwright install chromium
```

探测结果会写入 `var/coros_probe/`，该目录已被忽略。

## Auth

所有 athlete/plan 路由均需要 Bearer token（后续逐步加保护，当前 auth 路由已完整）。

```bash
# 1. 获取 OTP（mock 模式直接返回 code）
curl -X POST http://127.0.0.1:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000"}'
# → {"message":"验证码已发送","otp_code":123456}

# 2. 验证 OTP，获取 JWT
curl -X POST http://127.0.0.1:8000/auth/send-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "13800138000", "code": "123456"}'
# → {"access_token":"...","token_type":"bearer","user_id":1}

# 3. 后续请求带上 token
curl http://127.0.0.1:8000/auth/me \
  -H "Authorization: Bearer <token>"
```

Token 有效期 30 天，无 refresh token。OTP 10 分钟过期，单次使用。

## Skills（训练方法论）

| slug | 描述 | 适用场景 |
|------|------|---------|
| `marathon_st_default` | ST 默认全马方法论，LLM + 规则混合 | 有一定训练基础的跑者 |
| `coach_zhao_unified` | 赵可统一马拉松法，季节自适应 | 按照该训练体系的跑者 |
| `running_beginner` | 入门跑者计划，纯规则 RPE 强度 | 零基础或周跑量 < 40 km |

加新 skill：在 `app/skills/<slug>/` 下放 `skill.md`、`spec.yaml`、`skill.py`（导出 `skill` 实例）。

## 前端页面

| 路径 | 说明 |
|------|------|
| `/login` | 手机 OTP 登录 |
| `/onboarding` | 新用户引导（COROS 连接 → 目标设定 → 训练日 → 确认） |
| `/dashboard` | 训练概览（今日、本周、目标、训练量、状态） |
| `/today` | 今日课程详情 + 标记完成 |
| `/week` | 本周训练日历 |
| `/plan` | 计划总览 + 待处理调整入口 |
| `/settings` | Skill 选择 |

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
- `POST /coros/connect`：连接 COROS 账号（`fake` 模式本地验证；`real` 模式直连 COROS API）
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
# 后端
uv run python -m py_compile $(find app -name "*.py")
uv run python -m unittest discover -s tests -v   # 71 tests

# 前端
cd web
pnpm test        # 35 tests
pnpm type-check

# Skill 注册器冒烟测试
uv run python -c "from app.skills import list_skills; print([m.slug for m in list_skills()])"
```

测试自动将 `ST_DATABASE_URL` 设为 `sqlite:///st_test.db`，与生产 `st.db` 隔离。

## 部署 (fly.io)

生产环境托管在 fly.io（Singapore region），数据库为 Fly Managed Postgres。

**架构：**
- `performanceprotocol.io` → fly app `st-web`（Next.js standalone）
- `api.performanceprotocol.io` → fly app `st-api`（FastAPI + uvicorn）
- Postgres 集群 `st-db`（attached 到 `st-api`，自动设置 `DATABASE_URL` secret）

**首次 setup（一次性，本地手动执行）：**

```bash
flyctl auth login
bash scripts/fly_setup.sh   # ← 不要直接跑！逐条手动执行，里面有需要替换的密钥
```

setup 完成后，DNS 记录按 `flyctl certs show` 的输出在 GoDaddy 配好，证书自动签发。

**日常部署：**

push 到 `main` 分支自动触发 `.github/workflows/deploy.yml`：
1. 跑后端 unittest + 前端 pnpm test + type-check
2. 全部通过后并行部署 `st-api` 和 `st-web`
3. `st-api` 部署时通过 `release_command` 自动跑 `alembic upgrade head`

非 main 分支只跑 `.github/workflows/ci.yml`（不部署）。

**所需 GitHub Secrets：**
- `FLY_API_TOKEN`：fly.io 后台生成的 PAT，scope 至少包含 deploy 权限

**所需 fly secrets（运行时密钥，由 `flyctl secrets set` 配置，不入库）：**
| Secret | App | 来源 |
|---|---|---|
| `DATABASE_URL` | st-api | `flyctl postgres attach` 自动写入 |
| `OPENAI_API_KEY` | st-api | OpenAI 控制台 |
| `ST_SECRET_KEY` | st-api | `openssl rand -hex 32` |
| `COROS_AUTOMATION_MODE` | st-api | `real` |

**回滚：**

```bash
flyctl releases --app st-api          # 看历史版本
flyctl releases rollback v123 --app st-api
```

**数据库迁移本地开发：**

```bash
# 改了 app/models.py 后生成 migration
DATABASE_URL=sqlite:///alembic_dev.db uv run alembic revision --autogenerate -m "your change"
rm alembic_dev.db   # 清理本地基准 DB
# Review 生成的 migration 文件，确认无误后提交
```
