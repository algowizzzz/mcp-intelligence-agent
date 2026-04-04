# REQ-02b — Connector MR Worker Integration & Testing
**Status:** Pending Implementation
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** Configuring the Market Risk (w-market-risk) worker with live connector credentials and executing end-to-end integration tests for Teams, Outlook, Confluence, and Jira.
**Prerequisite:** REQ-02a (External Setup) must be completed — all credentials collected before beginning this document.

---

## 1. Background

The B-Pulse platform already ships a complete connector infrastructure:

- **24 Microsoft tools** across Teams, Outlook, SharePoint, and Power BI
- **12 Atlassian tools** across Confluence and Jira
- **Connector registry** (`sajhamcpserver/sajha/core/connectors_registry.py`) with credential management
- **Worker scope mapping** (`config/workers.json` → `connector_scope` object)
- **Admin UI** for connector configuration (admin.html → Connectors tab → Overview + Worker Mapping)
- **Test endpoint** `POST /api/super/connectors/{type}/test` for connectivity verification

The Market Risk worker (`w-market-risk`) already has a placeholder `connector_scope`:
```json
{
  "worker_id": "w-market-risk",
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
}
```

These placeholder values must be replaced with live credentials before integration testing.

---

## 2. Known Issues to Fix Before Testing

The following bugs must be resolved before integration testing will work correctly:

### BUG-CONN-001 — Credential Storage is Plaintext

**Location:** `sajhamcpserver/sajha/core/connectors_registry.py` line 60

The `decrypt(v)` function is referenced but the encryption implementation is stubbed. Credentials in `config/connectors.json` are stored in plaintext.

**Required fix:** Implement AES-256-GCM encryption for all credential fields before production use. For initial testing, plaintext storage is acceptable in a sandboxed environment — but flag this clearly.

**Temporary mitigation for testing:** Ensure `config/connectors.json` is in `.gitignore` and never committed to source control.

### BUG-CONN-002 — Missing `outlook_user_email` in Teams tool scope

The `teams_get_meetings` tool reads calendar data for a specific user. The `outlook_user_email` field in the worker scope is used but may not be set for the `w-market-risk` worker. Add it explicitly.

### BUG-CONN-003 — Token Cache Not Verified

`sajhamcpserver/sajha/core/token_cache.py` is referenced by `MSGraphClient`. Verify the implementation exists and handles token refresh correctly. If the file is missing, implement a simple in-memory dict-based cache with TTL.

---

## 3. Step-by-Step Integration Configuration

### Step 1 — Configure Microsoft 365 Connector (Admin UI)

1. Log in to B-Pulse as `risk_agent` (super_admin)
2. Navigate to **Admin Console** (`/admin.html`) → **Connectors** → **Overview** tab
3. Click **Configure** on the Microsoft 365 connector card
4. Fill in the modal:
   - **Display Name:** `Microsoft 365 — Production`
   - **Tenant ID:** _(from REQ-02a step 2.2)_
   - **Client ID:** _(from REQ-02a step 2.2)_
   - **Client Secret:** _(from REQ-02a step 2.3)_
5. Click **Test Connection** — expect: green "Connection successful" message
6. Click **Save**
7. Verify connector card shows status badge **Connected** and tool count **24**

**Backend verification:**
```bash
# Verify connectors.json updated
cat sajhamcpserver/config/connectors.json | python3 -m json.tool | grep -A 5 "microsoft_azure"
```

### Step 2 — Configure Atlassian Connector (Admin UI)

1. In **Connectors** → **Overview** → Click **Configure** on Atlassian card
2. Fill in:
   - **Display Name:** `Atlassian Cloud — Production`
   - **Email:** _(service account email from REQ-02a step 3.2)_
   - **API Token:** _(from REQ-02a step 3.2)_
   - **Confluence URL:** `https://yourcompany.atlassian.net/wiki`
   - **Jira URL:** `https://yourcompany.atlassian.net`
3. Click **Test Connection** — expect: green success
4. Click **Save**

### Step 3 — Configure Worker Scope for w-market-risk

1. In **Connectors** → **Worker Mapping** tab
2. Select worker: `Market Risk Worker (w-market-risk)`
3. Fill in **Microsoft 365 scope**:
   - **Teams Team ID:** _(GUID from REQ-02a step 2.5)_
   - **Outlook User Email:** _(mailbox from REQ-02a step 2.6)_
   - **SharePoint Site URL:** _(if applicable)_
4. Click **Save Microsoft 365 Scope**
5. Fill in **Atlassian scope**:
   - **Confluence Space Key:** _(from REQ-02a step 3.3)_
   - **Jira Project Key:** _(from REQ-02a step 3.4)_
   - **Jira Board ID:** _(from REQ-02a step 3.4)_
   - **Confluence Parent Page ID:** _(optional, from REQ-02a step 3.3)_
