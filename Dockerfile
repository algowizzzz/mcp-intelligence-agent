###############################################################################
# RiskGPT Digital Worker Platform — Single-Container Docker Image
#
# Services (managed by supervisord):
#   1. SAJHA MCP Server  — Flask/eventlet on 127.0.0.1:3002 (internal only)
#   2. Agent Server      — FastAPI/uvicorn on 127.0.0.1:8000 (internal only)
#   3. nginx             — Reverse proxy + static files on $PORT (external)
#
# External access only through nginx on $PORT (default 80).
# SAJHA and the agent server are bound to loopback — never directly exposed.
###############################################################################

FROM python:3.11-slim

# ── System packages ───────────────��──────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        gettext-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ──────────────────────────────��────────────────────────
# Install both requirements files in one layer to share the pip cache.
COPY requirements.txt                       ./requirements.txt
COPY sajhamcpserver/requirements.txt        ./sajha-requirements.txt
RUN pip install --no-cache-dir \
        -r requirements.txt \
        -r sajha-requirements.txt \
        bcrypt

# ── Application code ─────────────────────────────────────────────────────────��
COPY agent/             ./agent/
COPY agent_server.py    .
COPY run_sajha.py       .
COPY public/            ./public/
COPY sajhamcpserver/    ./sajhamcpserver/

# ── nginx configuration ───────────────────────────────────────────────────────
# Place as a template; scripts/start.sh runs envsubst to inject $PORT at runtime.
COPY nginx.conf /etc/nginx/templates/app.conf.template
RUN rm -f /etc/nginx/conf.d/default.conf \
          /etc/nginx/sites-enabled/default 2>/dev/null || true

# ── supervisord configuration ─────────────────────────────────────────────────
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# ── Entrypoint ────────────────────────��───────────────────────────────────────
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

# ── Runtime directories ───────────────────────────────────────────────────────
RUN mkdir -p \
        sajhamcpserver/logs \
        sajhamcpserver/data/flask_session \
        /var/log \
        /var/run

# ── Environment defaults ───────────────────────────��─────────────────────────��
ENV PYTHONUNBUFFERED=1 \
    PORT=80

EXPOSE 80

CMD ["/start.sh"]
