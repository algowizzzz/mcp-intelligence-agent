# REQ-02a — Connector External Setup Guide
**Status:** Pending Setup
**Version:** 1.1 (Updated 2026-04-04 — simplified app-based approach)
**Scope:** External setup steps for Teams, Outlook, Confluence, and Jira so that the AI (Claude in Chrome browser automation) can interact with them. This is about logging into apps and browsers — not API configuration.

---

## 1. Approach: Apps + Browser Logins

The connector setup does not require Azure AD app registration or API token configuration upfront. Instead:

- Download the native desktop apps where available (Teams, Outlook)
- Log into web-based apps in a browser (Confluence, Jira, Outlook Web)
- The AI agent (via Claude in Chrome) interacts with these apps through the browser interface directly
- Once basic interaction is confirmed working, credentials are then entered into the B-Pulse connector admin UI to enable tool-level API access

This approach lets you verify access and test basic workflows immediately, without needing IT admin involvement for API permissions.

---

## 2. Microsoft Teams Setup

### 2.1 Download & Install

Download Microsoft Teams from:
- **Windows/Mac desktop:** https://teams.microsoft.com/downloads
- **Browser (no install):** https://teams.microsoft.com (sign in directly)

Both work. Browser-based Teams is preferred for Claude in Chrome interaction as it runs in the same browser session.

### 2.2 Sign In

1. Open https://teams.microsoft.com in Chrome
2. Sign in with your organizational Microsoft 365 account (e.g. `yourname@yourcompany.com`)
3. Accept any MFA prompts
4. Verify you can see the team and channel that B-Pulse should post to

### 2.3 Create a Dedicated Channel for B-Pulse

In the target team, create a channel for AI-generated outputs:

1. Click **…** next to the team name → **Add channel**
2. Name: `B-Pulse Alerts` (or `AI Risk Outputs` — your preference)
3. Description: `Automated alerts and outputs from B-Pulse Digital Workers`
4. Privacy: Standard (visible to all team members)
5. Click **Create**

### 2.4 Note Down (Needed for REQ-02b)

- The exact team name as it appears in Teams
- The channel name you just created
- Your Microsoft 365 email address

### 2.5 Teams Setup Checklist

```
[ ] Teams open in Chrome and logged in
[ ] Can see the target team
[ ] B-Pulse Alerts channel created
[ ] Team name noted: _______________________
[ ] Channel name noted: _______________________
[ ] M365 email noted: _______________________
```

---

## 3. Outlook Setup

### 3.1 Access Outlook

Outlook Web is simplest for AI interaction:

1. Open https://outlook.office.com in Chrome (same session as Teams)
2. You should already be signed in (shared Microsoft 365 session)
3. Verify you can see your inbox and compose a new email

If using Outlook desktop app:
- Download from https://aka.ms/getoutlook or via Microsoft 365 installer
- Sign in with same organizational account

### 3.2 Identify the Test Mailbox

B-Pulse will send and read emails on behalf of a specific mailbox. Decide which:

**Option A — Your own mailbox:** Use your logged-in account email. Simple for testing.

**Option B — Shared mailbox:** If your organization has a shared inbox for risk alerts (e.g. `mrrisk@yourcompany.com`), use that. Requires the shared mailbox to be added to your Outlook profile.

For initial testing, Option A (your own mailbox) is fine.

### 3.3 Create a Test Email Folder

To avoid cluttering your inbox during testing:

1. In Outlook Web → right-click **Inbox** → **Create new subfolder**
2. Name: `B-Pulse Test`
3. This is where test emails sent by the AI will arrive

### 3.4 Outlook Setup Checklist

```
[ ] Outlook Web open in Chrome and logged in
[ ] Can compose and send a test email
[ ] Test mailbox email noted: _______________________
[ ] B-Pulse Test folder created in inbox
```

---

## 4. Confluence Setup

### 4.1 Access Confluence

1. Open your Confluence site in Chrome: `https://yourcompany.atlassian.net/wiki`
2. Sign in with your Atlassian account credentials
3. Verify you can navigate to the Market Risk (or equivalent) space

### 4.2 Identify the Target Space

1. Navigate to the space where B-Pulse should create pages
2. Note the **Space Key** — visible in the URL: `.../wiki/spaces/{SPACE_KEY}`
3. Also note the full Space Name for reference

### 4.3 Create a Test Parent Page

Create a page to contain all B-Pulse generated content during testing:

1. In the target space → **Create** → **Page**
2. Title: `B-Pulse Test Pages`
3. Body: `This page is a container for pages created by B-Pulse Digital Workers during testing. Safe to delete after testing.`
4. Publish the page
5. Note the page URL — the page ID is the number in the URL: `.../pages/{PAGE_ID}/...`

