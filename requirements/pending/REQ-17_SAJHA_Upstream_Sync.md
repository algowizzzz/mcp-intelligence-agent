# REQ-17 — Adopt Upstream SAJHA MCP Server As-Is

**Status:** Pending — Analysis & Planning (verified 2026-05-17)
**Version:** 1.0
**Author:** Saad Ahmed
**Priority:** High — architectural alignment per leadership directive

> **Directive:** Use the upstream SAJHA MCP server at https://github.com/ajsinha/sajhamcpserver **as-is**, without modifying its code. Custom tools may be added on top. Our agent (`agent/` + `agent_server.py`) must adapt to consume it.

---

## 1. Current State

We currently ship a **forked copy** of SAJHA at `sajhamcpserver/` inside the agent repo (v2.9.8 frozen). It is Flask-based, has multi-worker data isolation baked in, and carries 31 custom tool implementations + 82 custom tool JSON configs.

Upstream has moved to **v5.0.0** with substantial breaking changes:

| Dimension | Our fork (v2.9.8) | Upstream (v5.0.0) | Compatibility |
|---|---|---|---|
| Web framework | Flask + SocketIO + EventLet | FastAPI + uvicorn + SSE/WS | **Breaking** |
| MCP protocol | Pre-2025 spec | MCP 2025-11-25 (Tasks, Elicitation, Sampling) | **Breaking** for clients |
| Tool composition | Direct call → dict | Kleisli composition with `StepResult` envelope | Breaking for tool outputs |
| Tool count shipped | ~40 (mostly removed in our fork) | 500 production tools (FMP, OpenBB, FRED, Alpha Vantage, etc.) | We'd inherit |
| Auth | API key, JWT (custom) | API key (`X-API-Key`), JWT (`Authorization: Bearer`) | Compatible (same header names) |
| Multi-worker isolation | **Yes** — `data_context`, `path_resolver`, `storage`, `worker_repository` | **No** — single-tenant; has logical "tenants" with tool patterns + quotas | **Capability gap** |
| Worker-scoped data layers (my_data / domain_data / common) | Yes | No | **Capability gap** |
| `X-Worker-*` headers | Yes (we read them in `g.worker_ctx`) | Not recognized | **Capability gap** |
| Config format | `application.properties` + `workers.json` + `users.json` | `application.yml` (YAML) + `users.json` + `apikeys.json` | Partial overlap |
| Storage abstraction | LocalStorage + S3Storage (our addition) | Bundled (`storage.py`) — Local + S3 with cache | Functionally similar |
| Frontend / admin UI | Provided by our agent (`public/`) | Bundled (Jinja2, 42 screens, 4 themes) | Both exist; can coexist |
| Hot-reload | 5s (we changed default); 300s upstream default | 300s | Compatible |

## 2. Goal

Run upstream SAJHA unchanged in our local-dev + production stack while keeping:
1. All 31 of our custom tool implementations (IRIS CCR, EDGAR enrichment, Tavily, connectors, BM25, Python executor, etc.)
2. All 82 of our custom tool JSON configs
3. The multi-worker data isolation model that downstream relies on
4. Our agent (LangGraph FastAPI agent server) calling SAJHA over HTTP/SSE

…with **zero modifications to upstream source files**. Custom tools live in a separable layer that drops onto upstream cleanly.

## 3. Architectural Options

### Option A — Strict adoption (RECOMMENDED)

Upstream is consumed unchanged: as a git submodule pinned to a tag, or as a vendored copy in a sibling directory. We never edit files under it.

Our agent stack contributes:
- A **tools pack** (`tools-pack/`) — 31 tool implementations + 82 JSON configs. Mounted into upstream's `config/tools/` (and `sajha/tools/impl/` for code) via either: (a) upstream's plugin system (`config/plugins/*/plugin.json` manifest), or (b) `SAJHA_CONFIG_TOOLS_DIR` env var pointed at our directory, plus `PYTHONPATH` extension to expose our `tools.impl` package.
- A **worker-context middleware** in `agent_server.py` that injects `X-Worker-*` headers on every SAJHA call and applies post-hoc path scoping in our tool wrappers (instead of inside SAJHA).
- A separate **worker-data manager service** (or stay inside our agent server) that owns `data/workers/{worker_id}/` and the per-user namespacing logic. Our tool implementations read worker context out of headers rather than SAJHA's `g.worker_ctx`.

**Pros:** Future upstream updates are `git pull` away. Zero divergence risk. Cleanest separation of concerns.
**Cons:** We push worker-scoping logic into either (a) our agent layer, or (b) each custom tool. Slightly more glue code in the agent.
**Risk to multi-worker:** Medium. Achievable by having each custom tool read worker context from request headers in its `execute()` method, instead of via Flask `g`.

### Option B — Fork v5.0.0 and re-apply patches

