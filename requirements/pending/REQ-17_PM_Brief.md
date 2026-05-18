# REQ-17 — PM Brief: Adopt Upstream SAJHA As-Is

**Status:** Pending — Awaiting decision on architectural option
**Date:** 2026-05-17
**Owner:** Saad Ahmed
**Companion docs:** [REQ-17 technical requirements](REQ-17_SAJHA_Upstream_Sync.md) · [Jr dev stories](REQ-17_Jr_Dev_Stories.md)

---

## TL;DR

Leadership has asked us to **stop maintaining our own fork of SAJHA** and use the official upstream version (https://github.com/ajsinha/sajhamcpserver, v5.0.0) without changes — adding our custom tools on top. Doing this cleanly is **~2 weeks of focused work**. We unlock 500 financial tools the upstream maintainer ships, stop paying merge-conflict tax forever, and our multi-worker behavior gets restructured (not lost). One real risk to call out: the upstream version doesn't have our multi-worker data isolation built in — we need to move that logic into our agent layer.

---

## Why this matters

**Today.** We carry a 715-file Flask-based fork of SAJHA inside our repo (`sajhamcpserver/`). It's frozen at v2.9.8. Every upstream release we ignore is technical debt accumulating. Our fork has ~40 tools; upstream now ships 500 (FMP, OpenBB, FRED, Alpha Vantage, etc.).

**After this work.** Our repo references upstream as a pinned dependency. Our 31 custom tools (IRIS CCR, EDGAR enrichment, Tavily, connectors, BM25, Python executor, etc.) live in a separate "tools-pack" that drops into upstream cleanly. Upstream releases become a `git pull + bump tag` — no rebases.

**Strategic upside.** Aligns our work with the upstream maintainer (Ashutosh Sinha). Lets us pull in his future improvements (already 460 financial tools, new MCP 2025-11-25 protocol with async Tasks + Sampling). Frees engineering hours we currently spend reconciling drift.

---

## What changes

| Today | After REQ-17 |
|---|---|
| 715 files of forked SAJHA shipped in our repo | A single submodule pin pointing at upstream v5.0.0 |
| Our 31 custom tools live mixed into upstream code | All 31 in a clean `tools-pack/` folder |
| Multi-worker isolation baked into SAJHA Flask request context | Moved into our agent layer; tools read worker context from HTTP headers |
| `~40 tools` available to the agent | `500 upstream + 31 ours = 531 tools` |
| Flask + SocketIO + EventLet under the hood | FastAPI + uvicorn + SSE + WebSocket |
| MCP protocol pre-2025 | MCP 2025-11-25 (Tasks, Elicitation, Sampling) |
| Updates from upstream: manual port + rebase | Updates from upstream: `git submodule update` |

**For users**, the visible change is "more tools available" and a brief outage during cutover. No UI rewrite. Login, chat, admin panel — same.

---

## The one architectural question I need a decision on

The upstream version has **no concept of multi-worker isolation** (each "Market Risk Worker" / "Operational Risk" / etc. having its own data). Today this is baked into our fork via 5 framework files. We have two ways to preserve it:

1. **Option A (recommended) — Move worker isolation into our agent layer.** Each custom tool reads worker context from HTTP request headers instead of from SAJHA's internals. Cleanest separation; upstream truly stays untouched.

2. **Option B — Fork upstream v5.0.0 and port our 5 framework files into it (Flask → FastAPI).** Worker isolation stays inside SAJHA like today. But this *violates the directive* — we're modifying upstream.

I recommend Option A. Same effort. Long-term cheaper. Aligns with the directive.

---

## Time + risk

**Engineering: ~2 weeks of focused work.** Broken into 10 stories (see `REQ-17_Jr_Dev_Stories.md`) — most are 1 day or less.

**Risk register:**

| Risk | Likelihood | Impact | Plan |
|---|---|---|---|
| Upstream plugin system doesn't expose our tools cleanly | Low | High | 1-day spike before committing |
| Custom tools break when not running inside Flask | Medium | Medium | Centralized worker-context helper; tool-by-tool audit |
| MCP protocol changes break our agent's SSE consumption | Medium | Medium | Bundle protocol adaptation into same PR |
| Multi-worker data leak regression | Low | High | Hard gate: e2e isolation test must pass before merge |
| Tool name conflicts (upstream has EDGAR tools, so do we) | Low | Low | Audit + rename where needed |

---

## What gets bigger / what gets smaller

**Bigger:** Tool catalog (40 → 531). Compliance with current MCP spec. Engineering velocity on tools that *aren't* the framework.

**Smaller:** Files in our repo (drop ~715 fork files in exchange for ~120 tools-pack files). Time spent on rebase/conflict resolution (today: nontrivial; after: ~0).

---

## What we explicitly are NOT doing in this REQ

- Not rewriting the agent's LangGraph layer.
- Not changing the user-facing UI.
- Not migrating to a different LLM (xAI/Grok stays as today).
- Not contributing our multi-worker design back to upstream — that's a possible follow-up REQ-18.
- Not removing functionality. Every existing capability remains; we're just hosting it differently.

---

## Decisions I need from you

1. **Greenlight Option A (recommended) vs Option B?** Default: A.
2. **Submodule vs vendored clone of upstream?** Default: git submodule pinned to v5.0.0.
3. **Cutover timing.** This is best done in one branch over ~2 weeks rather than incrementally. Are there active demos / customer escalations that would block?
4. **Test bar.** Today UAT is manual + Playwright. Is the existing test suite (236 tests, all passing) enough to gate the cutover, or do you want a new isolation-specific test suite first?

---

## Next steps if approved

1. Day 1: spike to confirm plugin system works as expected (de-risks the whole approach).
2. Days 2–8: build tools-pack, adapt agent, write isolation tests.
3. Days 9–11: cutover branch + UAT.
4. Day 12: merge, monitor.

If the spike on day 1 fails, we revisit Option B before continuing.

---

## Bottom line

> The upstream maintainer is doing the bulk of SAJHA's roadmap work for us. We have been carrying a fork that gets staler every week. Two weeks of focused work cleans this up permanently and unlocks 500 new tools. The only real complexity is moving our worker-isolation logic up into our agent — and that work is contained, testable, and well-scoped.
