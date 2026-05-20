# WhatsApp CRM SA — FastAPI Application Container
# Uses Python 3.12 slim + uvicorn as ASGI server
# Built to run alongside rmyndharis/openwa:0.1.4 in the same compose network

FROM python:3.12-slim-bookworm

# ── Labels ──────────────────────────────────────────────────
LABEL org.opencontainers.image.title     = "WhatsApp CRM SA"
LABEL org.opencontainers.image.description= "Free WhatsApp CRM for SA SMMEs — FastAPI + OpenWA"
LABEL org.opencontainers.image.source     = "https://github.com/mikewithoutthemechanics/whatsapp-crm"
LABEL org.opencontainers.image.licenses   = "MIT"

# ── Install OS deps ─────────────────────────────────────────
# - libpq-dev   → psycopg / asyncpg PostgreSQL client
# - gcc         → compile psycopg / any C-extension wheels
# - libmagic1   → python-magic for file type detection
# - curl/tini   → healthcheck + clean entrypoint signal handler
RUN apt-get update && apt-get install -y --no-install-recommends \
      gcc \
      libpq-dev \
      curl \
      libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python deps ──────────────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── Application code ─────────────────────────────────────────
COPY app/    ./app/
COPY scripts ./scripts/
COPY tests   ./tests/

# ── OpenWA client note ───────────────────────────────────────
# This app calls OpenWA's REST API at http://openwa:2785 (Docker network name).
# No OpenWA Python SDK needed — pure HTTP only.
ENV OPENWA_API_URL=http://openwa:2785

# ── Entrypoint ──────────────────────────────────────────────
EXPOSE 8000

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"]
