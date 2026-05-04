#!/usr/bin/env bash
# PerformanceProtocol — one-time fly.io setup
# Run these commands MANUALLY, line by line. DO NOT execute the whole script
# unattended — each step has side effects on real fly.io infrastructure.
#
# Prerequisites:
#   1. Install flyctl:  curl -L https://fly.io/install.sh | sh
#   2. Sign in:         flyctl auth login
#   3. Domain DNS access on GoDaddy for performanceprotocol.io
#
# After completing all steps, push to main on GitHub will auto-deploy via
# .github/workflows/deploy.yml (using FLY_API_TOKEN from repo secrets).

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────
# Variables
# ──────────────────────────────────────────────────────────────────────
FLY_ORG="performance-protocol"
REGION="sin"                              # Singapore
API_APP="st-api"
WEB_APP="st-web"
DB_APP="st-db"
DOMAIN_API="api.performanceprotocol.io"
DOMAIN_WEB="performanceprotocol.io"
DOMAIN_WWW="www.performanceprotocol.io"

# ──────────────────────────────────────────────────────────────────────
# Step 1 — Create Postgres cluster (1 node, 256MB, 1GB volume)
# ──────────────────────────────────────────────────────────────────────
flyctl postgres create \
  --name "$DB_APP" \
  --org "$FLY_ORG" \
  --region "$REGION" \
  --vm-size shared-cpu-1x \
  --volume-size 1 \
  --initial-cluster-size 1
# Note the connection string from output — DO NOT need to save it,
# `flyctl postgres attach` (step 3) will set DATABASE_URL automatically.

# ──────────────────────────────────────────────────────────────────────
# Step 2 — Create empty API app (no deploy yet)
# ──────────────────────────────────────────────────────────────────────
flyctl apps create "$API_APP" --org "$FLY_ORG"

# ──────────────────────────────────────────────────────────────────────
# Step 3 — Attach Postgres → API app
# This sets DATABASE_URL secret automatically.
# ──────────────────────────────────────────────────────────────────────
flyctl postgres attach "$DB_APP" --app "$API_APP"

# ──────────────────────────────────────────────────────────────────────
# Step 4 — Set API secrets (NEVER commit these values)
# ──────────────────────────────────────────────────────────────────────
# Replace placeholders with real values from your password manager.
flyctl secrets set --app "$API_APP" \
  OPENAI_API_KEY="REPLACE_ME" \
  ST_SECRET_KEY="$(openssl rand -hex 32)" \
  COROS_AUTOMATION_MODE="real"

# ──────────────────────────────────────────────────────────────────────
# Step 5 — Create empty WEB app
# ──────────────────────────────────────────────────────────────────────
flyctl apps create "$WEB_APP" --org "$FLY_ORG"

# ──────────────────────────────────────────────────────────────────────
# Step 6 — Issue TLS certs (will be issued once DNS is in place)
# ──────────────────────────────────────────────────────────────────────
flyctl certs add "$DOMAIN_API"  --app "$API_APP"
flyctl certs add "$DOMAIN_WEB"  --app "$WEB_APP"
flyctl certs add "$DOMAIN_WWW"  --app "$WEB_APP"

# ──────────────────────────────────────────────────────────────────────
# Step 7 — Show DNS records to add at GoDaddy
# ──────────────────────────────────────────────────────────────────────
echo "── api.performanceprotocol.io ──"
flyctl certs show "$DOMAIN_API" --app "$API_APP"
echo "── performanceprotocol.io ──"
flyctl certs show "$DOMAIN_WEB" --app "$WEB_APP"
echo "── www.performanceprotocol.io ──"
flyctl certs show "$DOMAIN_WWW" --app "$WEB_APP"

# At GoDaddy DNS Management, add the records flyctl prints above.
# Typically:
#   - A record  @  → fly.io IPv4   (apex domain)
#   - AAAA      @  → fly.io IPv6
#   - A record  api  → same IPv4 (or use CNAME to st-api.fly.dev — but A is faster)
#   - AAAA      api  → IPv6
#   - CNAME     www  → performanceprotocol.io
#
# Cert provisioning takes 1–10 min after DNS resolves.
# Verify:  flyctl certs show <domain> --app <app>

# ──────────────────────────────────────────────────────────────────────
# Step 8 — First deploy (or push to main and let GitHub Actions do it)
# ──────────────────────────────────────────────────────────────────────
# Manual first deploy (recommended for the first time):
#   flyctl deploy --config fly/api.toml --dockerfile Dockerfile.api --remote-only
#   cd web && flyctl deploy --config ../fly/web.toml --dockerfile Dockerfile \
#     --build-arg BACKEND_URL=https://api.performanceprotocol.io --remote-only
#
# After that, just push to main on GitHub → workflow handles deploys.
