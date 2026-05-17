# REQ-06 — Branding: B-Pulse Digital Workers
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** Rebrand all user-facing interfaces and system messages from "RiskGPT" / "SAJHA MCP Server" / "Market Risk Digital Worker" to the unified brand **B-Pulse Digital Workers**.

---

## 1. Background & Current Brand Inventory

A full audit of existing brand elements across all HTML and configuration files:

| File | Current Brand Element | Location |
|---|---|---|
| `public/login.html` | `<title>RiskGPT — Sign In</title>` | `<head>` |
| `public/login.html` | `RiskGPT` heading (brand mark box) | `<div class="brand-name">` |
| `public/login.html` | No footer/disclaimer | — |
| `public/admin.html` | `<title>RiskGPT Admin Console</title>` | `<head>` |
| `public/admin.html` | Sidebar brand icon + label (32px) | `<div class="brand-icon">` |
| `public/admin.html` | No footer/disclaimer | — |
| `public/mcp-agent.html` | `<title>Market Risk Digital Worker</title>` | `<head>` |
| `public/mcp-agent.html` | Sidebar header / agent name display | `<div class="agent-header">` |
| `public/mcp-agent.html` | No footer/disclaimer | — |
| `public/index.html` | `<title>MCP Intelligence Agent</title>` | `<head>` |
| `application.properties` | `app.name=SAJHA MCP Server` | Server config |
| `application.properties` | `app.description=SAJHA Financial Risk Intelligence Platform` | Server config |

---

## 2. New Brand Identity

### 2.1 Brand Name

**Primary name:** `B-Pulse Digital Workers`
**Short form (where space is limited):** `B-Pulse`
**Agent identity (in chat):** `B-Pulse` (the agent refers to itself as B-Pulse when asked)
**Admin console name:** `B-Pulse Admin Console`

### 2.2 Taglines

| Context | Tagline |
|---|---|
| Login page subtitle | `Intelligent Digital Workers for Financial Risk` |
| Chat welcome message | `B-Pulse Digital Workers — AI-powered risk intelligence at your fingertips.` |
| Admin console subtitle | `Worker & Platform Management` |

### 2.3 Disclaimer Text

The following disclaimer must appear in the footer of all user-facing pages:

> **B-Pulse Digital Workers** is an AI-assisted intelligence platform. All outputs are for informational purposes only and do not constitute financial, legal, or investment advice. Information may be incomplete or subject to change. Always validate critical decisions with qualified professionals and authoritative sources. Usage is subject to your organization's acceptable use policy.

---

## 3. File-by-File Changes

### 3.1 `public/login.html`

**Title:**
```html
<!-- Before -->
<title>RiskGPT — Sign In</title>

<!-- After -->
<title>B-Pulse — Sign In</title>
```

**Brand heading (inside the login card brand mark):**
```html
<!-- Before -->
<div class="brand-name">RiskGPT</div>

<!-- After -->
<div class="brand-name">B-Pulse</div>
<div class="brand-tagline">Digital Workers</div>
```

**Brand mark styling** — add tagline style:
```css
.brand-tagline {
    font-size: 11px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #888;
    margin-top: 2px;
}
```

**Footer disclaimer** — add before `</body>`:
```html
<footer class="login-footer">
  <p class="disclaimer-text">
    <strong>B-Pulse Digital Workers</strong> is an AI-assisted intelligence platform.
    Outputs are for informational purposes only and do not constitute financial, legal,
    or investment advice. Validate critical decisions with qualified professionals.
  </p>
</footer>
```

```css
.login-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 10px 24px;
    background: rgba(10, 10, 10, 0.95);
    border-top: 1px solid #1f1f1f;
    text-align: center;
}
.disclaimer-text {
    font-size: 10px;
    color: #555;
    line-height: 1.5;
    max-width: 700px;
    margin: 0 auto;
}
.disclaimer-text strong {
    color: #777;
}
```

### 3.2 `public/admin.html`

**Title:**
```html
<!-- Before -->
<title>RiskGPT Admin Console</title>

<!-- After -->
<title>B-Pulse Admin Console</title>
```

**Sidebar brand section** — typically a logo/icon + label area:
```html
<!-- Before -->
<div class="sidebar-brand">
  <div class="brand-icon">...</div>
  <span class="brand-label">RiskGPT</span>
</div>

<!-- After -->
<div class="sidebar-brand">
  <div class="brand-icon"><!-- existing icon SVG -->
  </div>
  <div class="brand-label-group">
    <span class="brand-label">B-Pulse</span>
    <span class="brand-sublabel">Admin Console</span>
  </div>
</div>
```

```css
.brand-label-group {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
}
.brand-sublabel {
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    color: #666;
}
```

**Footer disclaimer** — add before `</body>`:
```html
<footer class="admin-footer">
  <span class="disclaimer-text">
    B-Pulse Digital Workers — AI outputs are informational only. Not financial advice.
    &copy; 2026 B-Pulse. All rights reserved.
  </span>
</footer>
```

```css
.admin-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 6px 16px;
    background: #080808;
    border-top: 1px solid #1a1a1a;
    text-align: center;
    z-index: 10;
}
.admin-footer .disclaimer-text {
    font-size: 10px;
    color: #444;
}
```

**Adjust body bottom padding** to prevent content being obscured by fixed footer:
```css
body { padding-bottom: 30px; }
```

### 3.3 `public/mcp-agent.html`

**Title:**
```html
<!-- Before -->
<title>Market Risk Digital Worker</title>

<!-- After -->
<title>B-Pulse Digital Workers</title>
```

