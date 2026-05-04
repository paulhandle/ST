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
| /api/healthz 路由修复（绕过 auth middleware） | 完成（待重部署生效） |

### ❌ 下一步要做的

#### 1. 重新部署 pp-web（最优先）

当前 pp-web 运行的是旧镜像（无 /api/healthz），health check critical。
修复已提交到 `feat/fly-deploy`，需要跑：

```bash
cd /Users/paul/Work/ST/web
flyctl deploy --config ../fly/web.toml --dockerfile Dockerfile \
  --build-arg BACKEND_URL=https://api.performanceprotocol.io --remote-only
```

#### 2. GoDaddy DNS 配置

需要在 GoDaddy DNS Management 添加以下记录：

| 类型 | 主机名 | 值 |
|---|---|---|
| A | `@` | `168.220.89.49` |
| AAAA | `@` | `2a09:8280:1::110:e696:0` |
| A | `api` | `149.248.210.173` |
| AAAA | `api` | `2a09:8280:1::110:e693:0` |
| CNAME | `www` | `pp-web.fly.dev` |

DNS 生效后证书自动签发（可用 `flyctl certs check performanceprotocol.io --app pp-web` 检查）

#### 3. 验收检查

DNS 传播 + 证书签发后（通常 5-30 分钟）：

```bash
# API
curl https://api.performanceprotocol.io/
# → {"service":"ST","status":"running"}

curl https://api.performanceprotocol.io/docs
# → Swagger UI

# Web
curl -I https://performanceprotocol.io/
# → HTTP/2 302 (redirect to /login)

# Health checks（应该 passing）
flyctl status --app st-api
flyctl status --app pp-web
```

#### 4. 合并到 main / PR

部署验收通过后：
- 确认 GitHub Secrets 里有 `FLY_API_TOKEN`
- 创建 PR: `feat/fly-deploy` → `main`
- PR merge 后，后续所有 push to main 自动通过 GitHub Actions 部署

---

## Fly 基础设施清单

| 资源 | 名称 | 状态 |
|---|---|---|
| Postgres cluster | `pp-db` | ✅ running (sin) |
| API app | `st-api` | ✅ healthy (2 machines, sin) |
| Web app | `pp-web` | ⚠️ critical health check (旧镜像，需重部署) |
| API IPv4 | `149.248.210.173` | allocated |
| API IPv6 | `2a09:8280:1::110:e693:0` | allocated |
| Web IPv4 | `168.220.89.49` | allocated |
| Web IPv6 | `2a09:8280:1::110:e696:0` | allocated |
| TLS cert | `api.performanceprotocol.io` | pending DNS |
| TLS cert | `performanceprotocol.io` | pending DNS |
| TLS cert | `www.performanceprotocol.io` | pending DNS |

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
