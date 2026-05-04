# Fly.io Deployment + Brand/Scope Update

**Branch:** `feat/fly-deploy` (基于 `feat/block-d-nav-and-auth`，含 Block D/E + activities calendar 的最新工作)

**Goal:** 把 ST 部署到 fly.io（Singapore 区，最小资源），用 Postgres 替换生产 DB，配 GitHub Actions CI/CD（push to main 触发 deploy）。同时调整用户可见品牌为 PerformanceProtocol，定位从"马拉松"扩到"严肃耐力训练"。

**Fly org:** `performance-protocol`
**Domain:** `performanceprotocol.io` (web) + `api.performanceprotocol.io` (api), 在 GoDaddy 管理

---

## Phase 0 — 用户可见品牌文案 (零风险)

- [ ] 重写 `README.md`：替换"马拉松"为"严肃耐力训练（当前 路跑全马/半马；规划中 越野跑、铁三）"，顶部加 PerformanceProtocol 标题。代码内部命名保持 `st`/`st-web`。
- [ ] `web/app/layout.tsx`：title 改为 `PerformanceProtocol · 表现提升协议`，description 改为多运动定位
- [ ] `pyproject.toml`：description 改为 "PerformanceProtocol — Endurance training planner"
- [ ] 跑测试确认无回归：`uv run python -m unittest discover -s tests` + `cd web && pnpm test`
- [ ] Commit: `docs: rebrand to PerformanceProtocol, broaden scope to endurance`

---

## Phase 1 — DB 迁移 Postgres-ready (本地仍 SQLite)

- [ ] 加依赖到 `pyproject.toml`：`psycopg[binary]>=3.1` + `alembic>=1.13`
- [ ] 改 `app/db.py`：
  - 读 `os.environ.get("DATABASE_URL")` 优先，否则 fall back 到 `ST_DATABASE_URL`，再 fall back 到 `sqlite:///st.db`
  - Postgres URL 自动转换 `postgres://` → `postgresql+psycopg://`
- [ ] `uv run alembic init alembic`
- [ ] `alembic/env.py`：从 `app.models.Base.metadata` 读 metadata；从 `DATABASE_URL` 读连接串
- [ ] `uv run alembic revision --autogenerate -m "initial schema"` — 生成首个 migration
- [ ] 本地测试：在临时 Postgres 容器跑一次 migration 验证（或先跳过，让 fly 部署时自动跑）
- [ ] 跑全套后端测试，确保 SQLite 路径仍 OK：`uv run python -m unittest discover -s tests`
- [ ] Commit: `feat(db): add Postgres support via alembic, env-driven DATABASE_URL`

---

## Phase 2 — Dockerfile + Fly 配置

- [ ] `Dockerfile.api`（多阶段，Python 3.11-slim，uv 装依赖，最终 image < 400MB）
- [ ] `.dockerignore` 在根 repo（排除 `.venv/`, `node_modules/`, `*.db`, `web/`, `.git/`, `var/`, `tests/`, `docs/`）
- [ ] `web/Dockerfile`（Next.js standalone 构建：node 20-alpine，最终 image < 200MB）
- [ ] `web/.dockerignore`
- [ ] 改 `web/next.config.js`：加 `output: 'standalone'`
- [ ] `fly/api.toml`：app name `st-api`，region `sin`，`shared-cpu-1x@256mb`，internal port 8000，HTTP service，release_command 跑 alembic upgrade
- [ ] `fly/web.toml`：app name `st-web`，region `sin`，`shared-cpu-1x@256mb`，internal port 3000，HTTP service，环境变量 `NEXT_PUBLIC_API_URL=https://api.performanceprotocol.io`
- [ ] 本地构建验证：`docker build -f Dockerfile.api -t st-api:test .` + 跑起来确认 healthcheck OK
- [ ] Commit: `feat(deploy): add Dockerfiles and fly.toml for st-api/st-web`

---

## Phase 3 — GitHub Actions

- [ ] `.github/workflows/ci.yml`：
  - 触发：`pull_request` + `push` 到任意分支
  - Job 1 backend: setup uv, run pytest
  - Job 2 frontend: setup pnpm, run `pnpm test` + `pnpm type-check`
- [ ] `.github/workflows/deploy.yml`：
  - 触发：`push` to `main` only
  - 依赖 ci.yml 通过（用 `workflow_run` 或者直接在 deploy 里再跑测试，二选一 — 推荐后者更可靠）
  - Job 1: deploy api — `flyctl deploy --config fly/api.toml`
  - Job 2: deploy web — `flyctl deploy --config fly/web.toml --build-arg NEXT_PUBLIC_API_URL=https://api.performanceprotocol.io`
  - 用 secret `FLY_API_TOKEN`
- [ ] README 加部署文档段落：env 变量列表、首次部署 setup 步骤、回滚命令
- [ ] Commit: `ci: add CI workflow + main-branch deploy to fly.io`

---

## Phase 4 — 一次性手工 setup (你执行，我提供命令清单)

我会在 `scripts/fly_setup.sh` 写好命令清单（带注释，你逐条手动执行而非自动跑，避免误触）：

