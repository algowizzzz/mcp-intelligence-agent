# Engineering Plan

Four work streams. This document supersedes the earlier version with full detail on Tavily coverage gaps, property-file governance for all tools, and the source-attribution redesign.

---

## Stream 1 — Intelligent Context Management (Summarisation)

### Problem
The current `MessageTrimmer` silently drops old messages. Production chatbots compress old context into a summary so the agent retains facts without blowing the token budget.

### Design

**Threshold & Trigger** (`.env`):
```
CONTEXT_WARN_TOKENS=120000   # trigger summarisation before next turn
CONTEXT_HARD_TOKENS=160000   # hard block until done (leaves 40k for prompt+response)
```

**`SummarisationMiddleware`** (`agent/summariser.py`):
Uses the `before_agent` hook (fires once per user turn, before the model loop).

```
before_agent(state):
  1. estimate tokens: sum(len(str(m.content)) / 4 for m in state["messages"])
  2. if tokens < WARN threshold → return None (no-op)
  3. split: tail = last 10 messages (kept verbatim — never split tool_call/tool_result pairs)
            head = everything before tail
  4. call LLM with SUMMARISE_PROMPT + head (temperature=0, no tools, max_tokens=600)
  5. replace head with: SystemMessage("## Prior Conversation Summary\n{summary}")
  6. return {"messages": [summary_msg] + tail}
```

**Summarisation Prompt** (new constant in `agent/prompt.py`):
```
SUMMARISE_PROMPT = """
You are a context compressor for a financial risk intelligence session.
Summarise the messages below in ≤ 500 words. Preserve exactly:
- Every counterparty name and its exposure / limit / credit rating figures
- Every specific number (notional, MTM, PFE, VaR, utilisation %)
- Every tool that was called, what it returned, and the source cited
- Any limit breaches, credit alerts, or action items raised
Omit greetings, repeated boilerplate, and tool schema details.
Output only the summary text, no preamble.
"""
```

**Files to change:**
| File | Change |
|------|--------|
| `agent/summariser.py` | New — `SummarisationMiddleware` class |
| `agent/prompt.py` | Add `SUMMARISE_PROMPT` constant |
| `agent/agent.py` | Add `SummarisationMiddleware()` to `middleware=[...]` after `MessageTrimmer` |
| `.env` | Add `CONTEXT_WARN_TOKENS`, `CONTEXT_HARD_TOKENS` |

**Cost note:** One extra LLM call per crossing, ~$0.01–0.05. The compressed context saves multiples of that on subsequent calls.

---

## Stream 2 — UI: Separate Thinking from Response

### Problem
All streamed text goes to the grey reasoning bubble until `_reasoningDone` flips `true`. `_reasoningDone` only flips on `tool_start`. If the agent answers with no tool calls (e.g., "what is MTM?"), the full response stays in the thinking section and the synthesis div is never shown.

### Fix — Retroactive Reclassification on `[DONE]`

In `onDone()`, after the stream ends, check if any tools were called. If none, move the reasoning buffer to the synthesis div and hide the bubble. This is an 8-line addition to one function — zero streaming-path changes.

```js
// Add at the START of onDone(), before finishReasoning():
var toolCount = Object.keys(_toolDataStore).length;
if (toolCount === 0 && _currentReasoning.trim()) {
    var reasonBubble = _currentAgentMsg.querySelector('.reasoning-bubble');
    var synthDiv     = _currentAgentMsg.querySelector('.synthesis');
    if (reasonBubble && synthDiv) {
        reasonBubble.style.display = 'none';
        synthDiv.style.display     = '';
        _currentSynthesis          = _currentReasoning;
        synthDiv.innerHTML         = parseMarkdown(_currentSynthesis);
    }
}
```

**Files to change:**
| File | Change |
|------|--------|
| `mcp-agent.html` | Modify `onDone()` — 8-line block at top |

---

