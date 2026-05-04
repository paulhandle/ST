# Fly.io Deployment + Brand/Scope Update

**Branch:** `feat/fly-deploy` (基于 `feat/block-d-nav-and-auth`，含 Block D/E + activities calendar 的最新工作)

**Fly org:** `performance-protocol`
**Domain:** `performanceprotocol.io` (web) + `api.performanceprotocol.io` (api), GoDaddy 管理

---

## 当前状态（2026-05-04 截止）

### ✅ 已完成

| 事项 | 状态 |
|---|---|
| 品牌文案重写（README / layout / pyproject） | 完成 |
| Postgres 依赖 + Alembic 迁移初始化 | 完成 |
| Dockerfile.api + web/Dockerfile | 完成 |
| fly/api.toml + fly/web.toml | 完成 |
| .github/workflows/ci.yml + deploy.yml | 完成 |
| Fly 基础设施创建（pp-db, st-api, pp-web） | 完成 |
| Postgres attach → st-api (DATABASE_URL auto-set) | 完成 |
| st-api secrets 配置（OPENAI / ST_SECRET_KEY / COROS） | 完成 |
| TLS certs 申请（3 个域名）| 完成 |
| IP 分配（st-api + pp-web 各 v4+v6）| 完成 |
| **st-api 首次部署：✅ HEALTHY** | 完成 |
| /api/healthz 路由修复（绕过 auth middleware） | 完成 |
| pp-web 新镜像重部署 | 完成并验收 |
| GoDaddy DNS 配置 | 完成并验收 |
| TLS certs 验收（3 个域名） | 完成 |
| Fly health checks 验收 | 完成 |
| 线上 HTTP 验收 | 完成 |
| 本地回归测试 | 完成 |
| PR 创建 | 完成：[#3](https://github.com/paulhandle/ST/pull/3) |
| PR CI | 完成：Backend + Frontend checks success |

### ❌ 下一步要做的

#### 1. PR 合并后检查 Actions

合并到 main 后，`.github/workflows/deploy.yml` 会部署 `st-api` 和 `pp-web`。需要确认 workflow 能读到 `FLY_API_TOKEN` 并完成。

---

## Review/Summary（2026-05-04）

用户完成 pp-web 新镜像部署和 GoDaddy DNS 配置后，已完成以下验收：

- `flyctl certs check api.performanceprotocol.io --app st-api`：Issued，verified and active
- `flyctl certs check performanceprotocol.io --app pp-web`：Issued，verified and active
- `flyctl certs check www.performanceprotocol.io --app pp-web`：Issued，verified and active
- `flyctl status --app st-api`：2 machines started，1/1 checks passing
- `flyctl status --app pp-web`：1 machine started，version 2，1/1 checks passing
- `curl -i https://api.performanceprotocol.io/`：HTTP 200，`{"service":"ST","status":"running"}`
- `curl -i https://performanceprotocol.io/`：HTTP 307，`location: /login`
- `curl -i https://www.performanceprotocol.io/`：HTTP 307，`location: /login`
- `curl -i https://performanceprotocol.io/api/healthz`：HTTP 200，`{"ok":true}`

本地回归：

- `uv run python -m unittest discover -s tests -v`：83/83 pass
- `cd web && pnpm test`：62/62 pass
- `cd web && pnpm type-check`：pass
- PR: https://github.com/paulhandle/ST/pull/3
- PR state: OPEN / MERGEABLE
- PR CI: Backend tests + Frontend tests/type-check all SUCCESS

---

## Fly 基础设施清单

| 资源 | 名称 | 状态 |
|---|---|---|
| Postgres cluster | `pp-db` | ✅ running (sin) |
| API app | `st-api` | ✅ healthy (2 machines, sin) |
| Web app | `pp-web` | ✅ healthy (version 2, /api/healthz passing) |
| API IPv4 | `149.248.210.173` | allocated |
| API IPv6 | `2a09:8280:1::110:e693:0` | allocated |
| Web IPv4 | `168.220.89.49` | allocated |
| Web IPv6 | `2a09:8280:1::110:e696:0` | allocated |
| TLS cert | `api.performanceprotocol.io` | ✅ issued / active |
| TLS cert | `performanceprotocol.io` | ✅ issued / active |
| TLS cert | `www.performanceprotocol.io` | ✅ issued / active |

## API secrets（st-api）

已配置（值不可见）：`DATABASE_URL` `OPENAI_API_KEY` `OPENAI_BASE_URL` `OPENAI_MODEL` `ST_SECRET_KEY` `COROS_AUTOMATION_MODE`

## 关键文件

| 文件 | 用途 |
|---|---|
| `fly/api.toml` | st-api fly 配置（sin, 256mb, release_command=alembic） |
| `fly/web.toml` | pp-web fly 配置（sin, 256mb, /api/healthz check） |
| `Dockerfile.api` | API 镜像（Python 3.11-slim, uv） |
| `web/Dockerfile` | Web 镜像（Next.js standalone, node:20-alpine） |
| `alembic/` | DB 迁移（首个 migration: 1ac50e58dbdb） |
| `.github/workflows/ci.yml` | PR CI（backend + frontend tests） |
| `.github/workflows/deploy.yml` | main push 自动部署 |
| `scripts/fly_setup.sh` | 一次性 setup 参考脚本 |