6. Click **Save Atlassian Scope**

**Verify in workers.json:**
```bash
cat sajhamcpserver/config/workers.json | python3 -m json.tool | grep -A 20 "connector_scope"
```

### Step 4 — Enable Connector Tools for Worker

1. In Admin Console → **Tools** tab
2. Verify the following tools are enabled for the Market Risk worker:
   - Teams tools: `teams_list_channels`, `teams_get_messages`, `teams_send_message`, `teams_list_members`, `teams_get_meetings`
   - Outlook tools: `outlook_read_email`, `outlook_search_email`, `outlook_send_email`, `outlook_reply_email`
   - Confluence tools: `confluence_list_spaces`, `confluence_search`, `confluence_get_page`, `confluence_list_pages`, `confluence_create_page`
   - Jira tools: `jira_list_projects`, `jira_search_issues`, `jira_create_issue`, `jira_get_issue`, `jira_update_issue`, `jira_add_comment`, `jira_list_sprints`
3. Click **Save Tools**

---

## 4. Integration Test Plan

All tests are run in the agent chat interface (`/mcp-agent.html`) as user `risk_agent` (super_admin) to have access to all tools. Each test prompts the agent naturally; the test records the tool invoked, the API call made, and the outcome.

### 4.1 Test Environment

| Item | Value |
|---|---|
| Interface | `/mcp-agent.html` |
| User | `risk_agent` (super_admin) |
| Worker | `w-market-risk` |
| Network monitoring | Browser DevTools → Network tab, filter `/api/` |

---

### 4.2 Microsoft Teams Tests

**TEST-TEAMS-001 — List channels**

Prompt: `"What channels are available in our Teams workspace?"`

Expected:
- Tool invoked: `teams_list_channels`
- Graph API call: `GET https://graph.microsoft.com/v1.0/teams/{team_id}/channels`
- Response: Table of channel names in chat
- Pass criteria: HTTP 200 from Graph; channel list visible in response

**TEST-TEAMS-002 — Read recent messages**

Prompt: `"Show me the last 5 messages in the [channel name] channel"`

Expected:
- Tool invoked: `teams_get_messages`
- Graph API call: `GET https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages?$top=5`
- Response: List of messages with sender and timestamp
- Pass criteria: HTTP 200; at least one message returned (or "channel is empty" confirmation)

**TEST-TEAMS-003 — Send a message ← WRITE OPERATION**

Prompt: `"Send a test message to the B-Pulse Alerts channel saying 'Integration test from B-Pulse — connectivity confirmed'"`

Expected:
- Tool invoked: `teams_send_message`
- `confirmation_required: true` → human-in-the-loop (HITL) confirmation prompt appears
- After user confirms: Graph API call: `POST https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages`
- Pass criteria: HTTP 200/201 from Graph; message visible in Teams channel within 30 seconds

**TEST-TEAMS-004 — List team members**

Prompt: `"Who are the members of our Market Risk team in Teams?"`

Expected:
- Tool invoked: `teams_list_members`
- Pass criteria: HTTP 200; member list with names and email addresses returned

**TEST-TEAMS-005 — Get upcoming meetings**

Prompt: `"What meetings are scheduled for this week in our team calendar?"`

Expected:
- Tool invoked: `teams_get_meetings`
- Uses `outlook_user_email` from worker scope
- Graph API call: `GET https://graph.microsoft.com/v1.0/users/{email}/calendarView`
- Pass criteria: HTTP 200; meeting list returned (may be empty if no meetings scheduled)

---

### 4.3 Outlook Tests

**TEST-OUTLOOK-001 — List mailbox folders**

Prompt: `"What folders are in the risk team mailbox?"`

Expected:
- Tool invoked: `outlook_list_folders`
- Graph API call: `GET https://graph.microsoft.com/v1.0/users/{email}/mailFolders`
- Pass criteria: HTTP 200; folder list returned (Inbox, Sent, Drafts, etc.)

**TEST-OUTLOOK-002 — Read recent emails**

Prompt: `"Show me the 3 most recent emails in the market risk inbox"`

Expected:
- Tool invoked: `outlook_read_email`
- Graph API call: `GET https://graph.microsoft.com/v1.0/users/{email}/mailFolders/Inbox/messages?$top=3`
- Pass criteria: HTTP 200; email subjects, senders, and timestamps returned

**TEST-OUTLOOK-003 — Search emails**

Prompt: `"Search the inbox for any emails about credit limit breaches"`

Expected:
- Tool invoked: `outlook_search_email`
- Graph API call with `$search` parameter
- Pass criteria: HTTP 200; results returned (may be empty — confirm "no results" is handled gracefully)

**TEST-OUTLOOK-004 — Send email ← WRITE OPERATION**