## Stream 3 — Tavily-Backed Yahoo Finance Tools

> **SEC EDGAR tools are out of scope for this stream.** All 20 EDGAR tools will be enabled as-is via enterprise proxy URL — update `tool.edgar.base_url`, `tool.edgar.search_url`, and `tool.edgar.viewer_url` in `server.properties` to point at your firm's proxy once it is provisioned. No code changes required.

### Approach
New tool files for Yahoo Finance only, inheriting from `TavilyBaseTool`. Same tool names, same input/output schemas. Only the data-fetch mechanism changes. Tools include `_source` in every response (the Tavily result URL) for source attribution.

---

### Yahoo Finance: Full Tool Map

#### Tool 1: `yahoo_get_quote` → `TavilyYahooGetQuoteTool`
**Status: ACHIEVABLE with minor precision caveat**

Tavily query:
```python
query  = f"{symbol} stock price market cap PE ratio EPS dividend yield 52-week high low"
params = { include_domains: ["finance.yahoo.com"], search_depth: "advanced",
           include_answer: True, max_results: 3 }
```
Parse Tavily `answer` field and top result snippets to reconstruct the output object.

Output schema match:
| Field | Achievable | Note |
|-------|-----------|------|
| `symbol` | ✅ | Passed in |
| `name` | ✅ | In Tavily snippet |
| `price` | ✅ | In Tavily answer (may lag 15 min) |
| `currency` | ✅ | Usually USD, parseable |
| `change` / `change_percent` | ✅ | In Tavily answer |
| `volume` / `avg_volume` | ⚠️ | Often available, occasionally missing |
| `market_cap` | ✅ | Prominent on Yahoo page |
| `pe_ratio` | ✅ | In Tavily answer |
| `dividend_yield` | ✅ | In Tavily answer |
| `fifty_two_week_high/low` | ✅ | In Tavily answer |
| `day_high/low`, `open`, `previous_close` | ⚠️ | Available during market hours, may be missing after-hours |
| `last_updated` | ✅ | Set to current timestamp |
| `_source` | ✅ | `https://finance.yahoo.com/quote/{symbol}` |

**Gap:** Price is delayed ~15 min (Yahoo/Tavily crawl). Not suitable for real-time execution/hedging decisions. Suitable for risk context and research.

---

#### Tool 2: `yahoo_get_history` → `TavilyYahooGetHistoryTool`
**Status: PARTIAL GAP — row-level OHLCV not achievable**

Tavily query:
```python
query  = f"{symbol} stock historical price performance {period} high low close change"
params = { include_domains: ["finance.yahoo.com"], search_depth: "advanced",
           include_answer: True, max_results: 3 }
```

What CAN be returned via Tavily:
- Period summary (start price, end price, % change, high, low)
- Dividend announcements found in the period
- Split events if any
- Trend narrative

What CANNOT be returned:
- Individual OHLCV rows (`history` array) — Tavily returns text, not tabular data
- Intraday intervals (`1m`, `5m`, `15m`, etc.)
- Exact adjusted_close series

**Design decision:** Return a `history_summary` object instead of the full `history` array. Keep the same schema but add `data_mode: "summary"` field so downstream consumers know they're getting aggregates, not rows.

Output schema adaptation:
```json
{
  "symbol": "AAPL",
  "period": "1mo",
  "interval": "1d",
  "data_mode": "summary",          ← new field, signals Tavily mode
  "data_points": null,             ← null in summary mode
  "history": [],                   ← empty in summary mode
  "period_summary": {              ← new field
    "start_price": 175.20,
    "end_price": 189.50,
    "period_high": 192.10,
    "period_low": 173.40,
    "change_percent": 8.16,
    "trend_narrative": "AAPL rose 8.2% over the past month..."
  },
  "dividends": [...],
  "splits": [...],
  "_source": "https://finance.yahoo.com/quote/AAPL/history"
}
```

