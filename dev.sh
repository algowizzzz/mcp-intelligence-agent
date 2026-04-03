#!/bin/bash
# Local dev: start SAJHA in background, agent server in foreground.
# Everything accessible at http://localhost:8000
set -e

VENV="$(dirname "$0")/venv/bin/python"
ROOT="$(cd "$(dirname "$0")" && pwd)"

cleanup() {
  echo ""
  echo "Stopping SAJHA..."
  kill "$SAJHA_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Start SAJHA MCP server in background
echo "Starting SAJHA MCP server on 127.0.0.1:3002..."
cd "$ROOT/sajhamcpserver"
"$VENV" run_server.py &> /tmp/sajha_dev.log &
SAJHA_PID=$!
cd "$ROOT"

# Wait for SAJHA to be ready
echo -n "Waiting for SAJHA..."
for i in $(seq 1 20); do
  if curl -sf http://localhost:3002/health > /dev/null 2>&1; then
    echo " ready."
    break
  fi
  sleep 1
  echo -n "."
done

echo ""
echo "Starting agent server on http://localhost:8000"
echo "  Chat UI:    http://localhost:8000/mcp-agent.html"
echo "  Admin:      http://localhost:8000/admin.html"
echo "  Login:      http://localhost:8000/login.html"
echo "  MCP Studio: http://localhost:3002  (super_admin only)"
echo ""

"$VENV" -m uvicorn agent_server:app --host 0.0.0.0 --port 8000 --reload
