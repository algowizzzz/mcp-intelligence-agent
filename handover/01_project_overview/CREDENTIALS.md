# B-Pulse Platform — Master Credentials Reference

> **KEEP THIS FILE PRIVATE.** Do not commit to git or share publicly.
> Last updated: 2026-04-04

---

## Microsoft Azure / M365

| Field | Value |
|-------|-------|
| **App Name** | RiskGPT-MCP-Connector |
| **Tenant ID** | `a241c412-f9f1-4461-8992-5c0b24ea8578` |
| **Client ID (App ID)** | `d39a3d30-eb6d-4969-98aa-82bab2ca5b22` |
| **Client Secret** | `<REDACTED — see local copy or Azure portal>` |
| **Secret Label** | B-Pulse Connector 2026 |
| **Secret Expiry** | ~24 months from creation (~April 2028) |
| **Tenant Domain** | DeepLearnHQ.onmicrosoft.com |
| **Portal** | https://portal.azure.com → App registrations → RiskGPT-MCP-Connector |

### Teams / Outlook (connector_scope — Market Risk Worker)

| Field | Value |
|-------|-------|
| **Teams Team Name** | Market Risk |
| **Teams Team ID** | `33793fc4-5b65-4a4f-b7b6-e11bcf3ffb54` |
| **Teams Channel Name** | B-Pulse Alerts |
| **Teams Channel ID** | `19:SHmWm9n11mv8FTPMTv2XpTyDbcj9bnLntOzTD_PW7KQ1@thread.tacv2` |
| **Outlook User** | SaadAhmed@DeepLearnHQ.onmicrosoft.com |

---

## Atlassian (Jira + Confluence)

| Field | Value |
|-------|-------|
| **Account Email** | sa5425592@gmail.com |
| **Site URL** | https://sa5425592.atlassian.net |
| **API Token Label** | B-Pulse MCP Server |
| **API Token** | `<REDACTED — see local copy or Atlassian token management>` |
| **API Token Mgmt** | https://id.atlassian.com/manage-profile/security/api-tokens |

### Jira (connector_scope — Market Risk Worker)

| Field | Value |
|-------|-------|
| **Project Key** | MRISK |
| **Board ID** | `35` |
| **Jira Site URL** | https://sa5425592.atlassian.net |

### Confluence (connector_scope — Market Risk Worker)

| Field | Value |
|-------|-------|
| **Space Key** | PENDING — create "Market Risk" space first |
| **Parent Page ID** | PENDING — note ID after space creation |

---

## B-Pulse Platform Accounts

| Role | Username | Password |
|------|----------|----------|
| Agent / End-user | `risk_agent` | `RiskAgent2025!` |
| Admin | `admin` | *(set during install)* |

### Ports
| Service | Port | URL |
|---------|------|-----|
| Agent Server (FastAPI) | 8000 | http://localhost:8000 |
| SAJHA MCP Server (Flask) | 3002 | http://localhost:3002 |

---

## Config File Locations

| File | Purpose |
|------|---------|
| `sajhamcpserver/config/connectors.json` | Connector credentials (source of truth for SAJHA) |
| `sajhamcpserver/config/workers.json` | Worker definitions, connector_scope (team/channel/project IDs) |
| `sajhamcpserver/config/application.properties` | Data paths, feature flags, hot-reload interval |

---

## Pending Items

- [ ] Confluence: provision the app at admin.atlassian.com → Apps → Add app → Confluence
- [ ] Confluence: create "Market Risk" space → note Space Key + Parent Page ID
- [ ] Update `workers.json` `confluence_space_key` and `confluence_parent_page_id` once known
- [ ] Outlook: verify SaadAhmed@DeepLearnHQ.onmicrosoft.com mailbox at https://outlook.office.com
- [ ] Outlook: create "B-Pulse Test" folder in mailbox (per REQ-02a checklist)
- [ ] Restart SAJHA MCP server to load updated connectors.json into memory