**Gap documented in tool description:** "Returns period summary statistics. For individual OHLCV rows, the direct Yahoo Finance API must be accessible."

---

#### Tool 3: `yahoo_search_symbols` → `TavilyYahooSearchSymbolsTool`
**Status: ACHIEVABLE**

Tavily query:
```python
query  = f"{query} stock ticker symbol exchange listing"
params = { include_domains: ["finance.yahoo.com"], max_results: limit }
```

Output schema match:
| Field | Achievable | Note |
|-------|-----------|------|
| `symbol` | ✅ | Extracted from Yahoo URLs in results |
| `name` | ✅ | Result title |
| `exchange` | ✅ | Usually in snippet |
| `type` | ✅ | EQUITY/ETF/INDEX from snippet |
| `sector` / `industry` | ⚠️ | Not in search snippets; set to null |
| `market_cap` | ⚠️ | Sometimes in snippet |
| `description` | ✅ | Tavily snippet text |
| `_source` | ✅ | Tavily result URL per match |

---

### Source Field
Every Tavily-backed Yahoo Finance tool must include `_source` in its response JSON:
```python
"_source": results[0]["url"]          # first Tavily result URL
# or constructed:
"_source": f"https://finance.yahoo.com/quote/{symbol}"
"_source": f"https://finance.yahoo.com/quote/{symbol}/history"
```

**Files to create:**
| File | Contents |
|------|---------|
| `sajhamcpserver/sajha/tools/impl/tavily_yahoo_finance_tool.py` | `TavilyYahooGetQuoteTool`, `TavilyYahooGetHistoryTool`, `TavilyYahooSearchSymbolsTool` |
| `sajhamcpserver/config/tools/tavily_yahoo_get_quote.json` | Config JSON |
| `sajhamcpserver/config/tools/tavily_yahoo_get_history.json` | Config JSON |
| `sajhamcpserver/config/tools/tavily_yahoo_search_symbols.json` | Config JSON |

**Disable old Yahoo tools** (rename `.json` → `.json.disabled` — hot-reloaded in 5s):
- `yahoo_get_quote.json`
- `yahoo_get_history.json`
- `yahoo_search_symbols.json`

---

## Stream 4 — Enterprise Integration

### 4a — FastAPI Captive API Key

**Design:**
- `Authorization: Bearer <key>` on all `/api/*` routes
- Keys stored in `.env` as `AGENT_API_KEYS=key1,key2` (comma-separated)
- `GET /health` stays open (load balancer / uptime checks)
- Frontend receives its key via `inject-config.js` build injection

**Files to change:**
| File | Change |
|------|--------|
| `agent_server.py` | Add `HTTPBearer` dependency, apply to POST route, add `GET /health` |
| `.env` | Add `AGENT_API_KEYS`, `FRONTEND_API_KEY` |
| `inject-config.js` | Inject `FRONTEND_API_KEY` alongside `API_URL` |
| `mcp-agent.html` | Add `Authorization` header to `fetch()` in `runAgent()` |

---

### 4b — Unified Data Folder + Property File Governance

#### Part 1 — Data Files

Tools that load data files (all 5 financial tools + DuckDB + MS Docs):

**`data/` folder structure:**
```
data/
  counterparties/
    exposure.json
    trades.json
    credit_limits.json
    var.json
    historical/
      2025-03-31.json
      2025-06-30.json
      2025-09-30.json
      2025-12-31.json
  duckdb/
    duckdb_analytics.db      (existing DuckDB database)
    *.csv / *.parquet        (any flat files DuckDB tools scan)
  msdocs/
    *.docx / *.xlsx          (Word/Excel files MS Doc tools read)
```

**`server.properties` — data file entries:**
```properties
# Root data folder (override to s3://bucket/prefix for cloud)
data.root=data

# Counterparty financial tools
tool.counterparty_exposure.data_file=counterparties/exposure.json
tool.trade_inventory.data_file=counterparties/trades.json
tool.credit_limits.data_file=counterparties/credit_limits.json
tool.historical_exposure.data_dir=counterparties/historical
tool.var_contribution.data_file=counterparties/var.json

# DuckDB tools
tool.duckdb.data_directory=duckdb

# MS Document tools
tool.msdoc.docs_directory=msdocs
```

