# MCP Intelligence Agent — Claude Code Instructions

## Architecture
Three-layer system:
- **Frontend** (`public/index.html`, `mcp-agent.html`) — HTML/JS chat UI
- **Agent Server** (`agent_server.py`) — FastAPI on port 8000, LangGraph agent, SSE streaming
- **SAJHA MCP Server** (`sajhamcpserver/`) — Flask MCP server on port 3002, 74+ tools

## Running Locally
```bash
# Terminal 1 — SAJHA MCP server (must start first)
cd sajhamcpserver
../venv/bin/python run_server.py

# Terminal 2 — Agent server
uvicorn agent_server:app --port 8000 --reload

# Frontend: open public/index.html in browser
```

## Key Directories
```
agent/              # LangGraph agent, prompt, tools client
agent_server.py     # FastAPI entrypoint, SSE streaming, canvas detection
sajhamcpserver/
  config/
    tools/          # JSON config per tool (name, implementation, schema)
    application.properties  # data paths, feature flags
  sajha/tools/impl/ # Tool implementations
  data/             # All data files (iris, osfi, counterparties, duckdb, sqlselect, uploads)
requirements/       # ERD and requirements docs
```

## Data Paths (application.properties)
- IRIS CCR: `./data/iris/iris_combined.csv`
- OSFI docs: `./data/osfi/`
- DuckDB: `./data/duckdb/`
- Uploads: `./data/uploads/`

## Adding a New Tool
1. Create implementation class in `sajhamcpserver/sajha/tools/impl/`
2. Create JSON config in `sajhamcpserver/config/tools/<tool_name>.json`
3. Set `"implementation": "sajha.tools.impl.<module>.<ClassName>"`
4. Hot-reload picks it up within 5 minutes — no restart needed

## Key Tool Modules
- `edgar_tavily_tools.py` — SEC EDGAR qualitative extraction (MD&A, earnings, segments, risk)
- `edgar_metric_tools.py` — XBRL financial metrics and ratios
- `tavily_ir_tool.py` — Universal IR tools (any public company, Tavily-native)
- `iris_ccr_tools.py` — IRIS counterparty credit risk data
- `osfi_tools.py` — OSFI regulatory guidance documents
- `tavily_yahoo_finance_tool.py` — Stock quotes, history, symbol search

## SEC/EDGAR Notes
- Use `direct_sec_json()` for all SEC JSON API endpoints (not Tavily)
- Use `stream_sec_section()` for large SEC Archives HTML filings (>2 MB)
- BMO and other Canadian banks file 6-K (not 10-Q) — EDGAR tools target 10-K/10-Q only
- `_validate_sources()` blocks synthesis from wrong-company or stale-year sources

## Authentication
- Agent server: `AGENT_API_KEYS` env var (comma-separated); empty = auth disabled
- SAJHA server: `user_id` + `password` via `/api/auth/login` → JWT Bearer token
- Default user: `risk_agent` / `RiskAgent2025!`
