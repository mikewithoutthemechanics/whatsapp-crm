#!/usr/bin/env bash
# whatsapp-crm — automated deploy script
# Supports: Railway · Render · Docker · local
#
# Usage:
#   ./deploy.sh railway      # deploy to Railway (requires railway CLI)
#   ./deploy.sh render       # deploy to Render  (requires render CLI or git push)
#   ./deploy.sh docker       # build + run locally via docker compose
#   ./deploy.sh setup        # interactive first-time setup
#   ./deploy.sh check        # run health checks against a running instance
#   ./deploy.sh status       # show current config + services
#
# Railway CLI:  npm i -g @railway/cli && railway login
# Render CLI:   npm i -g @render-cli && render login

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

WHITE='\033[97m'
GREEN='\033[92m'
YELLOW='\033[93m'
CYAN='\033[96m'
BOLD='\033[1m'
RESET='\033[0m'

ok()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()  { echo -e "${YELLOW}⚠${RESET} $*"; }
info()  { echo -e "${CYAN}ℹ${RESET} $*"; }
step()  { echo -e "${BOLD}${WHITE}▸ $*${RESET}"; }

# ── HELP ────────────────────────────────────────────────────────────────

if [ $# -lt 1 ]; then
  cat <<"USAGE"
WhatsApp CRM SA — Deploy Script

  ./deploy.sh <command> [options]

Commands:
  setup           Interactive first-time setup (creates .env, checks deps)
  check           Run health checks against a running instance
  status          Show current config and service status
  docker          Start full stack with docker compose (CRM + OpenWA + Postgres)
  railway         Deploy to Railway
  render          Push to Render (via git)
  openwa          Print OpenWA-specific Docker up command

Examples:
  ./deploy.sh setup         # guided first run
  ./deploy.sh docker        # one-command local stack
  ./deploy.sh railway       # push to Railway
USAGE
  exit 1
fi

CMD="$1"

# ── CONTROL COMMANDS ───────────────────────────────────────────────────

if [ "$CMD" = "check" ]; then
  URL="${2:-http://localhost:8000}"
  step "Health check: $URL/health"
  curl -sf "$URL/health" | python3 -m json.tool 2>/dev/null || curl -sf "$URL/health"
  echo ""
  step "Detailed health: $URL/api/admin/health/detailed"
  # JWT required — try without token first
  curl -sf "$URL/health" >/dev/null 2>&1 && \
    curl -sf "$URL/api/admin/health/detailed" | python3 -m json.tool 2>/dev/null \
    || echo "(JWT required for /admin/health/detailed — login with ADMIN_PASSWORD first)"
  exit 0
fi

if [ "$CMD" = "status" ]; then
  step "Config status"
  if [ -f .env ]; then
    source .env
    ok ".env loaded"
  else
    warn ".env not found — run ./deploy.sh setup"
  fi
  step "Dependencies"
  python3 -c "import fastapi,uvicorn" 2>/dev/null && ok "Python deps OK" || warn "Run: pip install -r requirements.txt"
  step "Docker"
  if command -v docker >/dev/null 2>&1; then
    docker --version | head -1
    if docker compose version >/dev/null 2>&1; then
      ok "Docker Compose v2 available"
    else
      warn "Docker Compose v1 (upgrade to v2 for best results)"
    fi
  else
    warn "Docker not found — skipped"
  fi
  step "OpenWA"
  if [ -n "${OPENWA_API_URL:-}" ]; then
    info "OPENWA_API_URL = $OPENWA_API_URL"
    [ -n "$OPENWA_API_KEY" ] && ok "OPENWA_API_KEY is set" || warn "OPENWA_API_KEY is empty"
  else
    warn "OPENWA_API_URL not set in .env — check docker-compose.yml"
  fi
  exit 0
fi

if [ "$CMD" = "openwa" ]; then
  step "OpenWA standalone Docker run (v0.1.4)"
  cat <<"EOF"
docker run -p 2785:2785 -p 2886:2886 \
  -e NODE_ENV=production \
  -v openwa-data:/app/data \
  --name crm-openwa \
  rmyndharis/openwa:0.1.4

# Then:
# 1. Open http://localhost:2886 → Create Session → scan QR
# 2. Settings → API Access → copy API key
# 3. Set OPENWA_API_KEY and OPENWA_SESSION_ID in your .env
# 4. docker compose up -d
EOF
  exit 0
fi

# ── SETUP ─────────────────────────────────────────────────────────────────

if [ "$CMD" = "setup" ]; then
  step "WhatsApp CRM SA — Interactive Setup"

  if [ -f .env ]; then
    info ".env exists — skipping create"
  else
    cp .env.example .env
    ok "Created .env from .env.example"
    warn "Edit .env now and add:"
    echo "  - OPENWA_API_KEY   (from OpenWA dashboard → Settings → API Access)"
    echo "  - OPENWA_SESSION_ID (default)"
    echo "  - GROQ_API_KEY     (free at https://console.groq.com)"
    echo "  - ADMIN_PASSWORD   (pick a strong password)"
  fi
  exit 0
fi

# ── DOCKER COMPOSE ──────────────────────────────────────────────────────────

if [ "$CMD" = "docker" ]; then
  step "Starting WhatsApp CRM SA stack with Docker Compose"
  if ! command -v docker >/dev/null 2>&1; then
    warn "Docker not found. Skipping."
    exit 1
  fi
  step "Pulling images"
  docker compose pull --quiet 2>/dev/null || true
  step "Starting services"
  docker compose up -d
  sleep 3
  docker compose ps
  echo ""
  step "Health check"
  curl -sf http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "wait for startup..."
  step "OpenWA dashboard: http://localhost:2886  (scan QR code)"
  step "CRM API:         http://localhost:8000"
  step "Swagger docs:    http://localhost:8000/docs"
  step "OpenWA API:      http://localhost:2785/api"
  exit 0
fi

# ── RAILWAY ─────────────────────────────────────────────────────────────────

if [ "$CMD" = "railway" ]; then
  step "Deploying to Railway"
  if ! command -v railway >/dev/null 2>&1; then
    warn "railway CLI not found. Install: npm i -g @railway/cli && railway login"
    exit 1
  fi
  railway up
  exit $?
fi

# ── RENDER ─────────────────────────────────────────────────────────────────

if [ "$CMD" = "render" ]; then
  step "Render deploy — push to GitHub triggers Render auto-deploy"
  git push origin main 2>/dev/null || {
    warn "git push failed — check git remote"
    exit 1
  }
  ok "Pushed to GitHub. Render will pick it up from your linked repo."
  step "Don't forget to set env vars in Render Dashboard → Environment:"
  echo "  WHATSAPP_PROVIDER=openwa"
  echo "  OPENWA_API_URL=...     (your OpenWA instance URL)"
  echo "  OPENWA_API_KEY=...     (from OpenWA dashboard)"
  echo "  OPENWA_SESSION_ID=default"
  echo "  GROQ_API_KEY=...       (free at https://console.groq.com)"
  echo "  SECRET_KEY=...         (or use Render 'Generate Value')"
  echo "  ADMIN_PASSWORD=...     (pick a strong password)"
  exit 0
fi

warn "Unknown command: $CMD"
echo "Run ./deploy.sh (no args) for usage."
exit 1