```bash
# 0. 登录 + 选 org
flyctl auth login
export FLY_ORG=performance-protocol

# 1. 创建 Postgres
flyctl postgres create \
  --name st-db --org $FLY_ORG --region sin \
  --vm-size shared-cpu-1x --volume-size 1 --initial-cluster-size 1
# 记下输出的 connection string

# 2. 创建 api app（不部署，先创建空壳）
flyctl apps create st-api --org $FLY_ORG

# 3. 关联 Postgres → api app（自动设置 DATABASE_URL secret）
flyctl postgres attach st-db --app st-api

# 4. 设置 api 其他 secrets
flyctl secrets set --app st-api \
  OPENAI_API_KEY=sk-... \
  JWT_SECRET=$(openssl rand -hex 32) \
  COROS_AUTOMATION_MODE=real

# 5. 创建 web app
flyctl apps create st-web --org $FLY_ORG

# 6. 配域名 + 证书
flyctl certs add api.performanceprotocol.io --app st-api
flyctl certs add performanceprotocol.io --app st-web
flyctl certs add www.performanceprotocol.io --app st-web

# 7. 看 DNS 指引（GoDaddy 配 A/AAAA）
flyctl certs show api.performanceprotocol.io --app st-api
flyctl certs show performanceprotocol.io --app st-web
```

GoDaddy DNS 配置（手动）：
- `api.performanceprotocol.io` A → fly 给的 IPv4，AAAA → IPv6
- `performanceprotocol.io` A/AAAA 同理（或用 ALIAS / CNAME flattening）
- `www.performanceprotocol.io` CNAME → `performanceprotocol.io`

**注意**：先别 merge feat/fly-deploy 到 main！等你完成上面 1-7 步（apps + Postgres + secrets + DNS），再 merge PR，第一次自动部署才会成功。

---

## 验收标准

- [ ] `https://performanceprotocol.io` 加载 Next.js 前端
- [ ] `https://api.performanceprotocol.io/docs` 显示 FastAPI Swagger
- [ ] 前端能调通后端（登录 / 历史活动 / 计划生成）
- [ ] push 任意 commit 到 main 触发自动 deploy
- [ ] PR 不部署，但跑 CI
- [ ] 所有现有测试在本地仍 pass

## 风险点 / 已知 issue

1. **首次部署前不能 merge 到 main**，否则 deploy.yml 会跑但目标 app 不存在 → 失败。先做 Phase 4 setup。
2. **SQLite → Postgres 迁移**：本次部署是 greenfield 生产，不迁数据，prod 从空 DB 开始。
3. **COROS 凭据**：用户在前端填的，存到 prod DB 的 `device_account` 表（已加密？需要确认）。
4. **next.js standalone build** 在 monorepo 里有时会漏文件，本地 docker 跑通是关键验证步骤。
5. **alembic autogenerate** 偶尔漏掉 enum 类型变更，第一版迁移要人肉 review。

## Review/Summary

**Status:** Code complete on `feat/fly-deploy` branch (4 commits). User-side setup pending.

**What's done:**
- Phase 0 — Brand text rebranded to PerformanceProtocol (README, layout.tsx, pyproject.toml). Internal codename `st` preserved.
- Phase 1 — Postgres-ready: `psycopg[binary]` + `alembic`, env-driven `DATABASE_URL` (auto-translates `postgres://` → `postgresql+psycopg://`), initial migration `1ac50e58dbdb` captured full current schema.
- Phase 2 — `Dockerfile.api` (Python 3.11 + uv), `web/Dockerfile` (Next.js standalone, node:20-alpine), `fly/api.toml` + `fly/web.toml` (sin region, shared-cpu-1x@256mb), `next.config.js` updated for standalone output + BACKEND_URL-driven rewrite.
- Phase 3 — `.github/workflows/ci.yml` (PR + non-main pushes) and `deploy.yml` (push to main, gated by tests, parallel deploy of api+web).
- Phase 4 — `scripts/fly_setup.sh` annotated checklist; README deploy section with architecture, secrets, rollback, migration workflow.

**Tests:** 83 backend + 62 frontend all green; type-check clean.

**What user needs to do before merging to main:**
1. Add `FLY_API_TOKEN` to GitHub repo secrets (Settings → Secrets and variables → Actions)
2. Run `scripts/fly_setup.sh` step-by-step locally to create st-api / st-web / st-db apps and attach Postgres
3. Set `OPENAI_API_KEY` + `ST_SECRET_KEY` + `COROS_AUTOMATION_MODE=real` via `flyctl secrets set --app st-api`
4. Add DNS records at GoDaddy per `flyctl certs show` output
5. Once certs go GREEN: open PR → merge to main → first auto-deploy fires

**Known limitations:**
- Single Postgres node (no HA) — fine for MVP, scale up later via `flyctl postgres update`
- No staging env — main deploys directly to prod
- `app/main.py` still calls `Base.metadata.create_all` at startup; harmless because it's idempotent and runs after `alembic upgrade head` (release_command). Long term, remove it.