**`DataLoader` utility** (`sajhamcpserver/sajha/core/data_loader.py`):
```python
class DataLoader:
    def load(self, relative_path: str) -> dict | list:
        root = properties.get('data.root', 'data')
        if root.startswith('s3://'):
            return self._load_s3(root, relative_path)
        return self._load_local(root, relative_path)

    def _load_local(self, root, path):
        full_path = Path(root) / path
        with open(full_path) as f:
            return json.load(f)

    def _load_s3(self, root, path):
        # boto3.client('s3').get_object(...)
        raise NotImplementedError("Set data.root=s3://bucket/prefix and install boto3")
```

Add `DataCache` with 60-second TTL so updated files are picked up without restart.

#### Part 2 — URL & Library Governance via Properties File

All tools that make HTTP calls or use external libraries should read their URLs and settings from `server.properties`, not hard-code them. This enables:
- Proxy configuration (swap URL base or add proxy prefix)
- Feature flags (enable/disable a tool group via `tool.yahoo.enabled=false`)
- URL overrides without code changes

**Complete URL governance table — all tools using external URLs:**

| Tool Group | Current Hard-coded URL | Properties Key |
|------------|----------------------|----------------|
| Yahoo Finance | `https://query2.finance.yahoo.com` | `tool.yahoo.base_url` |
| SEC EDGAR (data) | `https://data.sec.gov` | `tool.edgar.base_url` ← set to proxy URL when provisioned |
| SEC EDGAR (search) | `https://efts.sec.gov` | `tool.edgar.search_url` ← set to proxy URL when provisioned |
| SEC EDGAR (viewer) | `https://www.sec.gov` | `tool.edgar.viewer_url` ← set to proxy URL when provisioned |
| Tavily | `https://api.tavily.com/search` | `tool.tavily.api_url` |
| Fed Reserve (FRED) | `https://api.stlouisfed.org/fred` | `tool.fred.api_url` |
| ECB | `https://data-api.ecb.europa.eu/service/data` | `tool.ecb.api_url` |
| IMF | `http://dataservices.imf.org/REST/SDMX_JSON.svc` | `tool.imf.api_url` |
| Google Search | `https://www.googleapis.com/customsearch/v1` | `tool.google.api_url` |
| Investor Relations | (firm IR pages) | `tool.ir.base_url` |
| Bank of Canada | (BOC API) | `tool.boc.api_url` |
| ECB / BOJ / RBI / PBoC / Banque de France | (central bank APIs) | `tool.{bank}.api_url` |
| World Bank | (World Bank API) | `tool.worldbank.api_url` |
| FBI | (FBI API) | `tool.fbi.api_url` |

**Proxy pattern:** When your firm configures a proxy, update the relevant entries:
```properties
tool.yahoo.base_url=https://proxy.firm.internal/yahoo-finance
tool.edgar.base_url=https://proxy.firm.internal/sec-edgar
tool.edgar.search_url=https://proxy.firm.internal/sec-edgar-search
tool.edgar.viewer_url=https://proxy.firm.internal/sec-edgar-viewer
```
No code change required — SEC tools continue working unchanged once proxy URLs are set.

**`server.properties` additions:**
```properties
# External API URLs (override for proxy routing)
tool.yahoo.base_url=https://query2.finance.yahoo.com
tool.edgar.base_url=https://data.sec.gov
tool.edgar.search_url=https://efts.sec.gov
tool.edgar.viewer_url=https://www.sec.gov
tool.tavily.api_url=https://api.tavily.com/search
tool.fred.api_url=https://api.stlouisfed.org/fred
tool.ecb.api_url=https://data-api.ecb.europa.eu/service/data
tool.imf.api_url=http://dataservices.imf.org/REST/SDMX_JSON.svc
tool.google.api_url=https://www.googleapis.com/customsearch/v1
tool.boc.api_url=https://www.bankofcanada.ca/valet
tool.worldbank.api_url=https://api.worldbank.org/v2
tool.fbi.api_url=https://api.usa.gov/crime/fbi/cde
```

