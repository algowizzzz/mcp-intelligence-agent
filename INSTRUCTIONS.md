# MCP Intelligence Agent — Build Instructions & Progress Tracker

## Project Overview

Build a three-layer financial risk intelligence agent per the TRD (`mcp-agent-trd-final.docx`).

- **Layer 1**: HTML Frontend (`mcp-agent.html`) — single file, vanilla JS, SSE stream reader
- **Layer 2**: LangGraph FastAPI Backend (`agent_server.py` + `agent/` package) — ReAct agent, SSE streaming
- **Layer 3**: SAJHA MCP Server (port 3002) — already running, needs 5 custom tools + RBAC user

---

## Architecture

```
Browser (port 8080)          FastAPI (port 8000)          SAJHA (port 3002)
┌─────────────────┐    SSE   ┌──────────────────┐  HTTP   ┌────────────────┐
│ mcp-agent.html  │ ◄──────► │ agent_server.py  │ ──────► │ SAJHA MCP Svr  │
│ Vanilla JS      │  POST    │ LangGraph Agent  │ Bearer  │ 6 tools (RBAC) │
│ SSE reader      │          │ Claude Sonnet 4  │  token  │ BaseMCPTool    │
└─────────────────┘          └──────────────────┘         └────────────────┘
```

## Target Directory Structure

```
/Users/saadahmed/Desktop/react_agent/
├── INSTRUCTIONS.md              # This file
├── mcp-agent-trd-final.docx     # TRD (source of truth)
├── agent_server.py              # FastAPI app + SSE endpoint
├── requirements.txt             # Python deps (langchain, fastapi, etc.)
├── .env                         # Secrets (ANTHROPIC_API_KEY, SAJHA_PASSWORD)
├── agent/
│   ├── __init__.py
│   ├── agent.py                 # create_agent + checkpointer
│   ├── tools.py                 # 6 @tool wrappers → _call_sajha()
│   └── prompt.py                # SYSTEM_PROMPT
├── mcp-agent.html               # Single-file frontend
├── sajhamcpserver/              # SAJHA repo (already cloned & running)
│   ├── config/users.json        # Add risk_agent user
│   ├── config/server.properties # CORS config
│   ├── sajha/tools/impl/        # 5 new tool Python files
│   └── config/tools/            # 5 new tool JSON configs
└── tests/
    ├── test_tools.py
    ├── test_agent.py
    └── test_api.py
```

---

## Stories & Status

### EPIC 1: SAJHA MCP Server Configuration
> Configure SAJHA for agent use: RBAC user, CORS, and 5 custom tools.

| Story | Description | Status | QA |
|-------|-------------|--------|----|
| S1.1 | Add `risk_agent` user to `config/users.json` with 6-tool RBAC | DONE | Login OK, token returned, RBAC roles correct |
| S1.2 | Configure CORS in `config/server.properties` for ports 8000/8080 | DONE | Origins set to localhost:8080,8000 |
| S1.3 | Build `get_counterparty_exposure` tool (Pattern A — Python class) | DONE | RBC: notional $1.71B, MTM $194.8M, PFE $32.3M, rating BBB- |
| S1.4 | Build `get_trade_inventory` tool (Pattern A — Python class) | DONE | Goldman: 11 trades, $2.84B total notional |
| S1.5 | Build `get_credit_limits` tool (Pattern A — Python class) | DONE | TD Bank: 4 limit types, Wrong-Way Risk 89% WARNING |
| S1.6 | Build `get_historical_exposure` tool (Pattern A — Python class) | DONE | JPM @ 2025-09-30: notional $553M, 148 trades |
| S1.7 | Build `get_var_contribution` tool (Pattern A — Python class) | DONE | Deutsche Bank: VaR $75.3M, stress loss $446M |
| S1.8 | Verify all 6 tools (5 new + tavily) work via risk_agent user | DONE | All 5 custom tools pass via risk_agent bearer token |

### EPIC 2: LangGraph FastAPI Backend
> Build the agent reasoning layer with SSE streaming.

| Story | Description | Status | QA |
|-------|-------------|--------|----|
| S2.1 | Create `requirements.txt` with all Python deps | DONE | pip install OK, 43 packages |
| S2.2 | Create `.env` template with all required env vars | DONE | Placeholder key — user must fill ANTHROPIC_API_KEY |
| S2.3 | Create `agent/prompt.py` — SYSTEM_PROMPT | DONE | Attribution rules, reasoning style, financial precision |
| S2.4 | Create `agent/tools.py` — 6 @tool wrappers + `_call_sajha()` | DONE | 6 tools loaded, names match TRD |
| S2.5 | Create `agent/agent.py` — `create_agent` + MemorySaver | DONE | CompiledStateGraph created, no warnings |
| S2.6 | Create `agent_server.py` — FastAPI + SSE endpoint | DONE | uvicorn running on :8000, /docs returns 200 |
| S2.7 | Verify full SSE contract: session, text, tool_start, tool_end, usage, [DONE] | DONE | All event types verified, [src:] attribution in synthesis |

### EPIC 3: HTML Frontend
> Single-file frontend with SSE reader, three-tab UI, exports.

