# REQ-17 — Jr Dev Stories: Adopt Upstream SAJHA As-Is

**Status:** Pending — Awaiting approval of [REQ-17 technical requirements](REQ-17_SAJHA_Upstream_Sync.md) and [PM brief](REQ-17_PM_Brief.md)
**Date:** 2026-05-17

This is a sequenced backlog of ~10 stories. Most are 1 day or less. They're written for someone new to the codebase — each story includes "Where to look first" and "How to verify."

---

## Story 0 — Spike: confirm upstream's plugin system loads our tools (1 day)

**Goal:** Prove that upstream's plugin system can load a Python tool class without modifying any upstream files. **If this fails, escalate before continuing.**

**Steps:**
1. Read `sajhamcpserver-upstream/sajha/core/plugins.py` end-to-end. Understand `PluginManager.load_all()` flow.
2. Make a folder `~/Desktop/durga_agent/spike-tools-pack/` with:
   - `plugin.json` — manifest declaring one tool
   - `tools/hello_tool.json` — one tool config
   - `tools/hello_tool.py` — `class HelloTool(BaseMCPTool)` returning `{"message": "hello"}`
3. Start upstream with `SAJHA_CONFIG_PLUGINS_DIR=~/Desktop/durga_agent/spike-tools-pack python run_server.py`.
4. Call `POST http://localhost:3002/mcp` with `tools/list` — confirm `hello_tool` appears.
5. Call `POST http://localhost:3002/mcp` with `tools/call` for `hello_tool` — confirm the response is `{"message": "hello"}`.

**Verify:** `curl` shows the tool in both list and call responses. Upstream working tree (`git status` inside upstream submodule) is clean.

**Output:** Brief Slack/notes update: "spike PASSED" or "spike FAILED — here's why." If failed, the team picks Option B.

---

## Story 1 — Pin upstream as a git submodule (½ day)

**Goal:** Add `sajhamcpserver-upstream/` to our repo as a pinned submodule, never modified.

**Steps:**
1. Add submodule: `git submodule add https://github.com/ajsinha/sajhamcpserver.git sajhamcpserver-upstream`
2. Pin to v5.0.0 tag: `cd sajhamcpserver-upstream && git checkout v5.0.0 && cd ..`
3. Commit: "build: pin upstream SAJHA submodule to v5.0.0"
4. Add CI check: `git diff --quiet sajhamcpserver-upstream || (echo "upstream modified" && exit 1)`. Add to `.github/workflows/ci.yml`.
5. Document the pin bump procedure in `CONTRIBUTING.md` or a new `docs/upstream-sync.md`.

**Verify:** `git log --oneline -1 sajhamcpserver-upstream` shows the v5.0.0 commit. Cloning the repo fresh and running `git submodule update --init` pulls upstream.

---

## Story 2 — Set up `tools-pack/` scaffold (½ day)

**Goal:** Create the directory layout that custom tools will live in.

**Steps:**
1. `mkdir -p tools-pack/{impl,configs,lib}`
2. Write `tools-pack/plugin.json` (manifest using upstream's format from Story 0).
3. Write `tools-pack/requirements.txt` listing every Python dep our custom tools need (rank-bm25, pdfplumber, python-docx, openpyxl, plotly, pyarrow, duckdb, etc. — grep them from our current tool implementations).
4. Write `tools-pack/lib/worker_ctx.py` — a single helper:
   ```python
   def get_worker_ctx(request) -> dict:
       """Read X-Worker-* headers from a FastAPI request; return a dict mirroring
       the shape our tools previously got from Flask g.worker_ctx."""
   ```
5. Write a one-line README at `tools-pack/README.md` saying "this folder is loaded by upstream's plugin system; don't edit individual tools without re-reading REQ-17."

**Verify:** Directory exists, manifest validates against upstream's `plugins.py` schema (run upstream's plugin loader manually).

---

## Story 3 — Port one tool end-to-end (1 day)

**Goal:** Move ONE custom tool from our fork into `tools-pack/` and prove it works through upstream. Pick the simplest tool. Best candidate: `bm25_search_tool.py` — no external API deps, no connectors, no LLM.