**Rule:** APIs keys stay in `.env`. URLs and infrastructure config stay in `server.properties`.

**Tool implementation change:** Each `__init__` reads its base URL from properties:
```python
self.base_url = properties.get('tool.yahoo.base_url', 'https://query2.finance.yahoo.com')
```

**Files to change:**
| File | Change |
|------|--------|
| `sajhamcpserver/sajha/core/data_loader.py` | New file — `DataLoader` + `DataCache` |
| `sajhamcpserver/config/server.properties` | Add all `tool.*` URL keys + `data.*` keys |
| `sajhamcpserver/sajha/tools/impl/yahoo_finance_tool.py` | Read `base_url` from properties |
| `sajhamcpserver/sajha/tools/impl/enhanced_edgar_tool.py` | Read `base_url`, `search_url`, `viewer_url` from properties |
| `sajhamcpserver/sajha/tools/impl/tavily_tool_refactored.py` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/fed_reserve_tool_refactored.py` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/european_central_bank_tool_refactored.py` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/imf_tool_refactored.py` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/google_search_tool_refactored.py` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/[all other central bank tools]` | Read `api_url` from properties |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py` | Read `data_directory` from properties |
| `sajhamcpserver/sajha/tools/impl/msdoc_tools_tool_refactored.py` | Read `docs_directory` from properties |
| `sajhamcpserver/sajha/tools/impl/counterparty_*_tool.py` (×5) | Replace hash generation with `DataLoader` |
| `scripts/generate_data.py` | New — one-time script to seed `data/` from existing hash logic |

---

### 4c — Bedrock Placeholder

**`agent/llm_factory.py`** (new file):
```python
def create_llm():
    provider = os.getenv('LLM_PROVIDER', 'anthropic')
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514'),
            temperature=0, streaming=True
        )
    elif provider == 'bedrock':
        # Uncomment after: pip install langchain-aws boto3
        # from langchain_aws import ChatBedrockConverse
        # return ChatBedrockConverse(
        #     model=os.getenv('BEDROCK_MODEL_ID'),
        #     region_name=os.getenv('AWS_REGION', 'us-east-1'),
        #     temperature=0, streaming=True
        # )
        raise NotImplementedError("Bedrock stub — uncomment block in llm_factory.py")
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {provider}")
```

**`.env` additions:**
```
LLM_PROVIDER=anthropic
# BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-20250514-v1:0
# AWS_REGION=us-east-1
```

**Files to change:**
| File | Change |
|------|--------|
| `agent/llm_factory.py` | New — `create_llm()` factory |
| `agent/agent.py` | Replace `ChatAnthropic(...)` with `create_llm()` |
| `.env` | Add `LLM_PROVIDER`, commented Bedrock vars |
| `requirements.txt` | Add commented `langchain-aws>=0.2.0` and `boto3>=1.35.0` |

---

### 4d — Source Attribution Redesign (System Prompt)

**Current prompt rule:**
```
After every specific figure, append: [src:tool_name]
```

**Problem:** Shows tool name (e.g., `[src:get_counterparty_exposure]`) — not the actual source data came from.

**New rule:** Every tool response JSON includes a `_source` field. The agent should cite that field value, not the tool name.

**`_source` field per tool type:**