Prompt: `"Send an email to [your test email address] with subject 'B-Pulse Integration Test' and body 'This is an automated test from B-Pulse Digital Workers. Please ignore.'"`

Expected:
- Tool invoked: `outlook_send_email`
- `confirmation_required: true` → HITL confirmation prompt shows recipient, subject, and body preview
- After user confirms: Graph API call: `POST https://graph.microsoft.com/v1.0/users/{email}/sendMail`
- Pass criteria: HTTP 202 Accepted; email received in destination inbox within 5 minutes

**TEST-OUTLOOK-005 — Reply to email ← WRITE OPERATION**

Prompt: `"Reply to the most recent email in the inbox saying 'Acknowledged — B-Pulse automated reply test'"`

Expected:
- Agent first reads inbox to find message_id → `outlook_read_email`
- Then invokes `outlook_reply_email` with that message_id
- HITL confirmation shown
- After confirm: Graph API call: `POST https://graph.microsoft.com/v1.0/users/{email}/messages/{id}/reply`
- Pass criteria: HTTP 202; reply visible in sent folder

---

### 4.4 Confluence Tests

**TEST-CONF-001 — List spaces**

Prompt: `"What Confluence spaces do we have access to?"`

Expected:
- Tool invoked: `confluence_list_spaces`
- REST call: `GET https://company.atlassian.net/wiki/rest/api/space`
- Pass criteria: HTTP 200; list of spaces returned including the target space

**TEST-CONF-002 — Search pages**

Prompt: `"Search Confluence for pages about counterparty credit risk"`

Expected:
- Tool invoked: `confluence_search`
- REST call: `GET /wiki/rest/api/content/search?cql=...`
- Pass criteria: HTTP 200; at least 0 results (graceful empty state)

**TEST-CONF-003 — Read a page**

Prompt: `"Show me the content of the [known page title] page in Confluence"`

Expected:
- Agent first searches for page → `confluence_search` or `confluence_list_pages`
- Then reads: `confluence_get_page` with found page_id
- REST call: `GET /wiki/rest/api/content/{page_id}?expand=body.storage`
- Pass criteria: HTTP 200; page title and body content returned

**TEST-CONF-004 — Create a page ← WRITE OPERATION**

Prompt: `"Create a Confluence page in the Market Risk space titled 'B-Pulse Integration Test [date]' with body 'This page was created by B-Pulse Digital Workers during integration testing. Safe to delete.'"`

Expected:
- Tool invoked: `confluence_create_page`
- `confirmation_required: true` → HITL shows title, space, body preview
- After confirm: REST call: `POST /wiki/rest/api/content`
- Pass criteria: HTTP 200; page appears in Confluence space; returned URL accessible

**Cleanup:** Delete the created test page manually after verification.

---

### 4.5 Jira Tests

**TEST-JIRA-001 — List projects**

Prompt: `"What Jira projects do we have access to?"`

Expected:
- Tool invoked: `jira_list_projects`
- REST call: `GET /rest/api/3/project`
- Pass criteria: HTTP 200; project list including target project key

**TEST-JIRA-002 — Search issues**

Prompt: `"Search for open Jira issues in the [project key] project"`

Expected:
- Tool invoked: `jira_search_issues`
- REST call: `GET /rest/api/3/search?jql=project={key}+AND+status!=Done`
- Pass criteria: HTTP 200; issue list returned (may be empty)

**TEST-JIRA-003 — Get specific issue**

Prompt: `"Show me the details of Jira issue [PROJECT-1]"` (use a known issue key)

Expected:
- Tool invoked: `jira_get_issue`
- REST call: `GET /rest/api/3/issue/{issue_key}`
- Pass criteria: HTTP 200; issue summary, description, status, assignee returned

**TEST-JIRA-004 — List sprints**

Prompt: `"What sprints are currently active in the [project key] project?"`

Expected:
- Tool invoked: `jira_list_sprints`
- Requires board_id from worker scope
- REST call: `GET /rest/agile/1.0/board/{board_id}/sprint?state=active`
- Pass criteria: HTTP 200; sprint list returned

**TEST-JIRA-005 — Create a ticket ← WRITE OPERATION**

Prompt: `"Create a Jira ticket in the [project key] project of type Bug with summary 'B-Pulse Integration Test [date]' and description 'This ticket was created by B-Pulse Digital Workers during integration testing. Safe to close.'"`

Expected:
- Tool invoked: `jira_create_issue`
- `confirmation_required: true` → HITL shows project, type, summary, description
- After confirm: REST call: `POST /rest/api/3/issue`
- Pass criteria: HTTP 200/201; ticket created with key (e.g. `CCR-47`); visible in Jira board

**TEST-JIRA-006 — Add comment to ticket ← WRITE OPERATION**

Prompt: `"Add a comment to [the ticket created in TEST-JIRA-005] saying 'Integration test completed successfully.'"`

