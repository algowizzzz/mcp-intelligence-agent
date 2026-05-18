# MCP Intelligence Agent

> **Source:** Converted from `mcp-agent-trd-final.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

**MCP Intelligence Agent**

*Technical Reference Document*

LangGraph ReAct Backend · HTML/JS Frontend · SAJHA MCP Server · FastAPI · Final Edition

> LangGraph create_agent (LangChain v1.0) · ToolNode parallel execution · MemorySaver · FastAPI SSE streaming · HTML/JS frontend · SAJHA MCP Server · LangSmith observability
> **Industry-standard agentic architecture. LangGraph owns the reasoning loop. HTML owns the UI. SAJHA owns the data.**

|  |  |
|----|----|
| **Agent Framework** | LangChain v1.0 · create_agent · built on LangGraph v1.0 runtime |
| **Backend** | Python 3.10+ · FastAPI · uvicorn · httpx |
| **Frontend** | Pure HTML + CSS + Vanilla JS · single file · no framework · no build step |
| **MCP Server** | SAJHA v2.9.8 · github.com/ajsinha/sajhamcpserver · port 3002 |
| **LLM** | Claude Sonnet 4 · claude-sonnet-4-20250514 · langchain-anthropic |
| **Memory** | MemorySaver (dev) · SqliteSaver (production) · thread_id per session |
| **Observability** | LangSmith · full trace per query · tool lineage · cost per run |
| **Prepared By** | DeepLearnHQ Engineering |
| **Date** | March 30, 2026 |
| **Classification** | Confidential — Internal |

**Table of Contents**

| **01** | **System Overview** <br> *Purpose, three-layer architecture, and capability inventory* |
| --- | --- |

**1.1 Purpose**

The MCP Intelligence Agent is a financial risk intelligence tool that answers complex analyst queries by autonomously planning, executing multiple data tool calls in parallel, and synthesising a structured, sourced intelligence report. An analyst types a natural-language question — such as “Get me the full picture on RBC: exposure, trades, limits, and latest news” — and receives a complete report within 30 seconds, with every figure attributed to the data source that produced it.

**1.2 Three-Layer Architecture**

|                                                                       |
|-----------------------------------------------------------------------|
| **// Three-layer architecture**                                       |
| ┌──────────────────────────────────────────────────────────────────┐  |
| │ LAYER 1 — HTML FRONTEND (mcp-agent.html) │                          |
| │ Pure HTML + CSS + Vanilla JS · no framework · no build step │       |
| │ · Query panel, sample queries, Run / Cancel buttons │               |
| │ · SSE stream reader → renders thinking, tool cards, synthesis │     |
| │ · Three-tab UI: Execution Trace / Tool Calls / Intelligence Report│ |
| │ · Context meter, cost display, session restore, export bar │        |
| │ · POSTs to http://localhost:8000/api/agent/run │                    |
| └──────────────────────────────────────────────────────────────────┘  |
| │ SSE stream (text, tool_start, tool_end, usage, hitl, \[DONE\])      |
| ▼                                                                     |
| ┌──────────────────────────────────────────────────────────────────┐  |
| │ LAYER 2 — LANGGRAPH FASTAPI BACKEND (agent_server.py) │             |
| │ Python 3.10+ · FastAPI · LangChain v1.0 · LangGraph v1.0 runtime │  |
| │ · create_agent (LangChain v1.0) — THE ReAct orchestration loop │    |
| │ · @tool functions → callSajha() calls to SAJHA │                    |
| │ · MemorySaver checkpointer → state per thread_id │                  |
| │ · astream_events() → SSE stream to frontend │                       |
| │ · ANTHROPIC_API_KEY in .env — never reaches browser │               |
| │ · LangSmith tracing — full lineage per query │                      |
| │ · http://localhost:8000 │                                           |
| └──────────────────────────────────────────────────────────────────┘  |
| │ HTTP REST (callSajha)                                               |
| ▼                                                                     |
| ┌──────────────────────────────────────────────────────────────────┐  |
| │ LAYER 3 — SAJHA MCP SERVER (github.com/ajsinha/sajhamcpserver) │    |
| │ Python/Flask · port 3002 · 40+ tools · BaseMCPTool extension │      |
| │ · All 6 agent tools registered here │                               |
| │ · Tavily web search built-in · 5 internal tools to build │          |
| │ · Bearer token auth · RBAC per user · audit log (server.log) │      |
| └──────────────────────────────────────────────────────────────────┘  |

**1.3 Technology Stack**

|  |  |
|----|----|
| **Frontend** | Pure HTML + CSS + Vanilla JS · single file · Google Fonts CDN only · no npm · no build |
| **Agent Framework** | LangChain v1.0 create_agent · LangGraph v1.0 runtime · Python 3.10+ |
| **LLM** | langchain-anthropic · Claude Sonnet 4 (claude-sonnet-4-20250514) · streaming=True |
| **Backend** | FastAPI · uvicorn · httpx (SAJHA calls) · python-dotenv |
| **Memory** | MemorySaver (development) · SqliteSaver (production) · keyed by thread_id |
| **MCP Server** | SAJHA v2.9.8 · python-flask · port 3002 · BaseMCPTool extension pattern |
| **Observability** | LangSmith · full trace per query · tool call lineage · LLM cost breakdown |
| **Auth** | ANTHROPIC_API_KEY in FastAPI .env · SAJHA Bearer token in Python · RBAC user |

**1.4 Complete Capability Inventory**

|  |  |
|:--:|:--:|
| **Capability** | **Owner** |
| ReAct loop: Think → Plan → Act → Observe → Reflect → Synthesize | LangGraph create_agent |
| Parallel tool execution (all tool_calls in one AIMessage fire simultaneously) | LangGraph ToolNode |
| Human-in-the-Loop: pause mid-query for analyst clarification | LangGraph interrupt() + Command(resume=) |
| Retry / error handling on tool failure | LangGraph ToolNode error ToolMessage |
| Max iteration guard | LangGraph recursion_limit config |
| Conversation memory across turns in session | LangGraph MemorySaver (thread_id) |
| Auto-summarisation: compress history when context grows | LangGraph middleware or custom node |
| Streaming: LLM tokens appear word-by-word | FastAPI astream_events() → HTML SSE reader |
| Streaming: tool start / end events | FastAPI astream_events() → HTML SSE reader |
| User cancellation (Cancel button) | HTML \_activeReader.cancel() |
| Tool timeout 30s | httpx timeout in Python callSajha() |
| Graceful degradation: partial results on failure | HTML renderPartialResults() on error SSE |
| Source attribution: \[src:tool\] badges in report | System prompt + HTML renderWithAttribution() |
| Jump-to-tool on badge click with flash animation | HTML |
| PDF export via browser print dialog | HTML exportPDF() |
| Markdown export with data lineage section | HTML exportMarkdown() |
| Real token cost tracking (from API usage field) | HTML recordCost() from usage SSE event |
| Live USD cost display with breakdown tooltip | HTML updateCostDisplay() |
| Session persistence: thread_id + report in localStorage | HTML saveSession() / restoreSession() |
| Restore banner + Clear Session button | HTML |
| SAJHA auth: Bearer token + silent 401 re-auth | Python agent/tools.py \_call_sajha() |
| RBAC: risk_agent user with restricted tool list | SAJHA config/users.json |
| Audit log: every tool call in server.log | SAJHA automatic |
| Full observability: every LLM call and tool traced | LangSmith (LANGCHAIN_TRACING_V2=true) |
| API key security: never reaches the browser | FastAPI .env ANTHROPIC_API_KEY |
| Context meter: token estimate, cost, summary badge | HTML |
| Configurable thresholds: summN, maxIter, ctxLimit | HTML inputs → sent as params to backend |
| Three-tab UI: Trace / Tools / Intelligence Report | HTML |
| Tool bar with live tool chips | HTML (TOOL_UI_META) |
| Export bar: PDF + Markdown buttons | HTML |

| **02** | **LangGraph Agent Backend** <br> *create_agent, @tool wrappers, memory, and the project structure* |
| --- | --- |

**2.1 Python Dependencies**

|                                          |
|------------------------------------------|
| **// requirements.txt**                  |
| \# requirements.txt                      |
| langchain\>=1.0.0                        |
| langgraph\>=1.0.0                        |
| langchain-anthropic\>=0.3.0              |
| fastapi\>=0.115.0                        |
| uvicorn\>=0.32.0                         |
| httpx\>=0.27.0                           |
| python-dotenv\>=1.0.0                    |
| langgraph-checkpoint-sqlite\>=2.0.0      |
|                                          |
| \# Observability (strongly recommended): |
| langsmith\>=0.2.0                        |

**2.2 Project Structure**

|                                                         |
|---------------------------------------------------------|
| **// Project directory structure**                      |
| mcp-intelligence-agent/                                 |
| ├─ agent_server.py FastAPI app + SSE streaming endpoint |
| ├─ requirements.txt                                     |
| ├─ .env Secrets (never commit)                          |
| ├─ agent/                                               |
| │ ├─ \_\_init\_\_.py                                    |
| │ ├─ agent.py create_agent setup + checkpointer         |
| │ ├─ tools.py @tool decorated callSajha() wrappers      |
| │ └─ prompt.py SYSTEM_PROMPT string                     |
| ├─ sajhamcpserver/ SAJHA repo (cloned separately)       |
| ├─ mcp-agent.html HTML frontend (single file)           |
| └─ tests/                                               |
| ├─ test_tools.py Unit tests: each @tool function        |
| ├─ test_agent.py Integration: full agent runs           |
| └─ test_api.py FastAPI endpoint tests                   |

**2.3 Tool Wrappers (agent/tools.py)**

Each of the 6 tools is a @tool decorated async function. The docstring is injected into Claude's context so it knows when and how to use the tool. LangGraph's ToolNode calls these automatically and fires them in parallel when Claude emits multiple tool_calls in one message.

|  |
|----|
| **// agent/tools.py** |
| \# agent/tools.py |
| import httpx, os |
| from langchain_core.tools import tool |
|  |
| SAJHA_BASE = os.getenv('SAJHA_BASE_URL', 'http://localhost:3002') |
| \_sajha_token: str \| None = None |
|  |
| async def \_get_token() -\> str: |
| global \_sajha_token |
| if \_sajha_token: |
| return \_sajha_token |
| async with httpx.AsyncClient() as c: |
| r = await c.post(f'{SAJHA_BASE}/api/auth/login', |
| json={'user_id':'risk_agent','password':os.getenv('SAJHA_PASSWORD')}) |
| \_sajha_token = r.json()\['token'\] |
| return \_sajha_token |
|  |
| async def \_call_sajha(tool_name: str, args: dict) -\> dict: |
| global \_sajha_token |
| token = await \_get_token() |
| try: |
| async with httpx.AsyncClient(timeout=30.0) as c: |
| r = await c.post(f'{SAJHA_BASE}/api/tools/execute', |
| headers={'Authorization': f'Bearer {token}'}, |
| json={'tool': tool_name, 'arguments': args}) |
| if r.status_code == 401: \# token expired — silent re-auth |
| \_sajha_token = None |
| return await \_call_sajha(tool_name, args) |
| r.raise_for_status() |
| return r.json()\['result'\] |
| except httpx.TimeoutException: |
| return {'error': f'{tool_name} timed out after 30s'} |
|  |
| @tool |
| async def get_counterparty_exposure(counterparty: str, date: str = '') -\> dict: |
| '''Returns current notional, MTM, PFE and net exposure for a counterparty. |
| Use for: current risk snapshot, credit profile, collateral posted. |
| counterparty: name or LEI. date: YYYY-MM-DD, defaults to today. |
| ''' |
| return await \_call_sajha('get_counterparty_exposure', |
| {'counterparty': counterparty, 'date': date}) |
|  |
| @tool |
| async def get_trade_inventory(counterparty: str, asset_class: str = 'All') -\> dict: |
| '''Returns all open trade positions for a counterparty. |
| Use for: trade-level breakdown, notional by asset class, MTM per position. |
| ''' |
| return await \_call_sajha('get_trade_inventory', |
| {'counterparty': counterparty, 'asset_class': asset_class}) |
|  |
| @tool |
| async def get_credit_limits(counterparty: str) -\> dict: |
| '''Returns approved credit limits and current utilization. |
| Use for: limit breach check, headroom analysis, approver details. |
| ''' |
| return await \_call_sajha('get_credit_limits', {'counterparty': counterparty}) |
|  |
| @tool |
| async def get_historical_exposure(counterparty: str, date: str) -\> dict: |
| '''Returns point-in-time exposure snapshot for a specific historical date. |
| Use for: QoQ trend analysis — call in parallel with four quarter-end dates. |
| ''' |
| return await \_call_sajha('get_historical_exposure', |
| {'counterparty': counterparty, 'date': date}) |
|  |
| @tool |
| async def get_var_contribution(counterparty: str, |
| confidence_level: str = '99%') -\> dict: |
| '''Returns VaR contribution, marginal VaR, component VaR, and stress loss. |
| Use for: portfolio risk contribution, VaR decomposition. |
| ''' |
| return await \_call_sajha('get_var_contribution', |
| {'counterparty': counterparty, |
| 'confidence_level': confidence_level}) |
|  |
| @tool |
| async def web_search(query: str) -\> dict: |
| '''Searches the web for news, ratings actions, filings, and market intelligence. |
| Use for: recent news, credit rating changes, earnings, regulatory filings. |
| ''' |
| return await \_call_sajha('tavily', {'query': query}) |
|  |
| AGENT_TOOLS = \[ |
| get_counterparty_exposure, get_trade_inventory, get_credit_limits, |
| get_historical_exposure, get_var_contribution, web_search |
| \] |

**2.4 create_agent Setup (agent/agent.py)**

|  |
|----|
| **// agent/agent.py** |
| \# agent/agent.py |
| from langchain.agents import create_agent \# LangChain v1.0 — current standard |
| from langchain_anthropic import ChatAnthropic |
| from langgraph.checkpoint.memory import MemorySaver |
| from .tools import AGENT_TOOLS |
| from .prompt import SYSTEM_PROMPT |
|  |
| llm = ChatAnthropic( |
| model='claude-sonnet-4-20250514', |
| temperature=0, |
| streaming=True, |
| ) |
|  |
| \# MemorySaver: in-memory state per thread_id (restart-safe with SqliteSaver) |
| \# SqliteSaver: use in production — state survives server restarts |
| checkpointer = MemorySaver() |
| \# from langgraph.checkpoint.sqlite import SqliteSaver |
| \# checkpointer = SqliteSaver.from_conn_string('agent_state.db') |
|  |
| agent = create_agent( |
| model=llm, |
| tools=AGENT_TOOLS, |
| checkpointer=checkpointer, |
| system_prompt=SYSTEM_PROMPT, |
| ) |
|  |
| \# LangGraph handles under the hood: |
| \# · ReAct loop: LLM → ToolNode (parallel) → LLM → repeat until no tool_calls |
| \# · State accumulated in messages list via MemorySaver per thread_id |
| \# · recursion_limit protects against infinite loops (default: 25) |

**2.5 System Prompt (agent/prompt.py)**

|  |
|----|
| **// agent/prompt.py** |
| \# agent/prompt.py |
| \# Tool descriptions are auto-injected from @tool docstrings by LangGraph. |
| \# This prompt focuses on persona, reasoning style, and attribution rules. |
|  |
| SYSTEM_PROMPT = '''You are a sophisticated financial risk intelligence agent. |
|  |
| REASONING STYLE: |
| \- Think step by step before deciding which tools to call |
| \- For full risk picture queries: call exposure, trades, limits, and web_search in parallel |
| \- For QoQ trend queries: call get_historical_exposure 4 times in parallel |
| with dates 2025-03-31, 2025-06-30, 2025-09-30, 2025-12-31 |
| \- Always synthesize all tool results into a coherent structured response |
| \- If a tool fails, note the gap and proceed with available data |
|  |
| SOURCE ATTRIBUTION: |
| After every specific figure, date, or fact from a tool result, append immediately: |
| \[src:tool_name\] |
| Examples: |
| Net exposure \$26.2M \[src:get_counterparty_exposure\] |
| Q3 MTM \$33.8M \[src:get_historical_exposure\] |
| Credit rating AA- \[src:get_counterparty_exposure\] |
| Do NOT annotate general commentary or your own analysis. |
|  |
| FINANCIAL PRECISION: |
| \- Distinguish MTM (mark-to-market) from notional at all times |
| \- Always state currency and date for exposure figures |
| \- Flag limit breaches explicitly with utilization percentage |
| \- Report VaR at the stated confidence level |
| ''' |

| **03** | **FastAPI Backend** <br> *SSE streaming endpoint, HITL resume, CORS, and environment* |
| --- | --- |

**3.1 Main Application and SSE Endpoint**

|  |
|----|
| **// agent_server.py** |
| \# agent_server.py |
| import os, json, uuid |
| from fastapi import FastAPI |
| from fastapi.responses import StreamingResponse |
| from fastapi.middleware.cors import CORSMiddleware |
| from pydantic import BaseModel |
| from dotenv import load_dotenv |
| from agent.agent import agent |
|  |
| load_dotenv() |
| app = FastAPI(title='MCP Intelligence Agent') |
|  |
| app.add_middleware(CORSMiddleware, |
| allow_origins=\['http://localhost:8080', 'http://127.0.0.1:8080'\], |
| allow_methods=\['POST', 'OPTIONS'\], |
| allow_headers=\['Content-Type'\], |
| ) |
|  |
| class RunRequest(BaseModel): |
| query: str |
| thread_id: str = '' \# empty = new session |
| resume: str \| None = None \# HITL resume answer |
|  |
| @app.post('/api/agent/run') |
| async def run_agent(req: RunRequest): |
| thread_id = req.thread_id or str(uuid.uuid4()) |
| config = {'configurable': {'thread_id': thread_id}} |
|  |
| async def stream(): |
| yield f"data: {json.dumps({'type':'session','thread_id':thread_id})}\n\n" |
| try: |
| inp = ({'messages': \[{'role':'user','content':req.query}\]} |
| if not req.resume else {'resume': req.resume}) |
|  |
| async for event in agent.astream_events(inp, config=config, version='v2'): |
| t = event\['event'\] |
|  |
| if t == 'on_chat_model_stream': |
| chunk = event\['data'\]\['chunk'\].content |
| if chunk: |
| yield f"data: {json.dumps({'type':'text','text':chunk})}\n\n" |
|  |
| elif t == 'on_tool_start': |
| yield f"data: {json.dumps({ |
| 'type':'tool_start', 'name':event\['name'\], |
| 'input':event\['data'\]\['input'\], 'run_id':event\['run_id'\] |
| })}\n\n" |
|  |
| elif t == 'on_tool_end': |
| yield f"data: {json.dumps({ |
| 'type':'tool_end', 'name':event\['name'\], |
| 'output':event\['data'\]\['output'\], 'run_id':event\['run_id'\] |
| })}\n\n" |
|  |
| elif t == 'on_interrupt': |
| yield f"data: {json.dumps({ |
| 'type':'hitl', |
| 'question':event\['data'\].get('question',''), |
| 'options':event\['data'\].get('options',\[\]), |
| 'thread_id':thread_id |
| })}\n\n" |
|  |
| elif t == 'on_chat_model_end': |
| usage = event\['data'\].get('output',{}).get('usage_metadata',{}) |
| if usage: |
| yield f"data: {json.dumps({'type':'usage','usage':usage})}\n\n" |
|  |
| yield 'data: \[DONE\]\n\n' |
| except Exception as e: |
| yield f"data: {json.dumps({'type':'error','message':str(e)})}\n\n" |
| yield 'data: \[DONE\]\n\n' |
|  |
| return StreamingResponse(stream(), media_type='text/event-stream', |
| headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'}) |
|  |
| \# Start: uvicorn agent_server:app --host 0.0.0.0 --port 8000 --reload |

**3.2 Environment Variables**

|                                                    |
|----------------------------------------------------|
| **// .env**                                        |
| \# .env (never commit to version control)          |
| ANTHROPIC_API_KEY=sk-ant-...                       |
| SAJHA_BASE_URL=http://localhost:3002               |
| SAJHA_PASSWORD=RiskAgent2025!                      |
|                                                    |
| \# LangSmith observability (strongly recommended): |
| LANGCHAIN_TRACING_V2=true                          |
| LANGCHAIN_API_KEY=ls\_\_...                        |
| LANGCHAIN_PROJECT=mcp-intelligence-agent           |

| **04** | **HTML Frontend** <br> *SSE event contract, simplified runAgent(), and what the HTML owns* |
| --- | --- |

**4.1 SSE Event Contract**

The frontend receives a stream of JSON events from the FastAPI backend. Every event has a type field. The frontend routes on type to update the correct UI element in real time.

|  |  |  |
|:--:|:--:|:--:|
| **Event type** | **Payload** | **Frontend action** |
| session | { thread_id } | Store in \_threadId for session persistence and HITL resume |
| text | { text } | Append chunk to active streaming element (thinking or synthesis text) |
| tool_start | { name, input, run_id } | Create tool card in running state (amber spinner) |
| tool_end | { name, output, run_id } | Update tool card: spinner → ✓ green or ✗ red, show response |
| usage | { input_tokens, output_tokens } | recordCost() → updateCostDisplay() → amber cost figure |
| hitl | { question, options, thread_id } | Show HITL card; on submit POST /api/agent/run with resume |
| error | { message } | renderPartialResults(message); switchTab('report') |
| \[DONE\] | (literal string) | finaliseReport(); renderWithAttribution(); saveSession(); switchTab |

**4.2 runAgent() in the HTML File**

|  |
|----|
| **// HTML frontend runAgent()** |
| // mcp-agent.html \<script\> |
| var \_threadId = null; |
| var \_activeReader = null; |
|  |
| async function runAgent(query) { |
| var res = await fetch('http://localhost:8000/api/agent/run', { |
| method: 'POST', |
| headers: { 'Content-Type': 'application/json' }, |
| body: JSON.stringify({ query: query, thread_id: \_threadId \|\| '' }) |
| }); |
|  |
| \_activeReader = res.body.getReader(); |
| var decoder = new TextDecoder(); |
| var buffer = ''; |
|  |
| while (true) { |
| var chunk = await \_activeReader.read(); |
| if (chunk.done) break; |
| buffer += decoder.decode(chunk.value); |
| var lines = buffer.split('\n'); |
| buffer = lines.pop(); |
|  |
| for (var line of lines) { |
| if (!line.startsWith('data: ')) continue; |
| var data = line.slice(6).trim(); |
| if (data === '\[DONE\]') { |
| finaliseReport(); saveSession(); return; |
| } |
| try { |
| var evt = JSON.parse(data); |
| switch (evt.type) { |
| case 'session': \_threadId = evt.thread_id; break; |
| case 'text': streamText(evt.text); break; |
| case 'tool_start': onToolStart(evt); break; |
| case 'tool_end': onToolEnd(evt); break; |
| case 'usage': recordCost(evt.usage); break; |
| case 'hitl': showHitl(evt); break; |
| case 'error': renderPartialResults(evt.message); return; |
| } |
| } catch(e) {} |
| } |
| } |
| } |
|  |
| // Cancel: aborts the SSE stream mid-query |
| function cancelRun() { |
| if (\_activeReader) \_activeReader.cancel(); |
| renderPartialResults('Cancelled by user'); |
| } |
|  |
| // HITL resume: POST with the analyst's answer and current thread_id |
| function submitHitl() { |
| var answer = getHitlAnswer(); |
| hideHitlCard(); |
| fetch('http://localhost:8000/api/agent/run', { |
| method: 'POST', |
| headers: { 'Content-Type': 'application/json' }, |
| body: JSON.stringify({ query: '', thread_id: \_threadId, resume: answer }) |
| }).then(resumeStream); |
| } |

**4.3 What the HTML File Owns**

|  |  |
|:--:|:--:|
| **Component** | **Responsibility** |
| TOOL_UI_META | icon, color, category, label per tool — visual metadata only |
| streamText(text) | Appends SSE text chunks to the active streaming DOM element with blinking cursor |
| onToolStart(evt) | Creates a tool card in running state; keyed by run_id |
| onToolEnd(evt) | Updates the matching tool card: spinner → ✓/✗, populates response data |
| onSummaryEvent(info) | Renders orange summarisation event card in Trace tab |
| recordCost(usage) | Accumulates inputTokens + outputTokens; computes USD via COST_PER_M constants |
| updateCostDisplay() | Updates context meter: real token count + amber cost + hover tooltip |
| renderWithAttribution(text) | Replaces \[src:tool_name\] markers with clickable src-badge spans |
| jumpToTool(name) | Switches to Tool Calls tab; scrolls to and flash-animates the matching card |
| renderPartialResults(reason) | Warning banner + all successful tool results as data cards |
| exportPDF() | document.body.classList.add('print-mode'); window.print() |
| exportMarkdown() | Builds markdown string from synthesis + lineage; navigator.clipboard.writeText() |
| saveSession() | Persists thread_id, last synthesis, tool results, cost to localStorage |
| restoreSession() | Reads localStorage on page load; restores if saved within 24 hours |
| showHitl(evt) | Renders HITL card with question, option buttons, free-text input |
| init() | Async: sajha token check → tool bar → sample queries → keyboard shortcut → restore |

| **05** | **Context Management & Cost Tracking** <br> *Summarisation, token estimation, and real USD cost from API* |
| --- | --- |

**5.1 Auto-Summarisation**

LangGraph's MemorySaver accumulates all messages per thread_id. For very long sessions, the summarization_middleware (LangChain v1.1+) compresses conversation history automatically. As a fallback, a custom summarisation node can be added to the LangGraph StateGraph that calls Claude when message count exceeds a threshold.

|  |
|----|
| **// Summarisation options** |
| \# Option A: LangChain v1.1 summarization_middleware (recommended) |
| from langchain.middleware import summarization_middleware |
|  |
| agent = create_agent( |
| model=llm, |
| tools=AGENT_TOOLS, |
| checkpointer=checkpointer, |
| system_prompt=SYSTEM_PROMPT, |
| middleware=\[summarization_middleware(max_tokens=180000, threshold=0.85)\] |
| ) |
|  |
| \# Option B: Custom summarisation node in LangGraph StateGraph |
| \# Add a node that calls Claude with a compression prompt when |
| \# len(state\['messages'\]) \>= SUMM_TURN_COUNT |
| \# This node replaces messages\[\] with a single \[CONVERSATION SUMMARY\] message |

**5.2 Real Cost Tracking in the HTML**

|  |
|----|
| **// Cost tracking in HTML** |
| // Cost constants (Claude Sonnet 4 pricing): |
| var COST_PER_M_INPUT = 3.00; // USD per million input tokens |
| var COST_PER_M_OUTPUT = 15.00; // USD per million output tokens |
|  |
| var \_sessionCost = { |
| inputTokens: 0, outputTokens: 0, callCount: 0, |
| reset: function() { this.inputTokens=0; this.outputTokens=0; this.callCount=0; }, |
| get total() { |
| return (this.inputTokens/1e6 \* COST_PER_M_INPUT) |
| \+ (this.outputTokens/1e6 \* COST_PER_M_OUTPUT); |
| } |
| }; |
|  |
| // Called when 'usage' SSE event arrives from FastAPI: |
| function recordCost(usage) { |
| \_sessionCost.inputTokens += (usage.input_tokens \|\| 0); |
| \_sessionCost.outputTokens += (usage.output_tokens \|\| 0); |
| \_sessionCost.callCount++; |
| updateCostDisplay(); |
| } |
|  |
| function updateCostDisplay() { |
| var tok = \_sessionCost.inputTokens + \_sessionCost.outputTokens; |
| document.getElementById('ctxNums').innerHTML = |
| '\<span\>' + Math.round(tok/1000) + 'k tok\</span\>' |
| \+ ' · \<span style="color:var(--amber);font-weight:700"\>\$' |
| \+ \_sessionCost.total.toFixed(4) + '\</span\>'; |
| document.getElementById('ctxMeter').title = |
| 'Input: '+\_sessionCost.inputTokens.toLocaleString()+' tok' |
| +'\nOutput: '+\_sessionCost.outputTokens.toLocaleString()+' tok' |
| +'\nCalls: '+\_sessionCost.callCount |
| +'\nTotal: \$'+\_sessionCost.total.toFixed(4); |
| } |

**5.3 Session Persistence in the HTML**

|  |
|----|
| **// Session persistence — thread_id enables LangGraph memory continuity** |
| var SK = { |
| thread:'agent_thread_id', query:'agent_last_query', |
| synth:'agent_last_synthesis', tools:'agent_last_tools', |
| cost:'agent_session_cost', ts:'agent_last_ts' |
| }; |
|  |
| function saveSession() { |
| try { |
| localStorage.setItem(SK.thread, \_threadId \|\| ''); |
| localStorage.setItem(SK.query, \_lastQuery \|\| ''); |
| localStorage.setItem(SK.synth, JSON.stringify(\_lastSynthesis \|\| {})); |
| localStorage.setItem(SK.tools, JSON.stringify(serializeTools())); |
| localStorage.setItem(SK.cost, JSON.stringify({ |
| i: \_sessionCost.inputTokens, |
| o: \_sessionCost.outputTokens, |
| c: \_sessionCost.callCount |
| })); |
| localStorage.setItem(SK.ts, new Date().toISOString()); |
| } catch(e) { console.warn('Save failed:', e.message); } |
| } |
|  |
| function restoreSession() { |
| try { |
| var ts = localStorage.getItem(SK.ts); |
| if (!ts \|\| Date.now()-new Date(ts).getTime() \> 86400000) return false; |
| var synth = JSON.parse(localStorage.getItem(SK.synth)\|\|'null'); |
| if (!synth\|\|!synth.summary) return false; |
| \_threadId = localStorage.getItem(SK.thread) \|\| null; |
| \_lastSynthesis = synth; |
| \_lastQuery = localStorage.getItem(SK.query) \|\| ''; |
| var cost = JSON.parse(localStorage.getItem(SK.cost)\|\|'null'); |
| if (cost) { \_sessionCost.inputTokens=cost.i; \_sessionCost.outputTokens=cost.o; } |
| document.getElementById('query').value = \_lastQuery; |
| document.getElementById('resultsArea').style.display = 'block'; |
| restoreToolCards(JSON.parse(localStorage.getItem(SK.tools)\|\|'null')); |
| renderReport(synth); updateCostDisplay(); showRestoredBanner(ts); |
| return true; |
| } catch(e) { return false; } |
| } |
| // On restore, \_threadId is also restored so the next query continues the same |
| // LangGraph conversation thread — MemorySaver remembers it by thread_id. |

| **06** | **Source Attribution & Report Export** <br> *[src:] badges, PDF, and Markdown with data lineage* |
| --- | --- |

**6.1 Source Attribution**

The system prompt instructs Claude to append \[src:tool_name\] after every specific figure in the synthesis. The HTML post-processes the synthesis text, replacing markers with clickable badges that jump to the originating tool card.

|  |
|----|
| **// Attribution badge renderer** |
| function renderWithAttribution(text) { |
| return esc(text).replace(/\\src:(\[a-z\_\]+)\\/g, function(m, toolName) { |
| var tool = TOOL_UI_META\[toolName\] \|\| {}; |
| return '\<span class="src-badge" data-tool="'+toolName+'"' |
| \+ ' onclick="jumpToTool(\\'+ toolName +'\\)"' |
| \+ ' title="Source: '+(tool.label\|\|toolName)+'"\>' |
| \+ '▦ '+(tool.label\|\|toolName)+'\</span\>'; |
| }); |
| } |
|  |
| function jumpToTool(name) { |
| switchTab('tools'); |
| document.querySelectorAll('.tool-card\[data-tool="'+name+'"\]').forEach(function(c){ |
| c.scrollIntoView({behavior:'smooth',block:'center'}); |
| c.classList.add('flash'); |
| setTimeout(function(){ c.classList.remove('flash'); }, 1200); |
| }); |
| } |

**6.2 PDF and Markdown Export**

|  |
|----|
| **// PDF and Markdown export** |
| // PDF: browser native print-to-PDF |
| function exportPDF() { |
| document.body.classList.add('print-mode'); |
| window.print(); |
| setTimeout(function(){ document.body.classList.remove('print-mode'); }, 500); |
| } |
|  |
| // @media print CSS: hides everything except \#panel-report |
|  |
| // Markdown: full report including data lineage |
| function exportMarkdown() { |
| if (!\_lastSynthesis) return; |
| var lines = \['# Intelligence Report', |
| '\*\*Generated:\*\* '+new Date().toLocaleString(), |
| '\*\*Query:\*\* '+(\_lastQuery\|\|''), |
| '\*\*Cost:\*\* \$'+\_sessionCost.total.toFixed(4), ''\]; |
| lines.push('## Summary', strip(\_lastSynthesis.summary), ''); |
| (\_lastSynthesis.sections\|\|\[\]).forEach(function(s){ |
| lines.push('## '+(s.title\|\|'')); |
| lines.push(strip(s.content\|\|''), ''); |
| if (s.data && Object.keys(s.data).length) { |
| lines.push('\| Metric \| Value \|','\|--------\|-------\|'); |
| Object.entries(s.data).forEach(function(e){ |
| lines.push('\| '+e\[0\]+' \| '+(typeof e\[1\]==='number'&&e\[1\]\>10000?fmt(e\[1\]):e\[1\])+' \|'); |
| }); lines.push(''); |
| } |
| }); |
| lines.push('## Data Sources'); |
| Object.values(\_toolKeys).filter(t=\>t.result&&t.result.success).forEach(function(t){ |
| lines.push('- \*\*'+(TOOL_UI_META\[t.call.name\]\|\|{}).label+'\*\*: '+JSON.stringify(t.call.input)); |
| }); |
| navigator.clipboard.writeText(lines.join('\n')) |
| .then(function(){ showToast('Copied ✓'); }); |
| } |
| function strip(t){ return (t\|\|'').replace(/\\src:\[a-z\_\]+\\/g,'').trim(); } |

| **07** | **SAJHA MCP Server** <br> *Setup, tool registration patterns, and RBAC configuration* |
| --- | --- |

**7.1 Setup and Verification**

|  |
|----|
| **// SAJHA setup and verification** |
| \# Clone and start SAJHA: |
| git clone https://github.com/ajsinha/sajhamcpserver |
| cd sajhamcpserver |
| python -m venv venv && source venv/bin/activate |
| pip install -r requirements.txt |
| python run_server.py \# starts at http://localhost:3002 |
|  |
| \# Verify API is responding: |
| TOKEN=\$(curl -s http://localhost:3002/api/auth/login \\ |
| -X POST -H 'Content-Type: application/json' \\ |
| -d '{"user_id":"admin","password":"admin123"}' \\ |
| \| python3 -c "import sys,json; print(json.load(sys.stdin)\['token'\])") |
|  |
| \# List registered tools: |
| curl -s http://localhost:3002/api/mcp \\ |
| -X POST -H 'Content-Type: application/json' \\ |
| -H "Authorization: Bearer \$TOKEN" \\ |
| -d '{"jsonrpc":"2.0","id":"1","method":"tools/list","params":{}}' \\ |
| \| python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d\['result'\]\['tools'\]),'tools')" |
|  |
| \# Test Tavily (built-in web search): |
| curl -s http://localhost:3002/api/tools/execute \\ |
| -X POST -H 'Content-Type: application/json' \\ |
| -H "Authorization: Bearer \$TOKEN" \\ |
| -d '{"tool":"tavily","arguments":{"query":"Royal Bank of Canada 2025"}}' |

**7.2 Create the Dedicated Agent User**

|                                                           |
|-----------------------------------------------------------|
| **// SAJHA RBAC user**                                    |
| // config/users.json — add after admin entry:             |
| {                                                         |
| "user_id": "risk_agent",                                  |
| "user_name": "MCP Intelligence Agent",                    |
| "password": "RiskAgent2025!",                             |
| "roles": \["api_user"\],                                  |
| "tools": \[                                               |
| "get_counterparty_exposure",                              |
| "get_trade_inventory",                                    |
| "get_credit_limits",                                      |
| "get_historical_exposure",                                |
| "get_var_contribution",                                   |
| "tavily"                                                  |
| \],                                                       |
| "enabled": true                                           |
| }                                                         |
| // risk_agent gets HTTP 403 on any tool not in this list. |
| // Never use admin credentials in the FastAPI agent.      |

**7.3 Configure CORS**

|                                                                          |
|--------------------------------------------------------------------------|
| **// SAJHA CORS**                                                        |
| \# config/server.properties:                                             |
| cors.enabled=true                                                        |
| cors.origins=http://localhost:8080,http://127.0.0.1:8080                 |
|                                                                          |
| \# Serve HTML agent from same machine:                                   |
| python -m http.server 8080 \# in project root where mcp-agent.html lives |

**7.4 The Five Internal Tools to Build**

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Tool** | **Build Pattern** | **Data Source** | **Priority** |
| get_counterparty_exposure | A — Python class (BaseMCPTool) | Internal risk engine API | 1 — highest value |
| get_historical_exposure | B — SQL (MCP Studio) + (cp, date) index | Risk data warehouse | 2 — QoQ trend |
| get_trade_inventory | A or B | Trade booking system | 3 |
| get_credit_limits | C — REST wrap (MCP Studio) | Credit limit service | 4 |
| get_var_contribution | A — Python class | VaR engine API or model DB | 5 |
| web_search (= tavily) | Built-in SAJHA — already live | Tavily API | ✔ Ready |

**7.5 Pattern A: Python Class Tool**

|  |
|----|
| **// Pattern A: Python class tool** |
| \# sajha/tools/impl/counterparty_exposure_tool.py |
| from sajha.tools.base_mcp_tool import BaseMCPTool |
| import requests |
|  |
| class CounterpartyExposureTool(BaseMCPTool): |
| def \_\_init\_\_(self, config): |
| super().\_\_init\_\_(config) |
| self.api_url = config.get('internal_api_url', '') |
| self.api_key = config.get('internal_api_key', '') |
|  |
| def execute(self, arguments): |
| cp = arguments.get('counterparty', '') |
| date = arguments.get('date', '') |
| r = requests.get(f'{self.api_url}/exposure', |
| params={'counterparty': cp, 'date': date}, |
| headers={'X-API-Key': self.api_key}, timeout=10) |
| r.raise_for_status() |
| d = r.json() |
| return { 'counterparty':d\['name'\], 'date':date, |
| 'notional_usd':d\['notional'\], 'mtm_usd':d\['mtm'\], |
| 'pfe_usd':d\['pfe'\], 'net_exposure':d\['net'\], |
| 'credit_rating':d\['rating'\], 'collateral_posted':d\['collateral'\] } |
|  |
| def get_input_schema(self): |
| return { 'type':'object', 'properties': { |
| 'counterparty': {'type':'string','description':'Name or LEI'}, |
| 'date': {'type':'string','description':'YYYY-MM-DD'} |
| }, 'required':\['counterparty'\] } |
|  |
| \# config/tools/counterparty_exposure.json: |
| \# { "name":"get_counterparty_exposure", |
| \# "implementation":"sajha.tools.impl.counterparty_exposure_tool.CounterpartyExposureTool", |
| \# "description":"Returns notional, MTM, PFE and net exposure for a counterparty", |
| \# "enabled":true, "internal_api_url":"http://risk.internal/api", |
| \# "internal_api_key":"\${INTERNAL_RISK_API_KEY}" } |
|  |
| \# Drop both files → SAJHA hot-reloads instantly, zero restart needed. |

**7.6 Pattern B: SQL Query Tool**

Admin → MCP Studio → Database Query Tool Creator. Write parameterised SQL; Studio generates the JSON Schema automatically. Supports PostgreSQL, MySQL, SQLite, DuckDB.

|  |
|----|
| **// Pattern B: parameterised SQL** |
| -- get_historical_exposure SQL (registered via MCP Studio): |
| SELECT counterparty_name AS counterparty, snapshot_date AS date, |
| notional_usd, mtm_usd, pfe_usd, net_exposure_usd |
| FROM exposure_snapshots |
| WHERE counterparty_name = {{counterparty}} |
| AND snapshot_date = {{date}}::date |
| LIMIT 1; |
|  |
| -- Index required for sub-100ms on 4 parallel QoQ calls: |
| CREATE INDEX idx_exp_cp_date ON exposure_snapshots(counterparty_name, snapshot_date); |

**7.7 Pattern C: REST Wrap Tool**

Admin → MCP Studio → REST Service Tool Creator. Point at internal API, configure auth headers, define input schema. No Python file needed.

|                                                                    |
|--------------------------------------------------------------------|
| **// Pattern C: REST wrap**                                        |
| // MCP Studio REST Tool Creator — example for get_credit_limits:   |
| Tool Name: get_credit_limits                                       |
| Method: GET                                                        |
| Endpoint: http://credit-service.internal/api/limits/{counterparty} |
| Auth: API Key → Header: X-API-Key → Value: \${CREDIT_API_KEY}      |
| Path Param: counterparty (string, required)                        |
| // Click Deploy — tool appears in tools/list immediately           |

| **08** | **LangGraph Built-In Capabilities** <br> *What create_agent handles automatically* |
| --- | --- |

**8.1 ReAct Loop and Parallel Tools**

create_agent implements the full ReAct loop automatically. When Claude's response contains tool_calls, LangGraph's ToolNode fires all of them simultaneously via asyncio.gather(), collects the results as ToolMessage objects, and feeds them back to Claude. This continues until Claude returns a response with no tool_calls.

|  |
|----|
| **// LangGraph ReAct loop internals** |
| \# What LangGraph does automatically inside create_agent: |
|  |
| \# 1. LLM node: call Claude with current messages + tool schemas |
| \# Claude responds with AIMessage that may contain tool_calls |
|  |
| \# 2. ToolNode: if AIMessage has tool_calls: |
| \# → fire all tool_calls in parallel via asyncio.gather() |
| \# → each call goes to the matching @tool function |
| \# → results become ToolMessage objects added to state |
|  |
| \# 3. Back to LLM with tool results in messages |
| \# Loop continues until no tool_calls in response |
|  |
| \# QoQ trend: Claude emits 4 get_historical_exposure tool_calls in one message |
| \# ToolNode fires all 4 via asyncio.gather() — latency = max, not sum |
|  |
| \# Error handling: if a @tool raises, ToolNode returns a ToolMessage with |
| \# the error text. Claude sees it and can retry or note the gap. |

**8.2 Memory and State**

|  |  |
|:--:|:--:|
| **Feature** | **LangGraph mechanism** |
| Conversation memory across turns | MemorySaver stores messages list per thread_id in RAM |
| State survives server restarts | SqliteSaver stores to disk — recommended for production |
| New session | Empty thread_id → uuid4() → fresh state in MemorySaver |
| Resumed session | Stored thread_id from localStorage → MemorySaver restores messages |
| Max iterations guard | recursion_limit in config (default 25); raises GraphRecursionError |
| HITL pause | interrupt() in a custom node; state saved; resumes on Command(resume=) |
| Context window management | summarization_middleware or custom node when messages grow large |

**8.3 LangSmith Observability**

When LANGCHAIN_TRACING_V2=true is set in the environment, every create_agent execution is traced in LangSmith automatically. No additional instrumentation is required. This is the full audit trail for the system.

- Every LLM call: prompt, response, input/output token count, latency, cost

- Every tool call: name, input, output, latency, success / error

- Full ReAct trajectory: which tools fired in which order

- Thread history: all turns in a session, grouped by thread_id

- Feedback: thumbs up/down attached to traces for evals

| ✓ | **LangSmith is the audit trail** <br> LangSmith traces satisfy the full observability requirement. Combined with SAJHA's server.log for tool execution details, every agent query has complete end-to-end lineage: who asked, what Claude reasoned, which tools fired, what data came back, and what the synthesis concluded. |
| --- | --- |

| **09** | **Complete End-to-End Flows** <br> *Startup, full query, QoQ trend, and HITL* |
| --- | --- |

**9.1 System Startup**

|                                                              |
|--------------------------------------------------------------|
| **// Startup**                                               |
| Terminal 1 — SAJHA MCP Server:                               |
| cd sajhamcpserver && python run_server.py                    |
| → http://localhost:3002 (tool execution layer)               |
|                                                              |
| Terminal 2 — LangGraph FastAPI Backend:                      |
| uvicorn agent_server:app --host 0.0.0.0 --port 8000 --reload |
| → http://localhost:8000 (agent reasoning layer)              |
|                                                              |
| Terminal 3 — HTML Frontend:                                  |
| python -m http.server 8080                                   |
| Open: http://localhost:8080/mcp-agent.html                   |
|                                                              |
| LangSmith (optional):                                        |
| Set LANGCHAIN_TRACING_V2=true in .env                        |
| Open: https://smith.langchain.com → see traces appear        |

**9.2 Full Query Execution**

|  |
|----|
| **// Full query execution** |
| Analyst types: 'Get the full picture on RBC' |
| ↓ HTML: POST /api/agent/run { query, thread_id } |
|  |
| FastAPI → agent.astream_events() starts |
| ↓ |
| LangGraph — LLM node: Claude thinks, decides to call 4 tools in parallel |
| → SSE on_chat_model_stream: thinking tokens stream to Trace tab word-by-word |
| ↓ |
| LangGraph — ToolNode: fires all 4 tool_calls simultaneously |
| → SSE on_tool_start ×4: 4 tool cards appear as 'running' in Tools tab |
| → 4 x callSajha() via httpx to SAJHA (asyncio.gather): |
| SAJHA executes get_counterparty_exposure → returns live data |
| SAJHA executes get_trade_inventory → returns trade list |
| SAJHA executes get_credit_limits → returns limit utilization |
| SAJHA executes tavily → returns 3 RBC news items |
| → SSE on_tool_end ×4: tool cards update spinner → ✓ |
| → SAJHA server.log: 4 entries written automatically |
| ↓ |
| LangGraph — LLM node: Claude synthesises all 4 results |
| → SSE on_chat_model_stream: synthesis streams word-by-word |
| → Claude appends \[src:\] markers to figures per system prompt |
| → Claude returns no tool_calls: loop ends |
| → SSE on_chat_model_end: usage → recordCost() → cost meter updates |
| → SSE \[DONE\] |
| ↓ |
| HTML: finaliseReport() |
| → renderWithAttribution() → \[src:\] markers → clickable badges |
| → renderExportBar() |
| → saveSession() → localStorage: thread_id + synthesis |
| → switchTab('report') |
| → LangSmith: full trace logged |
| Total time: ~8–12 seconds |

**9.3 QoQ Trend Analysis — Parallel Fan-Out**

|  |
|----|
| **// QoQ parallel fan-out** |
| Analyst: 'Run a QoQ trend on RBC for the last 4 quarters' |
|  |
| LangGraph ToolNode receives 4 tool_calls in one AIMessage: |
| { name:'get_historical_exposure', args:{counterparty:'RBC', date:'2025-03-31'} } |
| { name:'get_historical_exposure', args:{counterparty:'RBC', date:'2025-06-30'} } |
| { name:'get_historical_exposure', args:{counterparty:'RBC', date:'2025-09-30'} } |
| { name:'get_historical_exposure', args:{counterparty:'RBC', date:'2025-12-31'} } |
|  |
| asyncio.gather() fires all 4 calls simultaneously. |
| Latency = max(individual call times), not sum. |
| SAJHA SQL executes 4 parameterised queries in parallel. |
| Index on (counterparty_name, snapshot_date) keeps each \< 100ms. |
| Claude synthesizes QoQ trend from ordered ToolMessage results. |

**9.4 Human-in-the-Loop Flow**

|                                                                |
|----------------------------------------------------------------|
| **// HITL flow**                                               |
| Analyst: 'What is our exposure?' (ambiguous — no counterparty) |
|                                                                |
| Custom HITL node in LangGraph calls interrupt():               |
| interrupt({ 'question': 'Which counterparty?',                 |
| 'options': \['RBC', 'TD Bank', 'Goldman Sachs'\] })            |
|                                                                |
| → SSE: on_interrupt → HTML shows HITL card with option buttons |
| → LangGraph state saved to MemorySaver; execution paused       |
|                                                                |
| Analyst clicks 'RBC'                                           |
| → HTML: POST /api/agent/run { thread_id, resume: 'RBC' }       |
| → FastAPI: agent.astream_events({ 'resume':'RBC' }, config)    |
| → LangGraph resumes from exact pause point                     |
| → Continues with full RBC query                                |

| **10** | **Security & Production Deployment** <br> *API key, CORS, Nginx proxy, environment variables* |
| --- | --- |

**10.1 API Key Security**

The ANTHROPIC_API_KEY lives only in the FastAPI .env file and is loaded by python-dotenv at server startup. It is never sent to the browser. This resolves the primary security concern of v1–v3 where the key was in the HTML file.

|                                                                         |
|-------------------------------------------------------------------------|
| **// API key security**                                                 |
| \# FastAPI backend adds the key:                                        |
| llm = ChatAnthropic(                                                    |
| model='claude-sonnet-4-20250514',                                       |
| api_key=os.getenv('ANTHROPIC_API_KEY'), \# from .env                    |
| streaming=True,                                                         |
| )                                                                       |
|                                                                         |
| \# Browser only sees: SSE text chunks, token counts, tool names         |
| \# Browser never sees: API key, raw LLM responses, internal system URLs |

**10.2 Production Nginx Configuration**

For team deployments, Nginx serves the HTML file and proxies the FastAPI backend. This shares a single origin, eliminating all CORS complexity.

|  |
|----|
| **// Nginx production config** |
| \# /etc/nginx/sites-available/mcp-agent |
| server { |
| listen 443 ssl; |
| server_name risk-agent.internal; |
|  |
| \# Serve HTML frontend as static file |
| location / { |
| root /opt/mcp-agent; |
| try_files \$uri /mcp-agent.html; |
| } |
|  |
| \# Proxy FastAPI (same origin — no CORS needed) |
| location /api/ { |
| proxy_pass http://127.0.0.1:8000; |
| proxy_buffering off; \# Critical for SSE |
| proxy_read_timeout 120s; |
| proxy_set_header Connection ''; |
| proxy_http_version 1.1; |
| } |
|  |
| \# Proxy SAJHA MCP Server |
| location /sajha/ { |
| proxy_pass http://127.0.0.1:3002/; |
| } |
| } |
|  |
| \# FastAPI process manager (systemd or supervisor): |
| \# gunicorn agent_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000 |

| **11** | **Roadmap — Future Capabilities** <br> *What LangGraph enables next* |
| --- | --- |

**11.1 Near-Term (v6.0)**

|  |  |  |
|:--:|:--:|:--:|
| **Capability** | **LangGraph mechanism** | **Notes** |
| Input/output guardrails | content_moderation_middleware (LangChain v1.1) | Blocks PII, unsafe content before LLM + after tool |
| Multi-agent supervisor | LangGraph subgraph — supervisor routes to specialist agents | Risk agent, Trading agent, Compliance agent |
| Scheduled proactive runs | FastAPI BackgroundTasks + cron endpoint | Morning RBC briefing use case |
| Cross-session long-term memory | SqliteSaver → semantic search via LangSmith | Recall prior queries about RBC across sessions |
| Feedback / evals | LangSmith thumbs up/down on traces | Prompt improvement dataset |
| User identity + RBAC | FastAPI JWT middleware → per-user thread_id | Multi-analyst shared deployment |

**11.2 Multi-Agent Sketch (v6.0)**

|                                                                          |
|--------------------------------------------------------------------------|
| **// v6.0 multi-agent sketch**                                           |
| \# Supervisor routes complex queries to specialist agents:               |
| from langchain.agents import create_agent                                |
|                                                                          |
| risk_agent = create_agent(llm, tools=\[get_counterparty_exposure,        |
| get_historical_exposure,                                                 |
| get_var_contribution\])                                                  |
| trading_agent = create_agent(llm, tools=\[get_trade_inventory\])         |
| intel_agent = create_agent(llm, tools=\[web_search, get_credit_limits\]) |
|                                                                          |
| \# Supervisor orchestrates:                                              |
| \# 'Compare RBC vs TD risk' → routes to risk_agent for both,             |
| \# trading_agent for inventory, intel_agent for news,                    |
| \# then synthesizes across all three                                     |

**Appendix A — Complete Capability Matrix**

All capabilities and which layer owns them.

|  |  |
|:--:|:--:|
| **Capability** | **Layer** |
| ReAct loop: Think → Plan → Act → Observe → Synthesize | LangGraph create_agent |
| Parallel tool execution: all tool_calls fire simultaneously | LangGraph ToolNode (asyncio.gather) |
| Human-in-the-Loop: pause and resume with analyst answer | LangGraph interrupt() + Command(resume=) |
| Retry on tool failure: error ToolMessage returned to Claude | LangGraph ToolNode error handling |
| Max iteration guard | LangGraph recursion_limit config |
| Conversation memory across turns | LangGraph MemorySaver (thread_id keyed) |
| State survives server restarts | LangGraph SqliteSaver (production) |
| Auto-summarisation: compress history on growth | LangGraph summarization_middleware or custom node |
| Streaming: LLM tokens word-by-word | FastAPI astream_events() → HTML SSE |
| Streaming: tool start / end events live | FastAPI astream_events() → HTML SSE |
| User cancellation (Cancel button) | HTML \_activeReader.cancel() |
| Tool 30s timeout per call | Python httpx timeout in callSajha() |
| Graceful degradation: partial results on error | HTML renderPartialResults() on error SSE |
| Source attribution: \[src:\] markers in synthesis | System prompt in Python + HTML renderWithAttribution() |
| Attribution badges: clickable, jump to tool card | HTML |
| PDF export via browser print dialog | HTML exportPDF() + @media print CSS |
| Markdown export with data lineage | HTML exportMarkdown() + strip() |
| Real token cost from API usage field | HTML recordCost() from usage SSE event |
| Live USD cost display with tooltip | HTML updateCostDisplay() |
| Session persistence: thread_id + report (24h TTL) | HTML saveSession() / restoreSession() |
| Restored session banner + Clear Session | HTML |
| SAJHA auth: Bearer token + silent 401 re-auth | Python \_call_sajha() |
| RBAC: risk_agent with restricted tool list | SAJHA config/users.json |
| Audit log: every tool call to server.log | SAJHA automatic |
| Full observability: LLM + tool trace per query | LangSmith (LANGCHAIN_TRACING_V2=true) |
| API key security: never reaches browser | FastAPI .env ANTHROPIC_API_KEY |
| Context meter: token estimate and USD cost | HTML |
| Three-tab UI: Trace / Tools / Report | HTML |
| Tool bar with live tool chips | HTML TOOL_UI_META |
| Export bar: PDF + Markdown buttons | HTML |
| CORS: browser can call backend | FastAPI CORSMiddleware or Nginx proxy |
| Process management: restart on crash | systemd / supervisor / gunicorn |

**Appendix B — Implementation Checklist**

**Python Backend**

1.  python -m venv venv && pip install -r requirements.txt

2.  Copy .env.example to .env: fill ANTHROPIC_API_KEY and SAJHA_PASSWORD

3.  Set LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY for LangSmith

4.  uvicorn agent_server:app --port 8000 — verify http://localhost:8000/docs

5.  Test POST /api/agent/run with a simple query and verify SSE events arrive

6.  Confirm on_chat_model_stream, on_tool_start, on_tool_end, usage, \[DONE\] all fire

**SAJHA MCP Server**

7.  Clone https://github.com/ajsinha/sajhamcpserver, pip install, python run_server.py

8.  Create risk_agent user in config/users.json with 6-tool access list

9.  Configure cors.enabled + cors.origins in config/server.properties

10. Verify Tavily: test web_search @tool function directly from Python

11. Build internal tools in priority order: exposure → historical → trades → limits → VaR

12. Set all secrets as \${KEY} env vars in tool JSON configs

**HTML Frontend**

13. Remove any direct Anthropic API calls from HTML — all go to FastAPI now

14. Add runAgent() pointing at POST http://localhost:8000/api/agent/run

15. Add SSE event router switching on evt.type (session, text, tool_start, tool_end, usage, hitl, error, \[DONE\])

16. Store thread_id from session event in \_threadId variable

17. HITL submit: POST /api/agent/run with { thread_id: \_threadId, resume: answer }

18. Keep all render functions, export functions, cost tracking, session persistence

19. Verify Cancel button calls \_activeReader.cancel() and renders partial results

**Production**

20. Switch MemorySaver to SqliteSaver (persistent across restarts)

21. Configure Nginx: serve HTML static + proxy /api/ to FastAPI

22. Enable HTTPS on Nginx

23. gunicorn with UvicornWorker for multi-process FastAPI

24. Set up log rotation for logs/server.log (SAJHA) and FastAPI logs

25. Verify LangSmith traces appear for every query

**Appendix C — Glossary**

|  |  |
|----|----|
| **create_agent** | LangChain v1.0 function for building ReAct agents; built on LangGraph v1.0 runtime; current standard |
| **LangGraph** | Low-level orchestration runtime: StateGraph, ToolNode, MemorySaver, interrupt(), astream_events() |
| **LangChain v1.0** | High-level agent framework built on LangGraph; create_agent + middleware system; stable API (Oct 2025) |
| **ToolNode** | LangGraph node that executes all tool_calls in an AIMessage in parallel via asyncio.gather() |
| **MemorySaver** | In-memory LangGraph checkpointer; persists agent state per thread_id |
| **SqliteSaver** | Disk-backed LangGraph checkpointer; state survives server restarts; use in production |
| **thread_id** | Session identifier; passed in every agent invocation config; MemorySaver uses it to restore state |
| **astream_events** | LangGraph async generator yielding on_chat_model_stream, on_tool_start, on_tool_end, usage events |
| **interrupt()** | LangGraph primitive: pauses graph, saves state, waits for Command(resume=) to continue |
| **Command(resume=)** | LangGraph type passed to agent.ainvoke() to resume an interrupted execution |
| **recursion_limit** | LangGraph config limiting max graph iterations; replaces manual iter counter |
| **LangSmith** | Observability platform; traces every node, tool call, and LLM response; stores cost per run |
| **SAJHA MCP Server** | Production Python/Flask MCP server; data access layer; all tool calls route through it |
| **callSajha / \_call_sajha** | Python async function making HTTP POST to SAJHA /api/tools/execute with Bearer token |
| **Bearer token** | SAJHA auth token obtained via /api/auth/login; cached in \_sajha_token; re-fetched on 401 |
| **risk_agent** | Dedicated SAJHA user for agent API calls; RBAC-restricted to the 6 agent tools |
| **BaseMCPTool** | SAJHA base class to extend for Pattern A custom tool implementations |
| **Pattern A** | Tool as Python class extending BaseMCPTool in sajha/tools/impl/ |
| **Pattern B** | Tool as parameterised SQL via MCP Studio DB Query Tool Creator |
| **Pattern C** | Tool wrapping an existing REST endpoint via MCP Studio REST Service Tool Creator |
| **\${KEY}** | SAJHA variable substitution in tool config JSON; resolves to environment variable at runtime |
| **astream_events v2** | LangGraph streaming API version; required for on_tool_start / on_tool_end events |
| **LANGCHAIN_TRACING_V2** | Environment variable enabling LangSmith tracing when set to 'true' |
| **renderWithAttribution** | HTML function replacing \[src:tool_name\] markers with clickable src-badge spans |
| **\[src:tool_name\]** | Inline attribution marker Claude appends to figures; post-processed by renderWithAttribution() |
| **\_threadId** | Frontend variable holding current session thread_id; restored from localStorage on reload |
| **saveSession()** | Persists thread_id + synthesis + cost + tools to localStorage after every completed query |
| **restoreSession()** | Reads localStorage on page load; restores full session if saved within 24 hours |
| **QoQ** | Quarter-over-Quarter: 4 parallel get_historical_exposure calls with Q1–Q4 dates |
| **SSE** | Server-Sent Events: HTTP streaming used by FastAPI to push events to the HTML frontend |
| **Summarization middleware** | LangChain v1.1 middleware compressing message history when context grows large |

*End of Document — MCP Intelligence Agent · Technical Reference Document · Final Edition*