**Sidebar header / agent identity:**
```html
<!-- Find the agent name / header area in sidebar and update: -->
<!-- Before (any occurrence of "Market Risk", "RiskGPT", or agent name) -->
<div class="agent-name">Market Risk Digital Worker</div>

<!-- After -->
<div class="agent-name">B-Pulse</div>
<div class="agent-subtitle">Digital Workers</div>
```

**Welcome/splash message** in the empty chat state (shown before first message):
```html
<!-- Find the welcome screen HTML and update: -->
<div class="welcome-title">B-Pulse Digital Workers</div>
<div class="welcome-subtitle">AI-powered risk intelligence for financial professionals</div>
```

**Footer disclaimer** — add inside the chat interface, below the input area (fixed):
```html
<div class="chat-disclaimer">
  B-Pulse Digital Workers — AI outputs are for informational purposes only and do not
  constitute financial, legal, or investment advice. Always verify with authoritative sources.
</div>
```

```css
.chat-disclaimer {
    font-size: 10px;
    color: #3a3a3a;
    text-align: center;
    padding: 4px 16px;
    border-top: 1px solid #1e1e1e;
    line-height: 1.4;
    flex-shrink: 0;
}
```

**Ensure the disclaimer is inside the flex column** of the chat layout so it does not overlay content.

### 3.4 `public/index.html`

**Title:**
```html
<!-- Before -->
<title>MCP Intelligence Agent</title>

<!-- After -->
<title>B-Pulse Digital Workers</title>
```

Apply same branding pattern as mcp-agent.html if this page is still user-facing.

### 3.5 `sajhamcpserver/config/application.properties`

```properties
# Before
app.name=SAJHA MCP Server
app.description=SAJHA Financial Risk Intelligence Platform

# After
app.name=B-Pulse Digital Workers
app.description=B-Pulse AI-powered Digital Workers Platform
```

### 3.6 Agent Self-Identification (System Prompt)

In `agent/prompt.py`, update the agent's identity in the system prompt:

```python
# Find and replace any reference to "RiskGPT" or "SAJHA" in the fallback prompt:
_FALLBACK_PROMPT = """You are B-Pulse, an AI-powered financial risk intelligence assistant built on the B-Pulse Digital Workers platform.

You help financial risk professionals with counterparty credit risk analysis, market risk reporting, regulatory intelligence, and portfolio monitoring.

When asked about your identity:
- You are "B-Pulse" — an AI assistant powered by the B-Pulse Digital Workers platform
- Do not refer to yourself as Claude, ChatGPT, or any other AI model name
- You can say you are "powered by advanced AI" without naming the underlying model

[rest of system prompt follows...]
"""
```

---

## 4. Browser Tab Icon (Favicon)

If a favicon does not currently exist or is the default browser favicon, add a branded one:

1. Create a simple SVG favicon representing "B" or a pulse icon:
```html
<!-- In <head> of all HTML files: -->
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
```

2. Create `public/favicon.svg`:
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="6" fill="#0d1117"/>
  <text x="16" y="22" font-family="system-ui,sans-serif" font-size="18"
        font-weight="700" fill="#e0e0e0" text-anchor="middle">B</text>
</svg>
```

---

## 5. Error Pages & Messages

Any error messages, 404 pages, or API error responses that currently reference "RiskGPT" or "SAJHA" must be updated:

**Search pattern:** `grep -r "RiskGPT\|SAJHA\|sajha\|riskgpt" public/ agent/ sajhamcpserver/ --include="*.html" --include="*.py" --include="*.json" --include="*.properties" -l`

After search, review each occurrence and update to "B-Pulse Digital Workers" where user-facing, or leave as internal identifiers where appropriate (e.g. Python class names, internal variable names do not need to change).

---

## 6. What NOT to Change

The following identifiers are internal and must NOT be renamed (doing so would break functionality):

- Python class names: `SajhaMCPServer`, `ConnectorsRegistry`, etc.
- API route prefixes: `/api/super/`, `/api/admin/`, `/api/fs/`, `/api/agent/`
- Worker IDs: `w-market-risk`, `w-e74b5836`, etc.
- Data file paths: `sajhamcpserver/data/`, `domain_data/`, etc.
- Config file names: `users.json`, `workers.json`, `connectors.json`
- Git commit history and branch names

---

## 7. Acceptance Criteria

- [ ] Browser tab title shows "B-Pulse — Sign In" on login page
- [ ] Browser tab title shows "B-Pulse Admin Console" on admin page
- [ ] Browser tab title shows "B-Pulse Digital Workers" on chat page
- [ ] All user-visible instances of "RiskGPT" replaced with "B-Pulse" (verified by grep)
- [ ] All user-visible instances of "Market Risk Digital Worker" replaced with "B-Pulse Digital Workers"
- [ ] Disclaimer text appears in footer of all three pages (login, admin, chat)
- [ ] Disclaimer is not obstructing any interactive UI elements
- [ ] Agent responds to "What are you?" with B-Pulse identity, not "RiskGPT" or model name
- [ ] `application.properties` `app.name` updated to "B-Pulse Digital Workers"
- [ ] Internal Python class names, API routes, and data paths unchanged
- [ ] Favicon displays correctly in browser tab on all pages

---

## 8. Out of Scope

- Logo design or brand guidelines beyond the text and basic SVG favicon defined here
- Marketing materials or external documentation
- Mobile app branding
- Email template branding