### 4.4 Confluence Setup Checklist

```
[ ] Confluence open in Chrome and logged in
[ ] Can access the target space
[ ] Space Key noted: _______________________
[ ] Space Name noted: _______________________
[ ] Test parent page created
[ ] Parent page ID noted: _______________________
[ ] Confluence site URL noted: https://____________.atlassian.net/wiki
```

---

## 5. Jira Setup

### 5.1 Access Jira

1. Open your Jira site in Chrome: `https://yourcompany.atlassian.net`
2. Sign in with same Atlassian credentials (shared session with Confluence)
3. Navigate to the project that B-Pulse should manage tickets in

### 5.2 Identify the Target Project

1. In Jira → your project → note the **Project Key** visible in the URL or in any ticket ID (e.g. tickets named `MRISK-123` → key is `MRISK`)
2. Navigate to the **Board** view → note the URL: `.../boards/{BOARD_ID}` — this is needed for sprint queries

### 5.3 Create a Test Epic or Label

To keep test tickets organised:

1. Create a label called `bpulse-test` in Jira (Settings → Issues → Labels)
2. All tickets created by B-Pulse during testing will use this label
3. After testing, filter by this label and bulk-close/delete them

### 5.4 Jira Setup Checklist

```
[ ] Jira open in Chrome and logged in
[ ] Can create a new ticket manually (verify permissions)
[ ] Project Key noted: _______________________
[ ] Board ID noted: _______________________
[ ] Jira site URL noted: https://____________.atlassian.net
[ ] bpulse-test label created
[ ] Atlassian account email noted: _______________________
```

---

## 6. Creating an Atlassian API Token (Needed for Tool-Level Access)

While browser-based login enables AI interaction via Claude in Chrome, the B-Pulse MCP tools need an API token to call Confluence and Jira APIs programmatically from the agent.

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click **Create API token**
3. Label: `B-Pulse MCP Server`
4. Copy the token immediately — it will not be shown again

```
[ ] Atlassian API token created and saved securely
```

---

## 7. Microsoft 365 App-Level Credentials (If Tool-Level Access Required)

For the B-Pulse MCP tools to call Teams and Outlook APIs (not just browser interaction), an Azure AD app registration is needed. This is a lighter-touch version than the full enterprise setup:

**Fastest approach — use existing IT app registration if available:**
Ask your IT team: "Do we have an existing Azure AD app registration we can use for internal tools?" Many organizations already have one. If yes, request:
- The **Application (Client) ID**
- The **Tenant ID**
- A new **Client Secret** scoped to your use

**If IT creates a new one, request these minimum permissions:**
- `Mail.Read`, `Mail.Send` (for Outlook)
- `Team.ReadBasic.All`, `ChannelMessage.Read.All`, `ChannelMessage.Send` (for Teams)
- `Calendars.Read` (for meeting queries)
- All as **Application permissions** with **Admin consent**

Note the **Tenant ID**, **Client ID**, and **Client Secret** for entry into B-Pulse.

```
[ ] M365 Tenant ID obtained: _______________________
[ ] M365 Client ID obtained: _______________________
[ ] M365 Client Secret obtained (saved securely): [CONFIGURED]
[ ] Admin consent granted for all permissions
```

---

## 8. Complete Credentials Summary

Fill this in before proceeding to REQ-02b:

```
=== MICROSOFT 365 ===
Tenant ID:             _______________________
Client ID:             _______________________
Client Secret:         [save in password manager]
Teams team name:       _______________________
B-Pulse channel name:  _______________________
Outlook mailbox email: _______________________

=== ATLASSIAN ===
Atlassian email:       _______________________
API Token:             [save in password manager]
Confluence site URL:   https://____________.atlassian.net/wiki
Jira site URL:         https://____________.atlassian.net
Confluence Space Key:  _______________________
Confluence Parent Page ID: _______________________
Jira Project Key:      _______________________
Jira Board ID:         _______________________

=== BROWSER SESSIONS ACTIVE ===
[ ] Teams open in Chrome, logged in
[ ] Outlook Web open in Chrome, logged in
[ ] Confluence open in Chrome, logged in
[ ] Jira open in Chrome, logged in
```

---

## 9. What Happens Next

Once the above checklist items are complete:

- **Browser-based testing** can start immediately — Claude in Chrome can interact with the open app tabs directly (send a Teams message in the browser, compose an email in Outlook Web, create a page in Confluence, create a Jira ticket)
- **Tool-level API testing** (REQ-02b) requires the credentials above to be entered into B-Pulse Admin Console → Connectors
- The two can proceed in parallel if desired
