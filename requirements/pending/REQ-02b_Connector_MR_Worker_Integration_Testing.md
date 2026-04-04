# REQ-02b — Connector MR Worker Integration & Testing
**Status:** Pending Implementation
**Version:** 1.1 (Updated 2026-04-04 — references existing codebase config)
**Scope:** Configure the Market Risk worker with live connector credentials and run end-to-end integration tests.
**Prerequisite:** REQ-02a completed — all credentials and browser sessions established.

---

## 1. Current State in Codebase

Before doing anything, understand what is already configured:

### 1.1 Worker Scope Already Set (`config/workers.json`)

The `w-market-risk` worker already has placeholder connector scope values:

```json
"connector_scope": {
  "microsoft_azure": {
    "teams_team_id": "qa-team",
    "sharepoint_site_url": "https://qa.sharepoint.com/sites/QA"
  },
  "atlassian": {
    "confluence_space_key": "RISK",
    "jira_project_key": "CCR"
  }
}
```

These are **placeholder/test values** from a previous QA setup. They need to be replaced with the real values collected in REQ-02a.

### 1.2 Connector Registry (`config/connectors.json`)

Currently only `microsoft_azure` is defined, with status `not_configured` and empty credentials. Atlassian is not yet registered at all.

### 1.3 Environment (`.env`)

No Microsoft 365 or Atlassian credentials exist in `.env`. Only `ANTHROPIC_API_KEY` and `TAVILY_API_KEY` are configured. All connector credentials will be entered via the Admin Console UI, which writes to `config/connectors.json`.

---

## 2. Known Issues to Resolve Before Testing

### BUG-CONN-001 — Credentials Stored Plaintext

`connectors_registry.py` line 60 references a `decrypt(v)` function that is stubbed. Credentials written to `config/connectors.json` are stored in plaintext.

**For testing purposes:** Acceptable in a local/sandboxed environment. Ensure `config/connectors.json` is in `.gitignore` and never committed to source control.

**Before production:** Implement AES-256-GCM encryption (tracked separately, see REQ-07 credential encryption requirement).

### BUG-CONN-002 — Token Cache Verification

`sajhamcpserver/sajha/core/token_cache.py` is referenced by `MSGraphClient` but may not be fully implemented. Verify the file exists and the token refresh logic handles expiry correctly before running Outlook/Teams tests.

### BUG-CONN-003 — Missing `outlook_user_email` in Worker Scope

The `teams_get_meetings` tool reads calendar data via `outlook_user_email` from the worker's connector scope. This field is not currently set for `w-market-risk`. Add it when updating the scope in Step 3 below.

---

## 3. Setup Steps

### Step 1 — Configure Microsoft 365 Connector

1. Log into B-Pulse Admin Console at `http://localhost:8000/admin.html` as `risk_agent` / `RiskAgent2025!`
2. Navigate to **Connectors** → **Overview** tab
3. Click **Configure** on the Microsoft 365 card
4. Enter the values from REQ-02a:
   - Display Name: `Microsoft 365`
   - Tenant ID: _(from REQ-02a)_
   - Client ID: _(from REQ-02a)_
   - Client Secret: _(from REQ-02a)_
5. Click **Test Connection** — expect green success message
6. Click **Save**
7. Connector card status should now show **Connected**

### Step 2 — Configure Atlassian Connector

1. In **Connectors** → **Overview** → click **Configure** on the Atlassian card (or **Add Connector** if Atlassian is not yet listed)
2. Enter:
   - Display Name: `Atlassian`
   - Email: _(Atlassian account email from REQ-02a)_
   - API Token: _(from REQ-02a)_
   - Confluence URL: _(e.g. `https://yourcompany.atlassian.net/wiki`)_
   - Jira URL: _(e.g. `https://yourcompany.atlassian.net`)_
3. Click **Test Connection** → expect green success
4. Click **Save**

### Step 3 — Update Worker Scope for w-market-risk

1. In **Connectors** → **Worker Mapping** tab
2. Select **Market Risk Worker (w-market-risk)**
3. Update **Microsoft 365 scope** — replace the placeholder `qa-team` values:
   - Teams Team ID: _(real GUID from REQ-02a step 2.4)_
   - Outlook User Email: _(mailbox email from REQ-02a step 3.2)_
   - Remove or update SharePoint Site URL
