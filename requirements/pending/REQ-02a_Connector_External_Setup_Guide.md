# REQ-02a — Connector External Setup Guide
**Status:** Pending Setup
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** All external configuration steps required in Microsoft 365, Atlassian Cloud, and Jira **before** connecting them to the B-Pulse platform. This document covers work done OUTSIDE the application.

---

## 1. Overview

The B-Pulse platform supports two connector families:

| Connector Family | Services Covered | Auth Method |
|---|---|---|
| Microsoft 365 (Azure AD) | Teams, Outlook, SharePoint, Power BI | OAuth 2.0 Client Credentials (app-only) |
| Atlassian Cloud | Confluence, Jira | HTTP Basic Auth with API Token |

Each family requires one-time setup in the respective admin portals before credentials can be entered into B-Pulse. This document is a step-by-step guide for IT administrators performing that external setup.

---

## 2. Microsoft 365 Setup (Azure Active Directory)

### 2.1 What You Need

- An Azure AD tenant (Microsoft Entra ID) with Global Administrator or Application Administrator role
- The B-Pulse platform URL (needed for redirect URI configuration, if OAuth code flow is used in future)
- A service account or application identity that B-Pulse will use

### 2.2 Step 1 — Register an Application in Azure AD

1. Go to [https://portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. **Name:** `B-Pulse Digital Worker` (or your preferred name)
3. **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
4. **Redirect URI:** Leave blank for now (app-only flow does not need redirect)
5. Click **Register**
6. **Copy and save:**
   - **Application (client) ID** — this is `client_id`
   - **Directory (tenant) ID** — this is `tenant_id`

### 2.3 Step 2 — Create a Client Secret

1. In the registered app → **Certificates & secrets** → **New client secret**
2. **Description:** `B-Pulse MCP Server`
3. **Expires:** Choose the longest expiry your policy allows (24 months recommended)
4. Click **Add**
5. **IMMEDIATELY copy the secret Value** — it will not be shown again
   - This is `client_secret`

### 2.4 Step 3 — Grant API Permissions

The B-Pulse connector uses **application permissions** (no user context required — it acts as the application itself). In the registered app → **API permissions** → **Add a permission** → **Microsoft Graph** → **Application permissions**.

Add ALL of the following:

| Permission | Type | Purpose |
|---|---|---|
| `Mail.Read` | Application | Read all mailboxes |
| `Mail.Send` | Application | Send email on behalf of any mailbox |
| `Calendars.Read` | Application | Read calendar/meetings |
| `User.Read.All` | Application | List users and resolve email addresses |
| `Team.ReadBasic.All` | Application | List Teams and channels |
| `Channel.ReadBasic.All` | Application | Read channel metadata |
| `ChannelMessage.Read.All` | Application | Read channel messages |
| `ChannelMessage.Send` | Application | Send messages to channels |
| `Files.Read.All` | Application | Read SharePoint/OneDrive files |
| `Sites.Read.All` | Application | Read SharePoint sites |
| `GroupMember.Read.All` | Application | List group members |

After adding all permissions → **Grant admin consent for [Your Organization]** (requires Global Administrator).

> **Important:** Without admin consent, all API calls will return 403 Forbidden.

### 2.5 Step 4 — Identify Teams Team ID

The connector needs the internal Teams Team ID (a GUID), not the display name.

**Method A — Teams Admin Center:**
1. Go to [https://admin.teams.microsoft.com](https://admin.teams.microsoft.com) → **Teams** → **Manage teams**
2. Click the team you want B-Pulse to connect to
3. Copy the **Team ID** from the URL: `.../teams/details/{team_id}`

**Method B — Graph Explorer:**
1. Go to [https://developer.microsoft.com/en-us/graph/graph-explorer](https://developer.microsoft.com/en-us/graph/graph-explorer)
2. Sign in with your organization account
3. Run: `GET https://graph.microsoft.com/v1.0/me/joinedTeams`
4. Find your team and copy the `id` field

**Method C — PowerShell:**
```powershell
Connect-MicrosoftTeams
Get-Team -DisplayName "Market Risk Team" | Select-Object GroupId, DisplayName
```

**Save:** The Team ID (GUID format `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`) for entry into B-Pulse worker scope.

### 2.6 Step 5 — Identify Channel ID

Within the team, identify which channel B-Pulse should post to:

1. Open Teams → Navigate to the channel
2. Click **…** (More options) → **Get link to channel**
3. The URL contains `groupId={team_id}&tenantId={tenant_id}` — the channel ID is embedded in the URL as well
4. Alternatively via Graph Explorer: `GET https://graph.microsoft.com/v1.0/teams/{team_id}/channels`

### 2.7 Step 6 — Identify Outlook Mailbox User

The `outlook_send_email` and `outlook_read_email` tools act on behalf of a specific user mailbox.

1. Identify the service mailbox or user account that should send/receive (e.g. `mrrisk@yourdomain.com`)
2. Ensure the mailbox exists and is licensed for Exchange Online
3. Save the full email address — this becomes `outlook_user_email` in the worker scope

> **Note:** Using a shared mailbox is recommended for service accounts. Shared mailboxes do not require a license in most tenants.

### 2.8 Step 7 — Verify Connection (Manual Test)

Before configuring B-Pulse, verify the credentials work:

```bash
# Get token
curl -X POST \
  "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token" \
  -d "client_id={client_id}" \
  -d "client_secret={client_secret}" \
  -d "scope=https://graph.microsoft.com/.default" \
  -d "grant_type=client_credentials"

# Test with returned access_token
curl -H "Authorization: Bearer {access_token}" \
  "https://graph.microsoft.com/v1.0/users"
```

Expected: HTTP 200 with a list of users. If 403, admin consent has not been granted.

### 2.9 Microsoft 365 Setup Checklist

```
[ ] App registered in Azure AD (Name: B-Pulse Digital Worker)
[ ] client_id saved
[ ] tenant_id saved
[ ] client_secret saved (created, not expired)
[ ] All 11 API permissions added as Application permissions
[ ] Admin consent granted for all permissions
[ ] Teams Team ID identified and saved
[ ] Target channel ID identified
[ ] Outlook mailbox email identified (e.g. mrrisk@domain.com)
[ ] Manual token test passes (HTTP 200)
```

---

## 3. Atlassian Cloud Setup (Confluence + Jira)

### 3.1 What You Need

- An Atlassian Cloud account with Admin role on the target site
- Your Atlassian site URL (e.g. `https://yourcompany.atlassian.net`)

### 3.2 Step 1 — Create an API Token

1. Go to [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Click **Create API token**
3. **Label:** `B-Pulse MCP Server`
4. Click **Create**
5. **IMMEDIATELY copy the token** — it will not be shown again
   - This is `api_token`
6. The user email you are logged in with is `email` (e.g. `admin@yourcompany.com`)

> **Important:** The API token inherits the permissions of the user account that created it. Use a dedicated service account user (e.g. `bpulse-service@yourcompany.com`) rather than a personal account.

### 3.3 Step 2 — Confluence Setup

**Identify the Space Key for Market Risk:**

1. Go to Confluence → Navigate to the Market Risk space
2. The Space Key is visible in the URL: `https://yourcompany.atlassian.net/wiki/spaces/{SPACE_KEY}`
3. Alternatively, go to **Space Settings** → the Space Key is shown at the top
4. Save: `confluence_space_key` (e.g. `MRISK` or `RISK`)

**Verify Space Access:**

The service account must have at minimum **View** permission on the target space. To check:
1. Confluence → Space → **Space Settings** → **Permissions**
2. Ensure your service account or its group has the space listed

**Identify Parent Page ID (for page creation):**

When creating Confluence pages via the tool, you may want them to appear under a specific parent page:
1. Navigate to the parent page in Confluence
2. Go to **…** (More actions) → **Page information**
3. The Page ID appears in the URL: `.../pages/{page_id}/info`
4. Save this as the default `parent_page_id` for the worker scope

### 3.4 Step 3 — Jira Setup

**Identify the Project Key:**

1. Go to Jira → Your Project → **Project Settings** → **Details**
2. The **Key** field (e.g. `MRISK`, `CCR`, `RISK`) is the `jira_project_key`
3. Alternatively visible in issue IDs: `MRISK-123` → key is `MRISK`

**Identify the Board ID (for sprints):**

The `jira_list_sprints` tool requires a board ID:
1. Go to Jira → Your Project → **Board** view
2. The board ID is in the URL: `.../boards/{board_id}`

**Ensure Service Account Has Permission:**

The API token user must have:
- **Project role**: At minimum `Service Desk Team` or `Developer` role on the project
- **Issue permissions**: Create Issues, Edit Issues, Add Comments
- **Browse Projects** permission

To verify: In Jira → Project → **Project Settings** → **People** → confirm service account is listed with appropriate role.

### 3.5 Step 4 — Verify Atlassian Connection (Manual Test)

```bash
# Test Confluence
curl -u "admin@yourcompany.com:{api_token}" \
  "https://yourcompany.atlassian.net/wiki/rest/api/space?limit=5"

# Test Jira
curl -u "admin@yourcompany.com:{api_token}" \
  "https://yourcompany.atlassian.net/rest/api/3/myself"
```

Expected: HTTP 200 for both. If 401, the API token is incorrect. If 403, the service account lacks permissions.

### 3.6 Atlassian Setup Checklist

```
[ ] Service account created (recommended: bpulse-service@domain.com)
[ ] API token created and saved
[ ] Service account email saved
[ ] Confluence site URL saved (https://yourcompany.atlassian.net/wiki)
[ ] Jira site URL saved (https://yourcompany.atlassian.net)
[ ] Confluence Space Key identified and saved (e.g. MRISK)
[ ] Confluence parent page ID identified (for page creation)
[ ] Jira Project Key identified and saved (e.g. CCR)
[ ] Jira Board ID identified (for sprint queries)
[ ] Service account has Create/Edit permissions in Jira project
[ ] Service account has View/Edit permissions on Confluence space
[ ] Manual Confluence test passes (HTTP 200)
[ ] Manual Jira test passes (HTTP 200)
```

---

## 4. Teams Channel & Group Configuration

### 4.1 Create a Dedicated B-Pulse Channel (Recommended)

Rather than using an existing channel, create a dedicated channel for B-Pulse alerts and outputs:

1. Open the target Team → **Add channel**
2. **Channel name:** `B-Pulse Alerts` (or `AI Risk Alerts`, `Digital Worker Outputs`)
3. **Description:** `Automated messages from B-Pulse Digital Workers`
4. **Privacy:** Standard (all team members) or Private (admin-controlled)
5. Click **Create**

### 4.2 Add Service Account to Teams (If Separate from User Accounts)

If using a dedicated Azure AD application identity:

> Note: App-only permissions (`ChannelMessage.Send`) allow the application to post directly without a user account. However, the Teams channel must exist in the team the app has access to.

No additional Teams group membership is required for app-only posting IF `ChannelMessage.Send` application permission is granted and admin-consented.

### 4.3 Channel Notification Settings

Ensure the target channel does not have notifications muted for the team members who should receive B-Pulse alerts:
1. Right-click the channel → **Channel notifications**
2. Set to **All activity** or **Mentions & replies** depending on preference

---

## 5. Security Considerations

### 5.1 Least Privilege

- Only grant the permissions listed in Section 2.4 — do not add `Mail.ReadWrite` (allows deletion), `Files.ReadWrite.All` (allows modification of all files), or similar overpowered scopes
- For Atlassian, use a service account with project-scoped permissions rather than site-admin access

### 5.2 Secret Rotation

Microsoft client secrets expire. Set a calendar reminder for 30 days before expiry:
- Expiry date is visible in Azure AD → App registrations → Certificates & secrets
- To rotate: create a new secret FIRST, update B-Pulse, then delete the old secret

Atlassian API tokens do not expire by default but should be rotated annually as a best practice.

### 5.3 Audit Trail

Both Microsoft Graph and Atlassian APIs maintain their own audit logs:
- Microsoft: Purview compliance portal → Audit → Activity search
- Atlassian: Jira Administration → Audit log

The B-Pulse audit log (`tool_calls.jsonl`) also records all tool invocations with user, tool name, and timestamp for cross-reference.

---

## 6. Credential Summary Template

Print this template and fill it in before proceeding to REQ-02b (in-application configuration):

```
=== MICROSOFT 365 CREDENTIALS ===
Tenant ID:         ___________________________________
Client ID:         ___________________________________
Client Secret:     ___________________________________
Teams Team ID:     ___________________________________
Channel Name:      ___________________________________
Outlook Email:     ___________________________________

=== ATLASSIAN CREDENTIALS ===
Service Email:     ___________________________________
API Token:         ___________________________________
Confluence URL:    https://____________.atlassian.net/wiki
Jira URL:          https://____________.atlassian.net
Confluence Space:  ___________________________________
Jira Project Key:  ___________________________________
Jira Board ID:     ___________________________________
```

---

## 7. Troubleshooting

| Symptom | Likely Cause | Resolution |
|---|---|---|
| Microsoft token request returns 400 | Wrong tenant_id or client_id format | Verify GUIDs from Azure portal |
| Microsoft API returns 401 | client_secret wrong or expired | Regenerate secret in Azure AD |
| Microsoft API returns 403 | Admin consent not granted | Return to step 2.4 and grant admin consent |
| Teams send message returns 403 | App lacks `ChannelMessage.Send` permission | Add permission and re-grant consent |
| Atlassian API returns 401 | Wrong email or API token | Verify token at id.atlassian.com |
| Atlassian API returns 403 | Service account lacks project permission | Add account to project in Jira/Confluence settings |
| Confluence space not found | Wrong space key | Verify via Confluence → Space Settings |
| Jira project not found | Wrong project key | Check issue IDs for correct key prefix |
