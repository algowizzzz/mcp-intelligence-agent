# Claude Code Handoff — Market Risk Digital Worker Connectors

## Context
The goal is making all four connectors live for the Market Risk Digital Worker:
**Teams (T2/T3), Outlook (T4), Jira (T5), Confluence (pending)**

**Standing rule**: All connector tests must be run via direct SAJHA API calls — no LLM calls.

---

## Current State

### What Was Just Done (this session)
1. ✅ **Teams app v1.0.1 (`market_risk_worker.zip`)** — rebuilt with correct `botId: "73a01a51-bd87-4e71-88a4-abcaf4fefebc"` (valid Bot Framework bot registered in Teams Developer Portal) and RSC `ChannelMessage.Send.Group` permission
2. ✅ **Admin Center catalog update** — uploaded v1.0.1 via Teams Admin Center → app detail page → "New version / Upload file"; confirmed "Updated Market Risk Worker in your list."
3. ✅ **App installed in B-Pulse Alerts** — Market Risk Worker v1.0.1 successfully installed in the Market Risk team's B-Pulse Alerts channel; "About this bot" confirmation dialog appeared, confirming RSC grant
4. ✅ **Root cause resolved** — `ChannelMessage.Send` does NOT exist as a Microsoft Graph Application permission; RSC `ChannelMessage.Send.Group` via team app installation is the correct app-only path
5. ✅ **`teams_tools.py` direct endpoint** — `TeamsSendMessageTool` posts directly to `teams/{team_id}/channels/{channel_id}/messages` (no Chat fallback needed now that RSC is active)

### Code State
`sajhamcpserver/sajha/tools/impl/teams_tools.py` — `TeamsSendMessageTool.execute()` posts directly to the channel endpoint. No fallback needed — RSC `ChannelMessage.Send.Group` is now granted via the installed app.

---

## Connector Status

| ID | Tool | Status | Notes |
|----|------|--------|-------|
| T2 | `teams_list_channels` | ✅ Was passing | Read-only, `Channel.ReadBasic.All` granted |
| T3 | `teams_send_message` | ✅ RSC installed — ready to verify | v1.0.1 installed in B-Pulse Alerts; `ChannelMessage.Send.Group` RSC granted |
| T4 | `outlook_read_email` | 🔲 Ready to test | Exchange Online mailbox now provisioned |
| T5 | `jira_list_projects` / `jira_search_issues` | ✅ Was passing | Atlassian token configured |
| T6 | confluence tools | ❌ Not set up | See below |

---

## Immediate Next Steps

### Step 1 — Run Connector Tests (Terminal)

Start the servers on the local Mac (not in the Cowork sandbox which has proxy restrictions):

```bash
# Terminal 1
cd react_agent/sajhamcpserver
../venv/bin/python run_server.py

# Terminal 2
cd react_agent
uvicorn agent_server:app --port 8000 --reload
```

Then run the test script:
```bash
cd react_agent
python3 test_connectors.py
```

Expected outcomes:
- **T2**: ✅ PASS (was passing before)
- **T3**: ✅ PASS via `POST /teams/{team_id}/channels/{channel_id}/messages` (RSC `ChannelMessage.Send.Group` now active)
- **T4**: ✅ PASS (Exchange mailbox now exists, Mail.Read/Mail.ReadWrite already granted)
- **T5**: ✅ PASS (was passing before)

**T3 troubleshooting**: If T3 returns 403 "Forbidden":
- The RSC grant may need a few minutes to propagate after app installation — wait 2-3 min and retry
- Verify the app is installed: Teams → Market Risk team → Manage team → Apps tab → confirm "Market Risk Worker" appears
- The channel_id must be: `19:SHmWm9n11mv8FTPMTv2XpTyDbcj9bnLntOzTD_PW7KQ1@thread.tacv2`

If T4 fails with `MailboxNotEnabledForRESTAPI`, the Exchange mailbox may need a few more minutes to provision (can take up to 15 min after license assignment).