We fork upstream v5.0.0 once, port our 5 framework files (`data_context.py`, `path_resolver.py`, `storage.py`, `worker_repository.py`, db migrations) from Flask → FastAPI, and maintain a long-lived branch.

**Pros:** Worker isolation stays inside SAJHA, like today. Migration is largely mechanical (Flask `g` → FastAPI `request.state`).
**Cons:** Violates the leadership directive ("use it as-is"). Every upstream release requires conflict resolution. Re-introduces the drift problem we just spent a session cleaning up.
**Recommendation:** Reject unless leadership later softens the directive.

### Option C — Skip upstream, keep our fork

Status quo. Pin our v2.9.8 fork; accept that we won't benefit from upstream's 500 tools or MCP 2025-11-25 features.

**Recommendation:** Reject unless Option A turns out infeasible.

**This requirements doc plans for Option A. Option B / C are documented as fallbacks only.**

## 4. Functional Requirements (Option A)

### R-17.1 — Upstream as a pinned dependency
- Add `sajhamcpserver-upstream/` as a git submodule of our repo (or a sibling repo + lockfile that records the upstream SHA).
- Document the exact commit pinned. No upstream files are modified.
- A `make sync-upstream` (or equivalent) script bumps the pin and rebuilds.

### R-17.2 — Tools pack
- Create `tools-pack/` at the repo root containing:
  - `tools-pack/configs/*.json` — 82 JSON tool configs
  - `tools-pack/impl/*.py` — 31 Python tool implementations
  - `tools-pack/plugin.json` — manifest declaring the pack to upstream's plugin system
  - `tools-pack/requirements.txt` — any extra Python deps (rank-bm25, pdfplumber, python-docx, openpyxl, plotly, pyarrow, duckdb, etc.)
- Verify the pack loads under upstream's `PluginManager.load_all()` (`sajha/core/plugins.py`).

### R-17.3 — Worker context propagation
- Agent server (`agent/tools.py:_service_headers()`) continues to send `X-Worker-Id`, `X-User-Id`, `X-Worker-Data-Root`, `X-Worker-My-Data-Root`, etc., as today.
- Custom tools in `tools-pack/impl/` read these headers from the request (FastAPI: `request.headers.get(...)`) inside their `execute()` method, instead of from Flask `g`. A small helper `tools_pack.worker_ctx.get_ctx(request)` centralizes this.
- Upstream sees the headers but ignores them — that's fine.

### R-17.4 — Data path resolution
- Move `data_context.py` / `path_resolver.py` logic into `tools-pack/lib/worker_paths.py`. Same API surface; no Flask dependency.
- Our agent server keeps `_resolve_fs_path()` for the `/api/fs/*` endpoints (file panel UI) — these don't touch SAJHA.

### R-17.5 — Storage abstraction
- Use upstream's bundled `sajha/core/storage.py` (it has Local + S3 + cache, like ours). Configure via upstream's `application.yml`.
- Our custom tools use upstream's storage helper, not our own `sajha/storage.py`.

### R-17.6 — Worker repository + admin UI
- Our agent server keeps owning `workers.json`, `users.json` (per-worker tool allowlists, role-based admin actions, file management). These don't need to live inside SAJHA.
- Upstream's bundled admin UI is **disabled** (don't mount its routes externally). Our `public/admin.html` remains canonical.

### R-17.7 — MCP protocol upgrade
- Audit our agent's SAJHA calls (`agent/tools.py:_call_sajha()`) and adapt to upstream's MCP 2025-11-25 response shape:
  - `StepResult` envelope: `{value, error, trace, duration, confidence, _composition: {...}}` — unwrap to legacy shape, or update downstream parsers.
  - Tool errors: `{"isError": true, "content": [...]}` — handle alongside protocol errors.
  - Tool listing: confirm `tools/list` returns the same fields (`name`, `description`, `inputSchema`).

### R-17.8 — Auth header
- We currently send `Authorization: <SAJHA_API_KEY>` directly (no `Bearer` prefix). Upstream expects `X-API-Key: sja_<key>` or `Authorization: Bearer <JWT>`. Switch to `X-API-Key` in `_service_headers()`.

### R-17.9 — Deployment
- Local dev: `python sajhamcpserver-upstream/run_server.py` (port 3002).
- Production: extend `docker-compose.prod.yml` so the `app` container can find `sajhamcpserver-upstream/` (via volume mount or copy step), set `SAJHA_CONFIG_PLUGINS_DIR=/app/tools-pack`.
- Health check: `curl http://localhost:3002/health` — same endpoint, upstream provides it.

