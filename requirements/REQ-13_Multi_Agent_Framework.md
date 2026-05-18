# SAJHA Intelligence Platform

> **Source:** Converted from `REQ-13_Multi_Agent_Framework.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

SAJHA Intelligence Platform

**REQ-13: Multi-Agent Framework & Middleware Hardening**

**Status:** Framework Implemented — verified 2026-05-17

> **Verification (2026-05-17):** Sub-agent executor is real and wired:
> - `agent/sub_agent_executor.py` — `SubAgentExecutor` class, two-pool threading (4 scheduler + 8 exec threads). Real implementation, not a stub.
> - `agent/sub_agent_tool.py` — `task()` tool exposed to the agent.
> - `agent/workflow_parser.py` — YAML frontmatter parser for `agent_mode: multi` workflows.
> - Middleware hardening: 6 of the planned 9 middlewares wired into `create_agent_for_worker` (DanglingToolCall, Summarisation, MessageTrimmer, LoopDetection, ToolErrorHandling + optional SubagentLimit). Three more (Retry, TokenBudget, Audit) are coded but not added to the default stack — see REQ-14 below for that work.
> - **What remains for full REQ-13 closure:** demonstrably running multi-agent workflows with `agent_mode: multi` in `data/workers/*/workflows/`. Framework is ready; production usage evidence is missing.

**Version:** 2.0 — Final

**Date:** 2026-04-05

**Branch:** feature/multi-agent (off main, do NOT merge until full UAT passes)

**Depends On:** None — all changes are additive; workers default to agent_mode: "single"

**Author:** SAJHA Engineering

Patterns adapted from ByteDance DeerFlow 2.0 (MIT Licence, 50K+ stars)

**1. Background**

**1.1 Current Architecture**

The platform runs a single LangGraph ReAct agent per user request. One reasoning loop, one context window, tools called sequentially or batched within a single LangGraph step.

> User query
>
> → create_agent_for_worker(system_prompt, tools)
>
> → ctx_token = \_worker_ctx.set({\*\*worker, 'user_id': ...})
>
> → agent_instance.astream_events(inp, config, version='v2')
>
> → SSE stream: text, tool_start/end, usage, canvas, context_gauge
>
> → \[DONE\]

Current middleware chain: SummarisationMiddleware() (180K token trigger) → MessageTrimmer() (800K char hard limit).

**1.2 Three Limitations**

- **No parallel specialisation.** A "full picture on Goldman Sachs" query calls 6+ tools serially. Each result accumulates in one context window even when results are fully independent — wasting tokens and latency.

- **No safety rails.** Agent loops (same tool + same args repeated) burn 5–10K tokens per iteration. Uncaught tool exceptions kill the entire run. Orphaned tool_calls from summarisation cause Anthropic API format errors.

- **No user-controlled orchestration.** Users cannot define repeatable multi-step agent pipelines for structured analysis processes. Every query starts from scratch with no reusable execution plan.

**1.3 What DeerFlow 2.0 Provides**

DeerFlow is a production harness that wraps LangGraph with:

- **Sub-agent execution via task() tool** — the lead agent spawns specialised sub-agents dynamically from its own reasoning. Multiple task() calls in one LangGraph step run concurrently in a two-pool ThreadPoolExecutor.

- **Middleware stack** — LoopDetectionMiddleware, ToolErrorHandlingMiddleware, DanglingToolCallMiddleware — production safety rails validated at scale.

- **General-purpose sub-agents** — sub-agents are not pre-configured roles. They are clones of the lead agent with a focused task prompt. The lead agent decides decomposition at reasoning time.

**1.4 Integration Philosophy**

We do NOT replace our architecture with DeerFlow. We borrow specific patterns and adapt them to our multi-tenant, worker-scoped, RBAC-controlled platform.

|  |  |  |
|----|----|----|
| **Aspect** | **DeerFlow** | **Our Platform** |
| **Users** | Single-user, local | Multi-tenant, multi-worker, RBAC |
| **Config** | config.yaml | workers.json |
| **Tools** | Built-in Python/bash | 74+ SAJHA MCP tools via HTTP |
| **Context** | runtime.context | \_worker_ctx ContextVar + X-Worker headers |
| **Orchestration** | Lead agent reasons freely | Lead agent reasons freely OR follows user workflow |
| **Sub-agent roles** | Fixed: researcher, coder, reporter | Dynamic — lead agent defines tasks at runtime |

Key difference from DeerFlow's original design: DeerFlow pre-defines sub-agent types in code. We make sub-agents fully dynamic — the lead agent writes the task prompt at reasoning time. Users can optionally supply a workflow file to control decomposition, tools, and execution order at runtime, without any admin pre-configuration.

**2. Architecture Overview**

**2.1 Two Execution Modes per Multi-Agent Worker**

- **Freestyle mode** — no workflow attached. The lead agent receives the user's query and reasons about whether and how to decompose it. For simple queries it answers directly. For complex queries it calls task() with sub-task decomposition it determines is appropriate. This is the pure DeerFlow pattern.

- **Workflow-guided mode** — user attaches a workflow file from my_workflows or verified_workflows. The lead agent reads the workflow's YAML frontmatter (agents, task prompts, tool allowlists, execution order) and becomes a faithful executor of the plan rather than a free reasoner.

Both modes use the same task() tool and SubAgentExecutor infrastructure. The difference is whether the lead agent generates the decomposition or reads it from a file.

**2.2 Runtime Flow**

> User sends query \[+ optional: workflow file from my_workflows / verified_workflows\]
>
> │
>
> ▼
>
> agent_server.py
>
> worker = resolve_worker_for_user()
>
> agent_mode = worker.get('agent_mode', 'single')
>
> if agent_mode == 'single':
>
> ── Standard single-agent flow (unchanged) ───────────────
>
> if agent_mode == 'multi':
>
> inject task() tool into lead agent's tool list
>
> │
>
> ▼
>
> Lead agent runs (create_agent_for_worker + full middleware chain)
>
> │
>
> ├─ No workflow → FREESTYLE
>
> │ Calls: task("Get Goldman CCR data from IRIS")
>
> │ task("Get Goldman EDGAR + news") ← parallel
>
> │ task("Search OSFI docs for Goldman") ← parallel
>
> │
>
> └─ Workflow attached → WORKFLOW-GUIDED
>
> Lead reads frontmatter: agents\[\], order, tools\[\]
>
> Calls task(agents\[order=1\]) × N in parallel
>
> Waits → Calls task(agents\[order=2\], context=results) × M
>
> Each task() call → SubAgentExecutor.execute_async()
>
> → scheduler_pool thread → execution_pool thread → asyncio.run()
>
> → \_worker_ctx.set(parent_ctx) ← same worker + data paths
>
> → create_agent_for_worker(prompt, filtered_tools, checkpointer=None)
>
> → result string (truncated to max_result_chars)
>
> → SSE: task_started / task_running / task_completed / task_failed
>
> Lead agent receives all results → synthesises final answer

**2.3 Sub-Agent Cloning Mechanism**

Sub-agents are not a separate agent type. They are ephemeral instances of create_agent_for_worker() with:

- Same system prompt as the lead agent (worker's configured prompt)

- Same or filtered tool set (full in freestyle; workflow-specified subset in guided mode)

- **Same worker context** — \_worker_ctx propagated before asyncio.run() so every SAJHA call carries identical X-Worker-Id, X-Worker-Data-Root, X-Worker-My-Data-Root headers

- No checkpointer — ephemeral, no persistence. Only the lead agent checkpoints.

- task() removed from tool list — prevents recursive sub-agent spawning

> \# Inside SubAgentExecutor.\_run_in_executor()
>
> ctx_token = \_worker_ctx.set(self.\_parent_worker_ctx) \# inherit worker data scope
>
> \# asyncio.run() copies calling context → sub-agent inherits \_worker_ctx
>
> asyncio.run(self.\_aexecute(prompt, task_id))

**3. Component 1 — Middleware Stack Hardening**

These three middlewares improve all workers regardless of agent mode. They slot into the existing middleware chain in create_agent_for_worker().

**3.1 Updated Middleware Chain**

**File:** agent/agent.py — create_agent_for_worker()

> mw = \[
>
> DanglingToolCallMiddleware(), \# 1. Fix orphaned tool_calls before model call
>
> SummarisationMiddleware(), \# 2. Compress long conversations
>
> MessageTrimmer(), \# 3. Hard char-limit fallback
>
> \]
>
> if extra_middleware:
>
> mw.extend(extra_middleware) \# SubagentLimitMiddleware for multi-agent workers
>
> mw += \[
>
> LoopDetectionMiddleware(), \# 4. Detect loops after model response
>
> ToolErrorHandlingMiddleware(), \# 5. Catch tool exceptions, continue gracefully
>
> \]

**3.2 DanglingToolCallMiddleware**

**File:** agent/middlewares/dangling_tool_call.py (~110 lines) Hook: wrap_model_call / awrap_model_call

**Problem:** SummarisationMiddleware compresses old messages. MessageTrimmer drops messages when context is full. Both can orphan AIMessage.tool_calls — the model sees a tool call with no corresponding ToolMessage result and throws an Anthropic API format error or hallucinates.

**Fix:** Before each model call, scan all messages. For every AIMessage.tool_call.id that has no matching ToolMessage, inject a synthetic ToolMessage(content="\[interrupted\]", status="error") immediately after it.

**3.3 LoopDetectionMiddleware**

**File:** agent/middlewares/loop_detection.py (~240 lines) Hook: after_model / aafter_model

**Problem:** Agent calls the same tool with identical arguments repeatedly — observed with EDGAR tools. Each repeat burns 5–10K tokens.

**Fix:** MD5-hash the sorted (tool_name, args) pairs from the model response. Track hashes in a per-thread sliding window (size 20).

- **warn_threshold (default 3):** embed a \[LOOP DETECTED\] warning in the AIMessage content

- **hard_limit (default 5):** strip all tool_calls from the AIMessage, force text-only response

Why embed in AIMessage rather than inject HumanMessage: Anthropic's API rejects mid-conversation SystemMessages. Embedding the warning in the AIMessage content is simpler and equally effective as DeerFlow's HumanMessage injection approach (PR \#1299).

**3.4 ToolErrorHandlingMiddleware**

**File:** agent/middlewares/tool_error_handling.py (~65 lines) Hook: wrap_tool_call / awrap_tool_call

**Problem:** Uncaught tool exceptions (SAJHA timeouts, DuckDB errors, PDF parse failures) propagate through LangGraph and kill the entire agent run.

**Fix:** Wrap every tool call in try/except. On exception → return ToolMessage(content="Error: Tool X failed: Y. Continue with available context.", status="error"). Re-raise GraphBubbleUp (LangGraph's HITL interrupt signal) before the general catch.

**3.5 SubagentLimitMiddleware**

**File:** agent/middlewares/subagent_limit.py (~75 lines) Hook: after_model — multi-agent workers only

**Problem:** The lead agent may generate more parallel task() calls than the thread pool can handle.

**Fix:** After the model response, count task() tool_calls. If count \> max_concurrent_subagents, keep first N, drop the rest. N clamped to \[2, 4\].

**4. Component 2 — Dynamic Multi-Agent Execution**

**4.1 Sub-Agent Configuration**

Sub-agents have no pre-defined schema in workers.json. They are dynamically constructed at runtime by the lead agent or by a workflow file. The only worker-level config is:

> {
>
> "worker_id": "w-market-risk",
>
> "agent_mode": "multi",
>
> "max_concurrent_subagents": 3
>
> }

That is the entire workers.json change. No sub_agent_roles array. No admin-defined role configurations.

**4.2 SubAgentExecutor**

**File:** agent/sub_agent_executor.py (~300 lines)

Two-pool architecture (DeerFlow pattern). Threads not asyncio.gather — avoids nested async deadlock in our async LangGraph environment.

> \_scheduler_pool (4 threads) — submits to executor, enforces timeout
>
> \_execution_pool (8 threads) — runs asyncio.run(agent.astream_events(...))

Key parameters per sub-agent execution (passed dynamically, not from config):

- prompt — the specific task instruction (written by lead agent or workflow)

- tool_filter — optional glob patterns (from workflow; None in freestyle = all tools)

- max_result_chars — default 8000, truncates result before returning to lead agent

- timeout_seconds — default 120

- task_id — SSE event correlation and registry lookup

Global task registry: In-memory dict (task_id → {status, result, error, ai_messages, started_at}). Cleared on server restart — callers receive status="not_found" and return immediately.

**4.3 task() Tool**

**File:** agent/sub_agent_tool.py

> @tool
>
> async def task(
>
> description: str, \# 3-5 word label for the progress card UI
>
> prompt: str, \# detailed sub-task instruction
>
> tool_call_id: Annotated\[str, InjectedToolCallId\],
>
> tools: list\[str\] \| None = None, \# glob patterns e.g. \["iris\_\*", "edgar\_\*"\]
>
> max_turns: int = 20,
>
> timeout_seconds: int = 120,
>
> max_result_chars: int = 8000,
>
> ) -\> str:

tools is optional. None (freestyle) = full worker tool list minus task() itself. Provided (workflow-guided) = filtered via fnmatch.

Execution flow:

- Build filtered tool list (or full list if tools=None)

- Create SubAgentExecutor with prompt, filtered tools, parent \_worker_ctx

- executor.execute_async(prompt, tool_filter, task_id)

- Emit task_started SSE event via get_stream_writer()

- Poll every 5s — forward ai_messages as task_running events

- On terminal status → emit task_completed / task_failed / task_timed_out

- Return result string to lead agent

SSE event schema:

> {"type": "task_started", "task_id": "...", "description": "CCR exposure lookup"}
>
> {"type": "task_running", "task_id": "...", "name": "...", "message": {...}}
>
> {"type": "task_completed", "task_id": "...", "name": "..."}
>
> {"type": "task_failed", "task_id": "...", "error": "..."}
>
> {"type": "task_timed_out", "task_id": "...", "error": "..."}

**4.4 Agent Mode Fork in agent_server.py**

> agent_mode = worker.get('agent_mode', 'single')
>
> if agent_mode == 'multi':
>
> from agent.sub_agent_tool import create_task_tool
>
> from agent.middlewares import SubagentLimitMiddleware
>
> max_concurrent = worker.get('max_concurrent_subagents', 3)
>
> task_tool = create_task_tool(
>
> parent_tools=tools,
>
> parent_worker_ctx={\*\*worker, 'user_id': payload\['user_id'\]},
>
> llm=llm,
>
> create_agent_fn=create_agent_for_worker,
>
> )
>
> agent_instance = create_agent_for_worker(
>
> system_prompt,
>
> tools + \[task_tool\],
>
> extra_middleware=\[SubagentLimitMiddleware(max_concurrent=max_concurrent)\],
>
> )
>
> else:
>
> agent_instance = create_agent_for_worker(system_prompt, tools)

**5. Component 3 — Workflow-Guided Orchestration**

**5.1 Overview**

Users can attach a workflow file from my_workflows or verified_workflows when sending a query. The workflow's YAML frontmatter defines the orchestration plan — what sub-agents to spawn, what tools each may use, and what execution order to follow. The lead agent reads this plan and executes it faithfully rather than reasoning freely.

This gives users repeatable, structured, version-controlled agent pipelines without any admin configuration.

**5.2 Workflow File Format**

Workflow files use YAML frontmatter embedded in standard markdown. The existing .md workflow format is extended with a multi-agent section.

> ---
>
> name: Goldman Sachs Full Picture
>
> description: Comprehensive counterparty analysis — CCR, market intel, regulatory
>
> agent_mode: multi \# tells lead agent to use workflow-guided execution
>
> agents:
>
> \- id: ccr
>
> description: "CCR exposure and limits"
>
> task: \>
>
> Get Goldman Sachs counterparty exposure, credit limits, VaR contribution,
>
> and limit breaches from IRIS. Return structured table: net MTM, limit util %.
>
> tools: \[iris\_\*, get_counterparty\_\*, get_trade\_\*, get_credit\_\*, get_var\_\*\]
>
> order: 1
>
> timeout_seconds: 120
>
> max_result_chars: 6000
>
> \- id: market
>
> description: "SEC filings and market data"
>
> task: \>
>
> Get Goldman Sachs latest 10-K/10-Q summary from EDGAR, earnings highlights,
>
> and stock performance last 30 days.
>
> tools: \[edgar\_\*, tavily\_\*, ir\_\*\]
>
> order: 1
>
> timeout_seconds: 90
>
> max_result_chars: 5000
>
> \- id: regulatory
>
> description: "OSFI regulatory guidance"
>
> task: \>
>
> Given Goldman Sachs net MTM exposure is {ccr.result_summary},
>
> search OSFI guidance docs for CCR requirements and recent advisories.
>
> tools: \[search_documents, document_search, osfi\_\*\]
>
> order: 2
>
> depends_on: \[ccr\]
>
> timeout_seconds: 60
>
> max_result_chars: 4000
>
> ---

**5.3 Frontmatter Fields**

|  |  |  |
|----|----|----|
| **Field** | **Required** | **Description** |
| agent_mode: multi | Yes | Signals to lead agent that this is a multi-agent workflow |
| agents\[\] | Yes | List of sub-agent definitions |
| agents\[\].id | Yes | Unique ID within this workflow (used in depends_on) |
| agents\[\].description | Yes | Short label shown in the progress card UI |
| agents\[\].task | Yes | Full task prompt sent to the sub-agent |
| agents\[\].tools | No | Glob patterns for tool allowlist. Omit = full tool set |
| agents\[\].order | No | Execution order (default 1). Same order value = parallel |
| agents\[\].depends_on | No | Agent IDs whose results are injected as {id.result_summary} |
| agents\[\].timeout_seconds | No | Default 120 |
| agents\[\].max_result_chars | No | Default 8000 |

**5.4 Execution Order and Dependencies**

Agents with the same order value run in parallel. Agents with a higher order run after all lower-order agents complete. depends_on enables result injection — the completed result is substituted into {id.result_summary} placeholders in the task string before spawning.

> order=1: \[ccr, market\] → run in parallel
>
> order=2: \[regulatory\] → waits for ccr (its depends_on), then spawns
>
> regulatory.task gets ccr result injected at {ccr.result_summary}

This enables sequential reasoning pipelines where later agents need context from earlier ones — not possible in pure freestyle mode where all task() calls in one LangGraph step are parallel.

**5.5 Lead Agent Behaviour in Workflow-Guided Mode**

The system prompt addendum for multi-agent workers includes workflow parsing instructions. When the lead agent detects a workflow file in the conversation context, it:

- Reads the YAML frontmatter from the file

- Validates agent_mode: multi is set

- Groups agents by order

- For order=1: calls all agents' task() in parallel (one LangGraph step)

- Waits for completion

- For each subsequent order: resolves depends_on references, substitutes result summaries, calls task() for that batch

- After all agents complete: synthesises all results into the final answer

Without a workflow file attached: lead agent reasons freely about decomposition (freestyle mode).

**5.6 Verified Workflows vs My Workflows**

|  |  |  |
|----|----|----|
|  | **verified_workflows** | **my_workflows** |
| **Created by** | Admin curates / user requests promotion | User creates directly |
| **Visible to** | All users of that worker | Creating user only |
| **Trust level** | Production-ready, reviewed | Experimental, in-progress |
| **Promotion path** | Admin approves and moves to verified | — |
| **Typical use** | Standard analysis pipelines, quarterly reports | Personal experiments, domain-specific variants |

Users create orchestration plans in my_workflows, iterate on them, and when satisfied request admin promotion to verified_workflows so the whole team benefits.

**6. Component 4 — System Prompt Addendum**

**File:** agent/prompt.py — \_augment_prompt()

When agent_mode="multi", the following is appended to the worker's system prompt alongside the existing Python addendum:

> === MULTI-AGENT ORCHESTRATION ===
>
> You have access to a \`task\` tool that spawns specialised sub-agents in parallel.
>
> Each sub-agent is a clone of you with a focused task prompt and access to the
>
> same worker data and tools (or a tool subset you specify).
>
> FREESTYLE MODE (no workflow file in context):
>
> Use task() when:
>
> \- The query requires 3+ independent data sources
>
> \- "Full picture", "comprehensive analysis", "complete review" requests
>
> \- Independent sub-tasks that can run in parallel
>
> Do NOT use task() for:
>
> \- Simple factual questions answerable with 1-2 tools
>
> \- Follow-up questions in an ongoing conversation
>
> \- Queries already focused on one data source
>
> How to call task():
>
> task(description="CCR exposure lookup",
>
> prompt="Get Goldman Sachs counterparty exposure, credit limits and VaR
>
> from IRIS. Return structured table with net MTM, limit util %.",
>
> tools=\["iris\_\*", "get_counterparty\_\*"\]) \# optional — omit for all tools
>
> Multiple task() calls in one response run in parallel.
>
> Sub-agents cannot call task() — no recursion.
>
> WORKFLOW-GUIDED MODE (workflow file attached with agent_mode: multi in frontmatter):
>
> Read the YAML frontmatter from the workflow file.
>
> Execute agents\[\] in order, respecting order and depends_on fields.
>
> Substitute {id.result_summary} placeholders with completed agent results.
>
> Do not deviate from the workflow plan unless an agent fails.
>
> After all agents complete, synthesise results into the final answer.

**7. Component 5 — Admin Panel UI**

**7.1 Worker Configuration Changes**

**File:** public/admin.html

The only new UI is a two-field addition to the Worker Configuration panel. No role editor. No tool allowlist configurator. The admin's only decision is on or off, plus optionally the concurrency limit.

> \<!-- Agent Mode dropdown (added after System Prompt textarea) --\>
>
> \<div class="form-row" style="max-width:900px;margin-top:20px"\>
>
> \<label class="form-label"\>Agent Mode\</label\>
>
> \<select class="form-input" id="wc-agent-mode" style="max-width:280px"\>
>
> \<option value="single"\>Single Agent (default)\</option\>
>
> \<option value="multi"\>Multi Agent (workflow-capable)\</option\>
>
> \</select\>
>
> \</div\>
>
> \<!-- Concurrency slider (shown only when multi is selected) --\>
>
> \<div id="wc-subagent-concurrency" style="display:none;margin-top:12px"\>
>
> \<label class="form-label"\>Max Concurrent Sub-Agents\</label\>
>
> \<input type="range" id="wc-max-subagents" min="2" max="4" value="3"
>
> oninput="document.getElementById('wc-max-subagents-val').textContent=this.value"\>
>
> \<span id="wc-max-subagents-val"\>3\</span\>
>
> \</div\>

**7.2 WorkerUpdateRequest Extension**

**File:** agent_server.py

> class WorkerUpdateRequest(BaseModel):
>
> name: Optional\[str\] = None
>
> description: Optional\[str\] = None
>
> system_prompt: Optional\[str\] = None
>
> enabled_tools: Optional\[list\] = None
>
> enabled: Optional\[bool\] = None
>
> agent_mode: Optional\[str\] = None \# "single" \| "multi"
>
> max_concurrent_subagents: Optional\[int\] = None \# clamped to \[2, 4\]
>
> \# sub_agent_roles is NOT added — roles live in workflow files, not workers.json

**7.3 Admin JS Load/Save**

> function loadWorkerConfig() {
>
> // ...existing fields...
>
> var mode = \_currentWorker.agent_mode \|\| 'single';
>
> document.getElementById('wc-agent-mode').value = mode;
>
> document.getElementById('wc-max-subagents').value =
>
> \_currentWorker.max_concurrent_subagents \|\| 3;
>
> document.getElementById('wc-subagent-concurrency').style.display =
>
> mode === 'multi' ? '' : 'none';
>
> }
>
> function saveWorkerConfig() {
>
> var body = {
>
> // ...existing fields...
>
> agent_mode: document.getElementById('wc-agent-mode').value,
>
> max_concurrent_subagents: parseInt(document.getElementById('wc-max-subagents').value),
>
> };
>
> // ...existing fetch logic...
>
> }

**8. Component 6 — Frontend Sub-Agent Progress Cards**

**File:** public/mcp-agent.html

**8.1 CSS**

> .subagent-cards {
>
> display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px;
>
> }
>
> .subagent-card {
>
> background: rgba(99, 102, 241, 0.08);
>
> border: 1px solid rgba(99, 102, 241, 0.25);
>
> border-left: 3px solid \#6366f1;
>
> border-radius: 0 6px 6px 0;
>
> padding: 8px 12px;
>
> font-size: 12px;
>
> display: flex; align-items: center; gap: 10px;
>
> animation: slideInSub 0.2s ease;
>
> }
>
> .subagent-card.done { border-left-color: \#22c55e; background: rgba(34,197,94,0.06); }
>
> .subagent-card.error { border-left-color: \#ef4444; background: rgba(239,68,68,0.06); }
>
> .subagent-card.timeout { border-left-color: \#f59e0b; background: rgba(245,158,11,0.06); }
>
> @keyframes slideInSub {
>
> from { opacity: 0; transform: translateX(-6px); }
>
> to { opacity: 1; transform: translateX(0); }
>
> }

**8.2 JavaScript — SSE Event Handler**

> var \_subAgentCards = {};
>
> function showSubAgentCard(taskId, description, name) {
>
> if (!\_currentAgentMsg) return;
>
> var container = \_currentAgentMsg.querySelector('.subagent-cards');
>
> if (!container) {
>
> container = document.createElement('div');
>
> container.className = 'subagent-cards';
>
> var toolCards = \_currentAgentMsg.querySelector('.tool-cards');
>
> \_currentAgentMsg.insertBefore(container, toolCards \|\| null);
>
> }
>
> var card = document.createElement('div');
>
> card.className = 'subagent-card';
>
> card.id = 'subagent-card-' + taskId;
>
> card.innerHTML =
>
> '\<div class="subagent-spinner"\>\</div\>' +
>
> '\<span class="subagent-label"\>' + esc(description \|\| name) + '\</span\>' +
>
> '\<span class="subagent-status" style="margin-left:auto"\>working…\</span\>';
>
> container.appendChild(card);
>
> \_subAgentCards\[taskId\] = card;
>
> }
>
> // SSE event switch additions:
>
> else if (type === 'task_started') { showSubAgentCard(evt.task_id, evt.description, evt.name); }
>
> else if (type === 'task_running') { updateSubAgentCard(evt.task_id, 'running', null); }
>
> else if (type === 'task_completed') { updateSubAgentCard(evt.task_id, 'done'); }
>
> else if (type === 'task_failed') { updateSubAgentCard(evt.task_id, 'error', evt.error); }
>
> else if (type === 'task_timed_out') { updateSubAgentCard(evt.task_id, 'timeout'); }

**9. Implementation Stories**

**Phase 0 — Branch**

|        |                                            |
|--------|--------------------------------------------|
| **ID** | **Description**                            |
| **S0** | Create feature/multi-agent branch off main |

**Phase 1 — Middleware Hardening (ships immediately to all workers)**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S1** | Create agent/middlewares/ package | Small |
| **S2** | DanglingToolCallMiddleware | Small |
| **S3** | LoopDetectionMiddleware | Medium |
| **S4** | ToolErrorHandlingMiddleware | Small |
| **S5** | SubagentLimitMiddleware | Small |
| **S6** | Integrate all 4 into create_agent_for_worker() with extra_middleware param | Small |
| **S7** | Regression: all existing UAT tests pass with new middleware chain | QA |

**Phase 2 — Multi-Agent Core (freestyle mode)**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S8** | SubAgentExecutor — two-pool ThreadPoolExecutor, \_worker_ctx propagation, task registry | Large |
| **S9** | task() tool — dynamic prompt, optional tool filter, SSE events, result truncation | Large |
| **S10** | Agent mode fork in agent_server.py | Small |
| **S11** | SSE forwarding for on_custom_event → sub-agent events | Small |
| **S12** | Multi-agent system prompt addendum in agent/prompt.py | Small |
| **S13** | Frontend: sub-agent progress cards CSS + JS in mcp-agent.html | Medium |
| **S14** | Admin UI: Agent Mode dropdown + concurrency slider in admin.html | Small |
| **S15** | WorkerUpdateRequest extension in agent_server.py | Small |
| **S16** | E2E test: freestyle multi-agent query on w-market-risk | QA |

**Phase 3 — Workflow-Guided Mode**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S17** | Workflow frontmatter parser (agents\[\], order, depends_on, tools\[\]) | Medium |
| **S18** | Lead agent workflow execution logic (ordered batches, result injection) | Large |
| **S19** | System prompt addendum: workflow-guided mode instructions | Small |
| **S20** | Seed w-market-risk with 2 example verified workflows (Goldman full picture, Monthly CCR report) | Medium |
| **S21** | E2E test: workflow-guided run — correct agent order, dependencies resolved, results injected | QA |

**Phase 4 — UAT & Merge**

|  |  |  |
|----|----|----|
| **ID** | **Description** | **Effort** |
| **S22** | Full regression: all existing UAT Phase 1–4 tests on feature branch | QA |
| **S23** | Multi-agent UAT suite (MA-\* tests) | QA |
| **S24** | Workflow-guided UAT suite (WF-\* tests) | QA |
| **S25** | Performance benchmarks: latency, thread count stability | QA |
| **S26** | PR to main with squash merge | DevOps |

**10. QA Test Plan**

**10.1 Middleware Tests (All Workers)**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **MW-01** | Agent calls same tool 3× identical args | Warning embedded in AIMessage, loop counter noted |
| **MW-02** | Agent calls same tool 5× identical args | tool_calls stripped, forced text-only response |
| **MW-03** | Two threads: same tool calls | Independent loop counters per thread_id |
| **MW-04** | Tool throws RuntimeError | Error ToolMessage returned, agent continues |
| **MW-05** | SAJHA returns HTTP 500 (simulated) | Error ToolMessage, agent notes gap and continues |
| **MW-06** | Summarisation creates orphaned tool_calls | Synthetic ToolMessages injected before next model call |
| **MW-07** | All existing UAT tests pass with new middlewares | Zero regressions |

**10.2 Multi-Agent Tests — Freestyle Mode**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **MA-01** | Worker agent_mode=single | No task tool in tool list; identical behaviour to today |
| **MA-02** | Worker agent_mode=multi | task tool present in tool list |
| **MA-03** | Simple query on multi-agent worker | Lead answers directly, no task() called |
| **MA-04** | "Full picture on Deutsche Bank" | 2–3 task() calls; SSE shows task_started events; synthesis follows |
| **MA-05** | task() with tools=\["iris\_\*"\] | Sub-agent tool list filtered to iris\_\* tools only |
| **MA-06** | task() with tools=None | Sub-agent gets full worker tool list minus task() |
| **MA-07** | Sub-agent timeout | task_timed_out SSE event; lead agent gets error string and continues |
| **MA-08** | Sub-agent SAJHA tool fails | ToolErrorHandlingMiddleware catches it; sub-agent returns partial result |
| **MA-09** | Sub-agent tries to call task() | task() not in sub-agent tool list; recursion prevented |
| **MA-10** | 5 task() calls generated, max=3 | SubagentLimitMiddleware keeps first 3, drops last 2 |
| **MA-11** | Worker context in sub-agent | Sub-agent SAJHA calls carry same X-Worker-Id as lead agent |
| **MA-12** | Server restart mid-run | Polling task() gets not_found → returns error string immediately |

**10.3 Workflow-Guided Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **WF-01** | Workflow file attached with agent_mode: multi | Lead agent reads frontmatter, executes in order |
| **WF-02** | Two agents at order=1 | Both task() calls in same LangGraph step, run in parallel |
| **WF-03** | Agent at order=2, depends_on order=1 agent | Waits for order=1 completion; result injected into task prompt |
| **WF-04** | {id.result_summary} placeholder | Resolved to first 500 chars of referenced agent result |
| **WF-05** | Workflow agent with tools specified | Only matching tools available to that sub-agent |
| **WF-06** | Workflow agent with no tools specified | Full worker tool list available to that sub-agent |
| **WF-07** | Workflow from my_workflows | Executes correctly; private to creating user |
| **WF-08** | Workflow from verified_workflows | Executes correctly; visible to all users of that worker |
| **WF-09** | Workflow without agent_mode: multi | Lead agent treats as regular workflow file, no sub-agents spawned |
| **WF-10** | Agent fails mid-workflow | Subsequent order agents get error string as context, execution continues |

**10.4 Admin UI Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **UI-01** | Agent Mode dropdown visible in Worker Config | Single Agent / Multi Agent options |
| **UI-02** | Selecting Multi Agent shows concurrency slider | Slider appears, default 3 |
| **UI-03** | Selecting Single Agent hides concurrency slider | Slider hidden |
| **UI-04** | Save worker with agent_mode=multi | workers.json updated: agent_mode, max_concurrent_subagents |
| **UI-05** | Reload worker config | Dropdown and slider restore correctly |

**10.5 Frontend Tests**

|  |  |  |
|----|----|----|
| **ID** | **Test** | **Expected** |
| **FE-01** | task_started SSE event | Sub-agent progress card appears with spinner |
| **FE-02** | task_completed SSE event | Card icon changes to ✓, status "done" |
| **FE-03** | task_failed SSE event | Card turns red, shows error snippet |
| **FE-04** | task_timed_out SSE event | Card turns amber, shows "timed out" |
| **FE-05** | Multiple concurrent sub-agents | Multiple cards appear simultaneously |
| **FE-06** | Cards visible after synthesis | Cards remain visible but compact after final answer |

**11. Performance Considerations**

**11.1 LLM Cost**

|  |  |  |  |
|----|----|----|----|
| **Scenario** | **Single Agent** | **Multi Agent Freestyle (3 subs)** | **Workflow-Guided (3 subs, ordered)** |
| **LLM calls** | 1 lead (5–8 tool rounds) | 1 lead + 3 subs | 1 lead + 3 subs |
| **Sub-agent context** | — | Clean per sub-agent (~15K) | Clean per sub-agent (~15K) |
| **Lead synthesis input** | ~50K accumulated | ~10K + 3 result strings | ~10K + 3 strings + dep. context |
| **Estimated cost** | ~\$0.15 | ~\$0.30–0.40 | ~\$0.30–0.45 |
| **Latency** | 30–60s (serial) | 20–35s (parallel) | 20–35s (ph.1) + 15–20s (ph.2+) |

**11.2 Thread Pool Sizing**

Default: 4 scheduler + 8 executor threads. Handles 3–4 concurrent multi-agent queries × 3 sub-agents each. At multi-pod scale (REQ-12): background task registry needs Redis.

**11.3 Result Truncation**

Sub-agent results are truncated to max_result_chars (default 8000 per agent) before returning to the lead agent. Three sub-agents at 8000 chars each = 24K chars (~6K tokens) of synthesis input — well within context budget.

**12. File Summary**

|  |  |  |  |
|----|----|----|----|
| **File** | **Status** | **Lines** | **Component** |
| agent/middlewares/\_\_init\_\_.py | New | 20 | Middleware |
| agent/middlewares/dangling_tool_call.py | New | ~110 | Middleware |
| agent/middlewares/loop_detection.py | New | ~240 | Middleware |
| agent/middlewares/tool_error_handling.py | New | ~65 | Middleware |
| agent/middlewares/subagent_limit.py | New | ~75 | Multi-Agent |
| agent/sub_agent_executor.py | New | ~300 | Multi-Agent |
| agent/sub_agent_tool.py | New | ~180 | Multi-Agent |
| agent/workflow_parser.py | New | ~120 | Workflow-Guided |
| agent/agent.py | Modified | +20 | MW integration |
| agent/prompt.py | Modified | +40 | Multi-agent addendum |
| agent_server.py | Modified | +35 | Fork + SSE + Request model |
| public/admin.html | Modified | +50 | Agent Mode UI |
| public/mcp-agent.html | Modified | +80 | Sub-agent cards |
| **Total new** |  | **~1,110** | Zero new pip dependencies |
| **Total modified** |  | **~225** | All existing LangGraph / langchain APIs |

**Removed vs REQ-13 v1.0:** agent/sub_agent_config.py (roles not pre-configured), agent/memory/ package (deferred to REQ-14), sub-agent role editor UI in admin.html, sub_agent_roles array in workers.json — approximately 1,200 lines of role-management and memory code removed from scope.

**13. Out of Scope**

- Persistent cross-session memory — deferred to REQ-14

- Worker-to-worker communication — sub-agents are scoped to the same worker context; cross-worker delegation is a separate architectural decision

- Sub-agent token streaming — sub-agents return completed result strings, not token-by-token. Frontend shows progress cards, not live token stream from sub-agents

- Sub-agent checkpointing — ephemeral only; only the lead agent checkpoints

- Workflow promotion API — my_workflows → verified_workflows promotion is a manual admin file operation for now

- Docker sandbox isolation for sub-agents — python_executor.py subprocess is sufficient

- Redis task registry — in-memory is sufficient for single-pod deployment; Redis deferred to REQ-12 multi-pod work

**14. Dependencies on Other REQs**

|  |  |
|----|----|
| **REQ** | **Relationship** |
| **REQ-10 (Common Data)** | Sub-agents searching common_data works automatically — same X-Worker-Common-Root header |
| **REQ-12 (S3 / Multi-pod)** | Background task registry needs Redis at multi-pod scale |
| **REQ-14 (Memory)** | Persistent memory builds on this middleware chain; MemoryMiddleware slots in at position 4 |
| **REQ-07 (PostgreSQL)** | workers.json migration to PostgreSQL; agent_mode field migrates with it |
