#!/usr/bin/env bash
###############################################################################
# SAJHA MCP Agent — Hetzner Server Bootstrap Script
#
# Run this ONCE on a fresh server after cloud-init finishes:
#   ssh root@62.238.3.148 'bash -s' < scripts/bootstrap-server.sh
#
# What it does:
#   1. Configures UFW firewall (SSH, HTTP, HTTPS only)
#   2. Creates app directories
#   3. Sets up Docker GHCR auth
#   4. Pulls and starts the stack
###############################################################################
set -euo pipefail

echo "=== SAJHA Server Bootstrap ==="
echo "Server: $(hostname) | $(date)"

# ── 1. Wait for cloud-init to finish ─────────────────────────────────────────
echo ""
echo "Step 1: Waiting for cloud-init to finish..."
cloud-init status --wait 2>/dev/null || true

# ── 2. Verify Docker is installed ────────────────────────────────────────────
echo ""
echo "Step 2: Verifying Docker..."
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Installing..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi
docker --version
docker compose version

# ── 3. Configure UFW Firewall ────────────────────────────────────────────────
echo ""
echo "Step 3: Configuring firewall..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
ufw status verbose

# ── 4. Create directories ────────────────────────────────────────────────────
echo ""
echo "Step 4: Creating directories..."
mkdir -p /opt/sajha/data/{postgres,app,logs}
mkdir -p /opt/sajha/backups
mkdir -p /opt/sajha/scripts

# ── 5. Create .env template ─────────────────────────────────────────────────
echo ""
echo "Step 5: Creating .env template..."
if [ ! -f /opt/sajha/.env ]; then
    cat > /opt/sajha/.env << 'ENVFILE'
# === SAJHA MCP Agent — Production Environment ===
# Fill in the values below, then run:
#   cd /opt/sajha && docker compose -f docker-compose.prod.yml up -d

# GitHub Container Registry (your-org/your-repo)
GITHUB_REPO=your-github-username/react_agent

# LLM Provider
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-xxxxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514
LLM_MAX_TOKENS=8192

# Authentication
JWT_SECRET=CHANGE_ME_TO_RANDOM_64_CHARS

# PostgreSQL
POSTGRES_DB=sajha
POSTGRES_USER=sajha
POSTGRES_PASSWORD=CHANGE_ME_TO_RANDOM_32_CHARS

# SAJHA MCP Server
SAJHA_API_KEY=sja_full_access_admin

# External APIs (optional)
TAVILY_API_KEY=

# Storage
STORAGE_BACKEND=local
ENVFILE
    echo "  Created /opt/sajha/.env — EDIT THIS FILE before deploying!"
else
    echo "  .env already exists, skipping."
fi

# ── 6. Set up daily backup cron ──────────────────────────────────────────────
echo ""
echo "Step 6: Setting up daily backups..."
cat > /opt/sajha/scripts/backup.sh << 'BACKUP'
#!/bin/bash
# Daily backup of Postgres + app data
set -e
BACKUP_DIR="/opt/sajha/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Postgres dump
docker exec sajha-postgres pg_dump -U sajha sajha | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# App data (configs, uploads, etc.)
tar -czf "$BACKUP_DIR/appdata_$DATE.tar.gz" -C /opt/sajha/data/app .

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "[$(date)] Backup completed: postgres_$DATE.sql.gz, appdata_$DATE.tar.gz"
BACKUP
chmod +x /opt/sajha/scripts/backup.sh

# Add daily cron at 3 AM
(crontab -l 2>/dev/null | grep -v backup.sh; echo "0 3 * * * /opt/sajha/scripts/backup.sh >> /opt/sajha/backups/backup.log 2>&1") | crontab -

# ── 7. Set up log rotation ──────────────────────────────────────────────────
echo ""
echo "Step 7: Setting up log rotation..."
cat > /etc/logrotate.d/sajha << 'LOGROTATE'
/opt/sajha/data/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    copytruncate
}
LOGROTATE

# ── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo "=== Bootstrap Complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit /opt/sajha/.env with your API keys"
echo "  2. Copy docker-compose.prod.yml to /opt/sajha/"
echo "  3. Copy scripts/init-db.sql to /opt/sajha/scripts/"
echo "  4. Login to GHCR:  echo YOUR_GHCR_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin"
echo "  5. Deploy:  cd /opt/sajha && docker compose -f docker-compose.prod.yml up -d"
echo "  6. Check:   curl http://localhost/health"
echo ""
echo "Server IP: $(curl -s ifconfig.me)"