**Steps:**
1. Copy `mcp-intelligence-agent/sajhamcpserver/sajha/tools/impl/bm25_search_tool.py` → `tools-pack/impl/bm25_search_tool.py`.
2. Copy `config/tools/document_search.json` → `tools-pack/configs/document_search.json`. Update the `"implementation"` path to match the new module location.
3. In `bm25_search_tool.py`, replace `from flask import g; ctx = g.worker_ctx` (or similar) with `ctx = get_worker_ctx(request)` from Story 2's helper.
4. Start upstream pointed at `tools-pack/`. Hit `tools/list` — `document_search` appears.
5. Call it with sample headers + payload. Verify the result.

**Verify:** Tool returns expected output when invoked via `POST /mcp` with `X-Worker-Id` / `X-Worker-Data-Root` headers set. Code reviewer confirms no Flask `g` references remain.

---

## Story 4 — Port all 31 custom tools (3 days, parallelizable)

**Goal:** Repeat Story 3 for every tool. Tools fall into 7 batches; assign by category.

**Batches (each ~½ day):**
- Batch A: IRIS CCR + counterparty + credit limits + historical exposure + trade inventory + var contribution (6 tools)
- Batch B: EDGAR + Tavily IR + Tavily Yahoo Finance (5 tools)
- Batch C: Connectors — Outlook, Teams, Confluence, Jira, SharePoint, PowerBI (6 modules; each declares 5–7 tools)
- Batch D: DuckDB OLAP + SQL Select + msdoc tools (3 modules)
- Batch E: Python executor + visualisation + workflow tools (3 modules)
- Batch F: BM25 + fs_index + data transform + file_read + operational + upload (already done in Story 3, do the rest here)
- Batch G: Demo / fibonacci (1 tool — `studio_saad_fib.py`)

**Per tool checklist** (paste into PR description):
- [ ] Implementation copied to `tools-pack/impl/`
- [ ] Config copied to `tools-pack/configs/`, `"implementation"` path updated
- [ ] Flask `g` references removed; uses `get_worker_ctx(request)` instead
- [ ] Smoke test: call via `POST /mcp` and confirm output

**Verify:** All 31 tools appear in `tools/list`. Each has a smoke test in `tests/tools-pack/test_<tool>.py`.

---

## Story 5 — Move worker-path resolution into tools-pack (1 day)

**Goal:** Port `data_context.py` + `path_resolver.py` logic out of our fork into `tools-pack/lib/worker_paths.py`. Same API, no Flask dependency.

**Steps:**
1. Read `mcp-intelligence-agent/sajhamcpserver/sajha/data_context.py` and `path_resolver.py`.
2. Reimplement the public API (`get_data_layers`, `resolve_file`, `list_files`) inside `tools-pack/lib/worker_paths.py`, taking a dict of paths instead of reading Flask `g`.
3. Update any tool in `tools-pack/impl/` that imports from `sajha.data_context` to import from `tools_pack.lib.worker_paths` instead.

**Verify:** Imports resolve; pytest under `tests/tools-pack/test_worker_paths.py` exercises each function with a fake worker context dict.

---

## Story 6 — Adapt agent's SAJHA caller (1 day)

**Goal:** Update `agent/tools.py` to talk to upstream's MCP protocol shape (`X-API-Key` header, v2025-11-25 response unwrapping).

**Steps:**
1. In `_service_headers()`, change `headers['Authorization'] = _SAJHA_API_KEY` to `headers['X-API-Key'] = _SAJHA_API_KEY`. Drop the legacy `Authorization` form.
2. Update upstream API key creation: write or update `tools-pack/configs/apikeys.json` example (real values via env at runtime).
3. In `_call_sajha()`, detect a `StepResult` envelope (`{value, error, trace, ...}`) in the response and unwrap to legacy shape so the rest of `agent/` doesn't need to change.
4. Handle `{"isError": true, "content": [...]}` as a tool-level error (not a transport error).
5. Run the full agent end-to-end against upstream + tools-pack, with one simple tool call (e.g. `bm25_search`). Verify output matches what the agent expects.

**Verify:** Existing `tests/test_tools.py` passes against upstream + tools-pack. SSE streaming still works end-to-end in the chat UI.

---

## Story 7 — Multi-worker isolation e2e test (1 day) **[GATE]**

**Goal:** Prove that worker A cannot read worker B's files when both go through the new architecture.