| Tool Type | `_source` value example |
|-----------|------------------------|
| Data-file tools (financial) | `data/counterparties/exposure.json` |
| Yahoo Finance (Tavily-backed) | `https://finance.yahoo.com/quote/AAPL` (from Tavily result URL) |
| SEC EDGAR (proxy-routed) | `https://data.sec.gov/submissions/CIK0000320193.json` (actual URL called, after proxy rewrite) |
| Tavily web search | `https://reuters.com/article/...` (first result URL) |
| FRED (Fed Reserve) | `https://api.stlouisfed.org/fred/series/observations?series_id=DFF` |
| ECB | `https://data-api.ecb.europa.eu/service/data/FM/...` |
| IMF | `http://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/...` |
| DuckDB | `data/duckdb/duckdb_analytics.db` |
| MS Docs | `data/msdocs/counterparty_exposure_Q4.xlsx` |

**Updated system prompt rule** (`agent/prompt.py`):
```
SOURCE ATTRIBUTION:
Every tool response includes a "_source" field identifying where the data came from
(a URL, a file path, or an API endpoint). After every specific figure, date, or fact
taken from a tool result, append immediately:
  [src:{_source value from that tool's response}]

Examples:
  Net exposure $26.2M [src:data/counterparties/exposure.json]
  Fed Funds Rate 5.25% [src:https://api.stlouisfed.org/fred/series/observations?series_id=DFF]
  RBC 10-K filed 2025-02-14 [src:https://www.sec.gov/Archives/edgar/data/1000177/...]

Do NOT annotate general commentary or your own reasoning.
```

**Implementation requirement:** Every tool's `execute()` method must include `_source` in its returned dict. This is a cross-cutting change across all tool implementations — both existing and new.

---

## Full File Change Summary

| File | Streams |
|------|---------|
| `agent/agent.py` | 1, 4c |
| `agent/summariser.py` *(new)* | 1 |
| `agent/prompt.py` | 1, 4d |
| `agent/llm_factory.py` *(new)* | 4c |
| `agent_server.py` | 4a |
| `mcp-agent.html` | 2, 4a |
| `sajhamcpserver/sajha/tools/impl/tavily_yahoo_finance_tool.py` *(new)* | 3 |
| `sajhamcpserver/sajha/core/data_loader.py` *(new)* | 4b |
| `sajhamcpserver/sajha/tools/impl/yahoo_finance_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/enhanced_edgar_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/tavily_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/fed_reserve_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/european_central_bank_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/imf_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/google_search_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/[all other central bank/external tools]` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/duckdb_olap_tools_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/msdoc_tools_tool_refactored.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/counterparty_exposure_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/trade_inventory_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/credit_limits_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/historical_exposure_tool.py` | 4b, 4d |
| `sajhamcpserver/sajha/tools/impl/var_contribution_tool.py` | 4b, 4d |
| `sajhamcpserver/config/server.properties` | 4b |
| `sajhamcpserver/config/tools/tavily_yahoo_*.json` *(new × 3)* | 3 |
| `sajhamcpserver/config/tools/yahoo_*.json` *(disable × 3)* | 3 |
| `.env` | 1, 4a, 4c |
| `requirements.txt` | 4c |
| `inject-config.js` | 4a |
| `data/` folder *(new)* | 4b |
| `scripts/generate_data.py` *(new)* | 4b |

---

## Recommended Execution Sequence

1. **Stream 2** — UI fix. One function, 8 lines, no backend change.
2. **Stream 4c** — LLM factory. Pure refactor, no behaviour change.
3. **Stream 4d** — Add `_source` to all existing tool responses + update system prompt. Groundwork for attribution before Tavily tools are built.
4. **Stream 4a** — API key auth. Straightforward security layer.
5. **Stream 4b (URLs)** — Move all URLs to properties file. No user-visible change, enables proxy routing.
6. **Stream 3** — Build Tavily tools, validate side-by-side with existing ones, then disable old configs.
7. **Stream 4b (Data folder)** — Generate seed files, wire `DataLoader`, move DuckDB/msdocs dirs.
8. **Stream 1** — Summarisation middleware. Build on stable foundation.