Expected:
- Tool invoked: `jira_add_comment`
- HITL confirmation shown
- After confirm: REST call: `POST /rest/api/3/issue/{key}/comment`
- Pass criteria: HTTP 200/201; comment visible on Jira issue

**TEST-JIRA-007 — Update ticket status ← WRITE OPERATION**

Prompt: `"Close the test ticket [key] with resolution 'Done'"`

Expected:
- Tool invoked: `jira_update_issue`
- HITL confirmation
- REST call: `PUT /rest/api/3/issue/{key}`
- Pass criteria: HTTP 200; ticket status updated to Done/Closed

**Cleanup:** Close/delete the test ticket after TEST-JIRA-007.

---

## 5. Test Result Recording Template

For each test, record:

```
TEST ID:          _____________________
Date/Time:        _____________________
User/Role:        _____________________
Prompt Used:      _____________________
Tool Invoked:     _____________________
HTTP Status:      _____________________
API Endpoint:     _____________________
HITL Triggered:   Yes / No / N/A
Pass / Fail:      _____________________
Failure Detail:   _____________________
Screenshot:       _____________________
```

---

## 6. Error Handling Verification

For each connector type, verify that error states are handled gracefully:

**TEST-ERR-001 — Invalid team_id**
Temporarily modify worker scope to use an invalid team_id → confirm agent returns meaningful error ("Team not found — please verify the team_id in worker configuration") rather than raw 404 JSON.

**TEST-ERR-002 — Expired credentials**
Delete the client secret from Azure (or change it temporarily) → confirm the agent returns "Connector credentials invalid or expired — please reconfigure the Microsoft 365 connector" rather than an unhandled exception.

**TEST-ERR-003 — Missing write permission**
Test sending a Teams message without the `ChannelMessage.Send` permission granted → confirm 403 is surfaced with a clear message.

**TEST-ERR-004 — Confluence space not found**
Set confluence_space_key to a non-existent key → confirm graceful error from `confluence_list_pages` and `confluence_search`.

---

## 7. Post-Testing Configuration Steps

After all tests pass:

1. **Remove test artifacts:**
   - Delete the test Confluence page created in TEST-CONF-004
   - Close/delete the test Jira ticket from TEST-JIRA-005
   - Note: Teams messages cannot be deleted via API without additional permissions — document the test message for posterity

2. **Enable confirmation_required for all write tools:**
   Verify that `confirmation_required: true` is set in the JSON config for ALL write-operation tools:
   - `teams_send_message.json`
   - `outlook_send_email.json`
   - `outlook_reply_email.json`
   - `confluence_create_page.json`
   - `jira_create_issue.json`
   - `jira_update_issue.json`
   - `jira_add_comment.json`

3. **Audit log review:**
   Check `sajhamcpserver/data/audit/tool_calls.jsonl` — verify all test tool invocations are logged with correct user_id, worker_id, tool_name, and timestamp.

4. **Enable connector for other workers (if applicable):**
   If other workers (CCR, etc.) should have connector access, repeat Step 3 of Section 3 for each worker.

---

## 8. Known Gaps & Future Enhancements

| Gap | Description | Priority |
|---|---|---|
| Credential encryption | Credentials stored plaintext in connectors.json | Critical (pre-production) |
| Retry logic | No exponential backoff on API rate limits (429 errors) | High |
| Token refresh | MSGraphClient caches tokens but may not refresh proactively | High |
| User-scoped auth | Currently app-only; consider delegated permissions for per-user mailbox access | Medium |
| Power BI integration | 6 Power BI tools exist but not tested in this plan | Medium |
| SharePoint tools | 6 SharePoint tools configured; scope setup not covered here | Medium |
| Connector health dashboard | No UI showing real-time connector health or last-successful-call | Low |
| Rate limit monitoring | No tracking of Graph API throttle headers | Low |

---

## 9. Acceptance Criteria

- [ ] Microsoft 365 connector configured with live credentials, status shows **Connected**
- [ ] Atlassian connector configured with live credentials, status shows **Connected**
- [ ] `w-market-risk` worker scope updated with live team_id, channel, email, space_key, project_key
- [ ] TEST-TEAMS-001 through TEST-TEAMS-005: All pass
- [ ] TEST-OUTLOOK-001 through TEST-OUTLOOK-005: All pass (including email received in inbox)
- [ ] TEST-CONF-001 through TEST-CONF-004: All pass (page created in Confluence)
- [ ] TEST-JIRA-001 through TEST-JIRA-007: All pass (ticket created, commented, closed)
- [ ] All write operations triggered HITL confirmation before executing
- [ ] TEST-ERR-001 through TEST-ERR-004: All return clear, human-readable error messages
- [ ] All tool invocations appear in audit log
- [ ] Test artifacts cleaned up (Confluence page deleted, Jira ticket closed)