**Steps:**
1. Set up two workers in workers.json: `w-test-a` and `w-test-b`. Each has a unique file in its `my_data/`.
2. Write a pytest at `tests/e2e/test_worker_isolation.py`:
   - Log in as user assigned to worker A. List `my_data/` — confirm only A's file shows.
   - List worker B's `my_data/` — confirm forbidden / empty.
   - Call `list_uploaded_files` via the agent — confirm only A's file in results.
   - Repeat as worker B.
3. Make this test a CI gate.

**Verify:** Test runs green. A run with worker isolation deliberately broken (e.g. swap `X-Worker-Data-Root` headers) makes the test fail — confirming it's a real check.

---

## Story 8 — Docker + deployment (1 day)

**Goal:** Update Docker setup so the upstream submodule and tools-pack are baked into the image and configured at startup.

**Steps:**
1. Update `Dockerfile` to copy `sajhamcpserver-upstream/` and `tools-pack/` into the image.
2. Update `supervisord.conf`: change the `[program:sajha]` command from `python run_sajha.py` to `python sajhamcpserver-upstream/run_server.py`, and set env `SAJHA_CONFIG_PLUGINS_DIR=/app/tools-pack`.
3. Update `docker-compose.local.yml` and `docker-compose.prod.yml` env vars as needed.
4. Add a `make build` / `make run` shortcut for local dev.

**Verify:** `docker compose -f docker-compose.local.yml up` brings up upstream + agent. Login + chat works.

---

## Story 9 — Update documentation (½ day)

**Goal:** Update every active doc that mentions our forked SAJHA.

**Steps:**
1. `CLAUDE.md` — update Architecture section: "SAJHA MCP Server (`sajhamcpserver-upstream/`) — upstream v5.0.0 pinned, 500 built-in tools + 31 from `tools-pack/`."
2. `LOCAL_DEV_SETUP.md` — update the run commands to use upstream's entry point.
3. `DOCS_INDEX.md` — add entries for the new `tools-pack/` if any docs end up there.
4. `handover/00_START_HERE.md` — note REQ-17 completion in the backlog/completed table.
5. `archive/INDEX.md` — add a new section: `archive/sajhamcpserver-v2.9.8-fork/` (the old fork, retired).

**Verify:** Every reader-facing doc reflects upstream as the SAJHA source of truth.

---

## Story 10 — Retire our embedded fork (½ day)

**Goal:** Move the old `sajhamcpserver/` to archive. Final cutover.

**Steps:**
1. Confirm nothing in the active tree still imports from `mcp-intelligence-agent/sajhamcpserver/` (use `grep -r "from sajha\." --include="*.py" agent/ agent_server.py` to check).
2. `git mv mcp-intelligence-agent/sajhamcpserver archive/sajhamcpserver-v2.9.8-fork`.
3. Update `archive/INDEX.md` with a section explaining what it was and why it's here.
4. Run the full test suite. Verify everything green.
5. Commit: "chore: retire embedded SAJHA fork; upstream + tools-pack now canonical".

**Verify:** Active tree has no `sajhamcpserver/` folder. CI green. App runs. The fork's history is preserved via `git mv`.

---

## Sequencing summary

```
Story 0 (Spike) ──► gates everything below

Story 1 (Submodule)  ─┐
Story 2 (Scaffold)   ─┼─► Story 3 (Port one tool) ─► Story 4 (Port all) ─┐
Story 5 (Worker paths)┘                                                  │
                                                                         ▼
Story 6 (Agent caller) ──────────────────────────────────────────────► Story 7 (Isolation gate)
                                                                         │
                                                                         ▼
                                                            Story 8 (Docker) ──► Story 9 (Docs) ──► Story 10 (Retire fork)
```

Stories 1–2 are independent and can run in parallel with Story 0. Story 5 can also run in parallel with Stories 3–4. Story 7 is the merge gate — nothing ships without it.

---

## Definition of Done (overall REQ-17)

- [ ] Story 0 spike passed.
- [ ] All 10 stories merged.
- [ ] CI green on the cutover branch.
- [ ] Story 7 isolation test gates the merge.
- [ ] Old `sajhamcpserver/` lives only in `archive/`.
- [ ] Production deploy of cutover branch passes smoke tests for 48 hours.