## 5. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NF-1 | Zero modifications to files under `sajhamcpserver-upstream/`. Verified by `git diff --quiet sajhamcpserver-upstream` in CI. |
| NF-2 | Upstream version pinned to a specific tag (initially `v5.0.0`). Pin bumps are explicit commits with regression testing. |
| NF-3 | All 31 custom tools pass smoke tests against upstream (each tool gets a one-line invocation test). |
| NF-4 | Multi-worker isolation: a tool invoked with worker A's headers cannot read worker B's files. End-to-end test required. |
| NF-5 | Agent server startup time does not regress more than 30% (currently ~3s SAJHA + ~3s agent). |

## 6. Acceptance Criteria

- [ ] `sajhamcpserver-upstream/` exists as a pinned submodule/clone, never modified.
- [ ] `tools-pack/` loads cleanly under upstream's plugin system (`config/plugins/`); upstream's startup log shows all 31 tools discovered.
- [ ] Our agent connects to upstream via `X-API-Key`, can call `tools/list`, and sees both upstream's 500 built-in tools plus our 31 custom tools.
- [ ] A chat session against the `Market Risk Worker` worker finds files in `data/workers/w-market-risk/` and not in any other worker's directory.
- [ ] All UAT tests under `tests/` pass.
- [ ] CLAUDE.md, DOCS_INDEX.md, and LOCAL_DEV_SETUP.md updated to point at upstream + tools-pack.
- [ ] Our embedded `sajhamcpserver/` folder is removed (or moved to archive/).

## 7. Open Decisions

| # | Question | Default if undecided |
|---|---|---|
| D-1 | Submodule vs vendored clone vs pip install? | **Submodule** pinned to tag |
| D-2 | Plugin manifest vs `SAJHA_CONFIG_TOOLS_DIR`? | **Plugin manifest** — cleanest separation |
| D-3 | Keep our admin UI / disable upstream's? | **Keep ours**; mount upstream only at `/mcp-studio/` |
| D-4 | Adapt to MCP 2025-11-25 in agent, or shim StepResult in our tool wrappers? | **Adapt agent** — short-term shim, long-term native |
| D-5 | What to do with our embedded `sajhamcpserver/` after migration? | Move to `archive/sajhamcpserver-v2.9.8-fork/` |

## 8. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Upstream's plugin system doesn't surface tools to clients via `tools/list` | High | Verify in a 30-min spike before committing to plugin manifest |
| Custom tools depend on Flask `g` and break under FastAPI request context | Medium | Centralize via `worker_ctx.get_ctx(request)`; audit each tool's `execute()` |
| MCP 2025-11-25 changes break our SSE handler | Medium | Pin upstream to a version where compatibility shim exists, or update SSE handler in same PR |
| Worker isolation regresses without our `data_context.py` baked into SAJHA | High | Multi-worker e2e test as gate (NF-4) |
| Upstream contains tools that conflict with our tool names (e.g. EDGAR tools) | Low | Audit upstream's `config/tools/` for name overlaps; rename our copies if needed |

## 9. Effort Estimate

| Phase | Estimate |
|---|---|
| Spike: plugin system + smoke test 1 tool against upstream | 1 day |
| Build `tools-pack/` (configs + impls + plugin.json + requirements) | 3 days |
| Adapt agent (`X-API-Key`, MCP 2025-11-25 response shape) | 2 days |
| Move worker-context resolution out of SAJHA into agent / tools-pack | 3 days |
| Deployment (Docker, env, health checks) | 1 day |
| UAT + regression testing | 2 days |
| Documentation update | 1 day |
| **Total** | **~2 weeks of focused dev** |

## 10. Out of Scope (For This REQ)

- Upgrading our LLM provider abstraction (separate REQ).
- Migrating our admin UI to React or any framework swap on our side.
- Contributing our worker-isolation back to upstream as a PR (could be a separate REQ-18 / a follow-up).
- Replacing our agent's LangGraph stack — that is unaffected by this work.

## 11. References

- Upstream repo: https://github.com/ajsinha/sajhamcpserver (commit `7921665`, v5.0.0)
- Upstream README: `/Users/saadahmed/Desktop/durga_agent/sajhamcpserver-upstream/README.md`
- Upstream CHANGELOG: `/Users/saadahmed/Desktop/durga_agent/sajhamcpserver-upstream/CHANGELOG.md`
- Upstream tool registration code: `sajha/tools/tools_registry.py` (load + scan + hot-reload)
- Upstream plugin system: `sajha/core/plugins.py`
- Upstream API surface: `sajha/routes/api_routes.py`, `mcp_routes.py`
- Our fork: `mcp-intelligence-agent/sajhamcpserver/` (v2.9.8)
- Our agent SAJHA caller: `agent/tools.py:_service_headers()`, `_call_sajha()`
- Companion docs: [REQ-17_PM_Brief.md](REQ-17_PM_Brief.md), [REQ-17_Jr_Dev_Stories.md](REQ-17_Jr_Dev_Stories.md), [REQ-17_Regression_Test_Suite.md](REQ-17_Regression_Test_Suite.md)
