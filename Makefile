# WhatsApp CRM SA — Makefile
# Run `make help` to see all targets.

SHELL := /bin/bash
.DEFAULT_GOAL := help

# ── Metadata ──────────────────────────────────────────────────
NAME    := whatsapp-crm
VERSION := 0.1.4
APP_PORT := 8000

# ── Help ───────────────────────────────────────────────────────
help:
	@echo "WhatsApp CRM SA v$(VERSION) — Make targets:"
	@echo ""
	@echo "  make install       Install Python dependencies (pip install -r requirements.txt)"
	@echo "  make setup         Create .env from template (interactive)"
	@echo "  make run           Start uvicorn dev server (--reload)"
	@echo ""
	@echo "  make openwa        Print Docker run command for OpenWA gateway"
	@echo "  make openwa-start  Start OpenWA in Docker"
	@echo "  make openwa-stop   Stop Docker OpenWA"
	@echo ""
	@echo "  make docker-up     Start full stack (CRM + OpenWA + PostgreSQL) via compose"
	@echo "  make docker-down   Stop all containers"
	@echo "  make docker-logs   Tail CRM + OpenWA logs"
	@echo "  make docker-clean  Stop + remove all volumes"
	@echo ""
	@echo "  make health        GET /health — check CRM is responding"
	@echo "  make health-full   GET /health + /admin/health/detailed"
	@echo ""
	@echo "  make deploy-railway    Deploy to Railway (need railway CLI)"
	@echo "  make deploy-render     Push to Render via git (auto-deploy on push)"
	@echo "  make deploy-heroku     Push to Heroku"
	@echo ""
	@echo "  make clean         Remove __pycache__ / .pyc / .db files"
	@echo "  make fmt           Format with black"
	@echo "  make lint          Lint with ruff"

# ── App ───────────────────────────────────────────────────────
install:
	pip install --upgrade pip && pip install -r requirements.txt

setup:
	python scripts/setup-production.py

run:
	uvicorn app.main:app --host 0.0.0.0 --port $(APP_PORT) --reload --log-level info

# ── OpenWA ────────────────────────────────────────────────────
OPENWA_IMAGE := rmyndharis/openwa:0.1.4
OPENWA_NAME  := crm-openwa

openwa:
	@echo "docker run -p 2785:2785 -p 2886:2886 \\" && \\
        echo "  -v $(NAME)-openwa-data:/app/data --name $(OPENWA_NAME) $(OPENWA_IMAGE)"
	@echo "" && \\
        echo "Then open http://localhost:2886 → Create Session → scan QR"

openwa-start:
	docker run -d -p 2785:2785 -p 2886:2886 \\
		-v $(NAME)-openwa-data:/app/data \\
		--name $(OPENWA_NAME) $(OPENWA_IMAGE)

openwa-stop:
	docker rm -f $(OPENWA_NAME) 2>/dev/null || true

# ── Docker stack ───────────────────────────────────────────────
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f --tail=100

docker-clean:
	docker compose down -v --remove-orphans 2>/dev/null || true
	docker rm -f $(OPENWA_NAME) 2>/dev/null || true
	docker volume rm $(NAME)_postgres_data $(NAME)-openwa-data 2>/dev/null || true

# ── Health ────────────────────────────────────────────────────
health:
	@curl -sf http://localhost:$(APP_PORT)/health | python3 -m json.tool

health-full:
	@curl -sf http://localhost:$(APP_PORT)/health | python3 -m json.tool && \\
	echo "" && \\
	@echo "(Admin route needs JWT — see CLIENT-ONBOARDING.md for how to get a token)"

# ── Deploy ─────────────────────────────────────────────────────
deploy-railway:
	@if command -v railway >/dev/null 2>&1; then \\
		railway up; \\
	else \\
		echo "railway CLI not found. Install: npm i -g @railway/cli && railway login"; \\
		exit 1; \\
	fi

deploy-render:
	git push origin main 2>/dev/null || git push origin master
	@echo "Pushed. Render will auto-deploy. Check: https://dashboard.render.com"

deploy-heroku:
	@if command -v heroku >/dev/null 2>&1; then \\
		git push heroku main; \\
	else \\
		echo "heroku CLI not found. Install from https://devcenter.heroku.com/articles/heroku-cli"; \\
		exit 1; \\
	fi

# ── Cleanup ────────────────────────────────────────────────────
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*.db" | grep -v ".git" | xargs rm -f 2>/dev/null || true
	@echo "Cleaned __pycache__ / *.pyc / *.db"

fmt:
	black app/ scripts/

lint:
	ruff check app/ scripts/