---

### Step 2 — Set Up Confluence

Confluence is the only connector with zero setup done. Current `workers.json` has placeholder values:
```json
"confluence_space_key": "PENDING_CONFLUENCE_SETUP",
"confluence_parent_page_id": "PENDING_CONFLUENCE_SETUP"
```

**2a. Add Confluence to the Atlassian org**
- Go to https://admin.atlassian.com → select the DeepLearnHQ org → Products → Add Confluence
- Start a free trial if no paid plan

**2b. Create the "Market Risk" Confluence space**
- Go to https://sa5425592.atlassian.net/wiki
- Create a new space → call it "Market Risk" → note the Space Key (e.g. `MRISK` or `MR`)
- Create a parent page called "Market Risk Worker" in that space → note the page ID from the URL

**2c. Update workers.json**
Edit `sajhamcpserver/config/workers.json` for the "Market Risk Worker" entry:
```json
"confluence_space_key": "<actual_space_key>",
"confluence_parent_page_id": "<actual_page_id>"
```

**2d. Test Confluence tools**
```bash
# In the test_connectors.py or via direct curl:
python3 -c "
import json, urllib.request
payload = json.dumps({
  'tool': 'confluence_search',
  'arguments': {
    'query': 'Market Risk',
    '_worker_context': {
      'atlassian_email': 'sa5425592@gmail.com',
      'atlassian_token': '<ATLASSIAN_API_TOKEN>',  # see .env / CREDENTIALS.md
      'atlassian_base_url': 'https://sa5425592.atlassian.net',
      'confluence_space_key': '<space_key>',
    }
  }
}).encode()
req = urllib.request.Request('http://localhost:3002/api/tools/execute', data=payload,
  headers={'Content-Type':'application/json','Authorization':'sja_full_access_admin'})
print(json.loads(urllib.request.urlopen(req,timeout=15).read()))
"
```

---

## Key Credentials / IDs (for reference)

```
Azure App:     RiskGPT-MCP-Connector
App ID:        d39a3d30-eb6d-4969-98aa-82bab2ca5b22
Tenant ID:     a241c412-f9f1-4461-8992-5c0b24ea8578
Client Secret: <AZURE_CLIENT_SECRET>  # see .env / CREDENTIALS.md

Teams Team:    Market Risk (33793fc4-5b65-4a4f-b7b6-e11bcf3ffb54)
Teams Channel: B-Pulse Alerts (19:SHmWm9n11mv8FTPMTv2XpTyDbcj9bnLntOzTD_PW7KQ1@thread.tacv2)
Outlook user:  SaadAhmed@DeepLearnHQ.onmicrosoft.com

Atlassian:     sa5425592@gmail.com / base: https://sa5425592.atlassian.net
Jira project:  MRISK (board 35)
SAJHA API key: sja_full_access_admin  (full tool access)
SAJHA user:    risk_agent / RiskAgent2025!  (note: auth uses password_hash field, compare works)
```

---

## Azure AD Permissions Granted (RiskGPT-MCP-Connector)

All 14 permissions have admin consent (green checkmarks):
- `Channel.ReadBasic.All` (App)
- `ChannelMessage.Read.All` (App)
- `Chat.Read.All` (App)
- `Chat.ReadWrite.All` (App) ← newly added this session
- `Files.Read.All` (App)
- `Mail.Read` (App)
- `Mail.ReadWrite` (App)
- `Mail.Send` (App)
- `Team.ReadBasic.All` (App)
- `TeamMember.Read.All` (App)
- `User.Read.All` (App)
- + 3 more

---

## Notes on Sandbox Limitations

If running tests from within the Cowork bash sandbox, ALL Microsoft Graph and Atlassian API calls will fail with proxy errors. The sandbox proxy allowlist blocks `login.microsoftonline.com`, `graph.microsoft.com`, and `atlassian.net`. Tests must be run from the user's Mac terminal where the venv Python has full internet access.