| Story | Description | Status | QA |
|-------|-------------|--------|----|
| S3.1 | Build HTML structure: query panel, tabs, results area | DONE | 1915 lines, dark theme, three-tab UI |
| S3.2 | Implement `runAgent()` SSE reader + event router | DONE | All 7 event types routed |
| S3.3 | Implement tool cards: onToolStart, onToolEnd, TOOL_UI_META | DONE | 6 tools with icon/color/label |
| S3.4 | Implement `renderWithAttribution()` + `jumpToTool()` | DONE | [src:] → clickable badges with flash |
| S3.5 | Implement cost tracking: `recordCost()`, `updateCostDisplay()` | DONE | Sonnet 4 pricing: $3/$15 per M |
| S3.6 | Implement session persistence: save/restore/clear | DONE | 24h TTL, restore banner |
| S3.7 | Implement exports: `exportPDF()`, `exportMarkdown()` | DONE | Print mode CSS + clipboard MD |
| S3.8 | Implement Cancel button + HITL card | DONE | HITL URL fixed to /api/agent/run |

### EPIC 4: Integration & End-to-End QA
> Wire all three layers together and verify complete flows.

| Story | Description | Status | QA |
|-------|-------------|--------|----|
| S4.1 | Start all 3 services (SAJHA:3002, FastAPI:8000, HTML:8080) | DONE | All 3 return HTTP 200/302 |
| S4.2 | Full query: "Get the full picture on RBC" → report | DONE | Tool called, synthesis with [src:] badges, usage tracked |
| S4.3 | QoQ trend: 4x parallel historical exposure calls | READY | Test in browser |
| S4.4 | Session restore: refresh page, verify restore banner | READY | Test in browser |
| S4.5 | Export: PDF + Markdown both work | READY | Test in browser |
| S4.6 | Error handling: kill SAJHA mid-query → partial results | READY | Test in browser |

---

## Build Order & Parallelism Plan

### Phase 1 — Parallel (SAJHA config + Backend skeleton + Frontend skeleton)
Run 3 agents in parallel:
- **Agent A**: SAJHA config (S1.1, S1.2) + build all 5 tools (S1.3–S1.7)
- **Agent B**: Backend (S2.1–S2.6) — requirements, .env, agent/, agent_server.py
- **Agent C**: Frontend (S3.1–S3.8) — mcp-agent.html single file

### Phase 2 — Integration
- Wire frontend → backend → SAJHA
- Run S1.8 (tool verification), S2.7 (SSE verification)

### Phase 3 — End-to-End QA
- Stories S4.1–S4.6

---

## QA Procedures

### Tool QA (per tool)
```bash
# 1. Login as risk_agent
TOKEN=$(curl -s http://localhost:3002/api/auth/login \
  -X POST -H 'Content-Type: application/json' \
  -d '{"user_id":"risk_agent","password":"RiskAgent2025!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 2. Execute tool
curl -s http://localhost:3002/api/tools/execute \
  -X POST -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"tool":"TOOL_NAME","arguments":{...}}'

# 3. Verify: success=true, expected fields present, no error
```

### Backend QA
```bash
# SSE stream test
curl -N -X POST http://localhost:8000/api/agent/run \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is RBC exposure?"}' 2>&1 | head -50
# Expect: data: {"type":"session",...}
# Expect: data: {"type":"text",...}
# Expect: data: {"type":"tool_start",...}
# Expect: data: [DONE]
```

### Frontend QA
```
1. Open http://localhost:8080/mcp-agent.html
2. Type query → Run → verify 3 tabs populate
3. Click [src:] badge → verify jump to tool card
4. Check cost meter shows non-zero
5. Refresh → verify restore banner appears
6. Click Export PDF → verify print dialog
7. Click Export MD → verify clipboard
```

---

## Tool Implementation Notes

### Data Strategy
Since internal risk APIs don't exist, all 5 tools return **realistic synthetic data** with:
- Consistent counterparty names (RBC, TD Bank, Goldman Sachs, JPMorgan, etc.)
- Realistic financial figures (notional $50M–$2B, MTM -$50M–$100M, etc.)
- Date-sensitive responses (historical tool varies by date)
- Deterministic: same counterparty + date → same result (seeded random)

### Tool Patterns
All 5 tools use **Pattern A** (Python class extending BaseMCPTool) since there are no real internal APIs or databases to connect to. Each tool:
1. Python class in `sajhamcpserver/sajha/tools/impl/`
2. JSON config in `sajhamcpserver/config/tools/`
3. Returns realistic synthetic financial data
4. Has proper input_schema with required/optional params

---

## Environment Variables (.env)

```
ANTHROPIC_API_KEY=sk-ant-...          # Required — user must fill
SAJHA_BASE_URL=http://localhost:3002
SAJHA_PASSWORD=RiskAgent2025!
LANGCHAIN_TRACING_V2=true             # Optional — LangSmith
LANGCHAIN_API_KEY=ls__...             # Optional — LangSmith
LANGCHAIN_PROJECT=mcp-intelligence-agent
```

---

## Change Log

| Date | Change | Stories |
|------|--------|---------|
| 2026-03-29 | Initial setup: cloned SAJHA, server running on :3002 | — |
| 2026-03-29 | Created INSTRUCTIONS.md | — |
| 2026-03-29 | Phase 1 complete: all 3 layers built in parallel | S1.1–S1.8, S2.1–S2.6, S3.1–S3.8 |
| 2026-03-29 | Fixed HITL resume URL in frontend (was /api/agent/resume, now /api/agent/run) | S3.8 |
| 2026-03-29 | Integration QA: all 3 services running, 5 SAJHA tools verified | S4.1 |
| 2026-03-29 | Fixed load_dotenv order in agent.py (key not loaded at import time) | S2.7 |
| 2026-03-29 | Fixed SSE streaming: text content extraction, AIMessage usage_metadata, tool output serialization | S2.7 |
| 2026-03-29 | END-TO-END SUCCESS: RBC query → tool call → synthesis with [src:] → [DONE] | S4.2 |