4. Click **Save Microsoft 365 Scope**
5. Update **Atlassian scope** — replace the placeholder `RISK` / `CCR` values:
   - Confluence Space Key: _(real space key from REQ-02a step 4.2)_
   - Jira Project Key: _(real project key from REQ-02a step 5.2)_
   - Jira Board ID: _(from REQ-02a step 5.2)_
   - Confluence Parent Page ID: _(from REQ-02a step 4.3)_
6. Click **Save Atlassian Scope**

**Verify in `config/workers.json`** that the connector_scope now has the real values (not `qa-team`, `RISK`, `CCR`).

### Step 4 — Enable Connector Tools for Worker

1. In Admin Console → **Tools** tab
2. Confirm the following tools are enabled for the Market Risk worker. If not, enable and save:

**Teams:** `teams_list_channels`, `teams_get_messages`, `teams_send_message`, `teams_list_members`, `teams_get_meetings`, `teams_get_channel_files`

**Outlook:** `outlook_read_email`, `outlook_search_email`, `outlook_send_email`, `outlook_reply_email`, `outlook_list_folders`, `outlook_get_email`

**Confluence:** `confluence_list_spaces`, `confluence_search`, `confluence_get_page`, `confluence_list_pages`, `confluence_create_page`

**Jira:** `jira_list_projects`, `jira_search_issues`, `jira_create_issue`, `jira_get_issue`, `jira_update_issue`, `jira_add_comment`, `jira_list_sprints`

---

## 4. Integration Test Plan

All tests run in the chat interface at `http://localhost:8000/mcp-agent.html` as `risk_agent`. Monitor the Browser DevTools Network tab filtered to `/api/` to observe tool calls.

### 4.1 Microsoft Teams Tests

**TEST-TEAMS-001 — List channels**
Prompt: `"What channels are in our Teams workspace?"`
Pass: Channel list returned including B-Pulse Alerts channel created in REQ-02a.

**TEST-TEAMS-002 — Read recent messages**
Prompt: `"Show me the 5 most recent messages in the B-Pulse Alerts channel"`
Pass: HTTP 200 from Graph; messages returned (or "channel is empty" handled gracefully).

**TEST-TEAMS-003 — Send a message ← WRITE**
Prompt: `"Send a message to the B-Pulse Alerts channel saying: Integration test from B-Pulse — connectivity confirmed [today's date]"`
Pass: HITL confirmation appears → user confirms → message visible in Teams within 30 seconds.

**TEST-TEAMS-004 — List members**
Prompt: `"Who are the members of our Market Risk team in Teams?"`
Pass: Member list with names and emails returned.

**TEST-TEAMS-005 — Get meetings**
Prompt: `"What meetings are scheduled for this week in the team calendar?"`
Pass: HTTP 200; list returned (may be empty — confirm graceful empty state).

---

### 4.2 Outlook Tests

**TEST-OUTLOOK-001 — List folders**
Prompt: `"What folders are in the market risk inbox?"`
Pass: Folder list including Inbox, Sent, and B-Pulse Test folder.

**TEST-OUTLOOK-002 — Read recent emails**
Prompt: `"Show me the 3 most recent emails in the inbox"`
Pass: Email subjects, senders, and timestamps returned.

**TEST-OUTLOOK-003 — Search emails**
Prompt: `"Search the inbox for any emails mentioning credit limits"`
Pass: HTTP 200; results returned or graceful "no results found" message.

**TEST-OUTLOOK-004 — Send email ← WRITE**
Prompt: `"Send an email to [your own email address] with subject 'B-Pulse Integration Test' and body 'This is an automated test from B-Pulse Digital Workers. Please ignore.'"`
Pass: HITL confirmation shows recipient, subject, body → user confirms → email received in inbox within 5 minutes.

**TEST-OUTLOOK-005 — Reply to email ← WRITE**
Prompt: `"Reply to the most recent email in my inbox saying: Acknowledged — B-Pulse automated reply test"`
Pass: Agent reads inbox first → HITL confirmation → reply sent → visible in Sent folder.

---

### 4.3 Confluence Tests

**TEST-CONF-001 — List spaces**
Prompt: `"What Confluence spaces do we have access to?"`
Pass: Space list returned, includes the target space from REQ-02a.

**TEST-CONF-002 — Search pages**
Prompt: `"Search Confluence for pages about counterparty credit risk"`
Pass: HTTP 200; results returned or graceful empty state.

**TEST-CONF-003 — Read a page**
Prompt: `"Show me the content of the B-Pulse Test Pages page in Confluence"` (the page created in REQ-02a step 4.3)
Pass: Page title and body content returned.

**TEST-CONF-004 — Create a page ← WRITE**
Prompt: `"Create a Confluence page in the [space name] space titled 'B-Pulse Test [today's date]' under the B-Pulse Test Pages parent, with body: This page was created by B-Pulse Digital Workers during integration testing. Safe to delete."`
Pass: HITL confirmation → page created → accessible at returned URL.

---

### 4.4 Jira Tests

**TEST-JIRA-001 — List projects**
Prompt: `"What Jira projects do we have access to?"`
Pass: Project list returned, includes target project.

**TEST-JIRA-002 — Search issues**
Prompt: `"Show me the 5 most recent open issues in the [project key] project"`
Pass: Issue list returned (may be empty).

**TEST-JIRA-003 — Get a specific issue**
Prompt: `"Show me the details of [PROJECT-1]"` (use any known real issue key)
Pass: Issue summary, status, assignee, description returned.

**TEST-JIRA-004 — List sprints**
Prompt: `"What sprints are active in the [project key] project?"`
Pass: Active sprint list returned.

**TEST-JIRA-005 — Create a ticket ← WRITE**
Prompt: `"Create a Jira ticket in the [project key] project of type Bug, summary: B-Pulse Integration Test [today's date], description: Created during integration testing — safe to close, label: bpulse-test"`
Pass: HITL confirmation → ticket created with key → visible on Jira board.

**TEST-JIRA-006 — Add a comment ← WRITE**
Prompt: `"Add a comment to [ticket from TEST-JIRA-005] saying: Integration test step 2 completed successfully."`
Pass: HITL confirmation → comment visible on Jira issue.

**TEST-JIRA-007 — Close the ticket ← WRITE**
Prompt: `"Close the test ticket [key] with status Done"`
Pass: HITL confirmation → ticket status updated.

---

## 5. Test Result Recording

For each test:
```
TEST ID:         _______________
Prompt used:     _______________
Tool invoked:    _______________
HTTP status:     _______________
API endpoint:    _______________
HITL triggered:  Yes / No / N/A
Pass / Fail:     _______________
Failure detail:  _______________
```

---

## 6. Error Handling Verification

Run these after the happy-path tests pass:

**TEST-ERR-001** — Temporarily set teams_team_id to `invalid-id-xyz` in worker scope. Prompt: "What channels are in our Teams?" Expected: Clear error message, not a raw stack trace.

**TEST-ERR-002** — Remove the Atlassian API token from connectors.json temporarily. Prompt: "Search Confluence for risk pages." Expected: "Connector credentials missing — please reconfigure the Atlassian connector."

**TEST-ERR-003** — Prompt: "List Confluence spaces" without having configured the confluence_space_key in worker scope. Expected: Tool should fall back gracefully or return all spaces without space-key filtering.

---

## 7. Post-Testing Cleanup

- [ ] Delete the test Confluence page created in TEST-CONF-004
- [ ] Close/delete the test Jira ticket from TEST-JIRA-005 (or use the `bpulse-test` label filter to bulk-close)
- [ ] Note: Teams messages cannot be deleted via Graph API without `ChannelMessage.Delete` permission — document the test message

---

## 8. Audit Log Verification

After all tests, check `sajhamcpserver/data/audit/tool_calls.jsonl`:
- [ ] All tool invocations appear with correct `user_id`, `worker_id`, `tool_name`, `timestamp`
- [ ] Write operations show `confirmation_required: true` in the log
- [ ] No failed test invocations are missing from the log

---

## 9. Acceptance Criteria

- [ ] Microsoft 365 connector shows **Connected** status in admin UI
- [ ] Atlassian connector shows **Connected** status in admin UI
- [ ] `w-market-risk` worker scope has real (not placeholder) values for all fields
- [ ] TEST-TEAMS-001 through TEST-TEAMS-005: all pass
- [ ] TEST-OUTLOOK-001 through TEST-OUTLOOK-005: all pass (including email received in inbox)
- [ ] TEST-CONF-001 through TEST-CONF-004: all pass (page created in Confluence)
- [ ] TEST-JIRA-001 through TEST-JIRA-007: all pass (ticket lifecycle complete)
- [ ] All write operations triggered HITL confirmation before executing
- [ ] TEST-ERR-001 through TEST-ERR-003: clear error messages returned
- [ ] All tool calls logged in audit trail
- [ ] Test artifacts cleaned up
