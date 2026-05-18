# RiskGPT Platform — Connector Integration ERD

> **Source:** Converted from `RiskGPT_Connector_ERD.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

> **RiskGPT Platform**
> Connector Integration ERD
> MS Teams | Power BI | SharePoint | Confluence | Jira

|                    |                                  |
|:-------------------|:---------------------------------|
| **Document Type**  | Requirements & Design ERD        |
| **Version**        | 1.0                              |
| **Date**           | April 2026                       |
| **Status**         | DRAFT — For Review               |
| **Classification** | CONFIDENTIAL — Internal Use Only |

**Table of Contents**

**1. Executive Summary**

This document defines the architecture, credential requirements, tool operations, and configuration specifications for integrating five enterprise collaboration and analytics connectors into the RiskGPT MCP platform. The connectors — Microsoft Teams, Power BI (live), SharePoint (existing), Confluence, and Jira — will be implemented as platform-level SAJHA MCP tools, available to all Digital Workers based on per-worker enabled_tools configuration.

The design follows the existing tool pattern: a Python implementation class in sajha/tools/impl/, a JSON tool config in config/tools/, and credential keys in application.properties or environment variables. No restart is required — the hot-reload mechanism picks up new tools within five minutes.

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Connector** | **Status** | **Auth Method** | **Primary Use Cases** |
| **SharePoint** | **Existing** | Azure AD (OAuth2) | Documents, lists, search, file metadata |
| **MS Teams** | **New** | Microsoft Graph API + Azure AD | Channel messages, meeting transcripts, search |
| **Power BI** | **New (live)** | Azure AD (OAuth2) | Report export, DAX dataset query, refresh |
| **Confluence** | **New** | Atlassian API Token (Basic) | Policy pages, runbooks, knowledge base |
| **Jira** | **New** | Atlassian API Token (Basic) | Issues, sprints, project metrics, tickets |

**2. Platform Architecture**

**2.1 How Connectors Plug In**

Every connector follows the same three-layer pattern already established by sharepoint_tool.py, edgar_tavily_tools.py, and the IRIS tools:

|  |  |  |
|:--:|:--:|:--:|
| **Layer** | **Location** | **Responsibility** |
| **Tool Config (JSON)** | sajhamcpserver/config/tools/\<tool\>.json | Tool name, description, input/output schema, enabled flag, credential env-var references |
| **Implementation (Python)** | sajhamcpserver/sajha/tools/impl/\<module\>.py | Auth, HTTP client, API calls, response normalisation, error handling |
| **Properties** | sajhamcpserver/config/application.properties | Data paths, feature flags, default config values |
| **Secrets** | Environment variables (.env / Docker secrets) | API keys, client secrets, passwords — never committed to git |

The agent_server.py passes the active worker's enabled_tools list to the SAJHA tool registry at request time. Only tools whose JSON config name appears in the worker's enabled_tools are exposed to the LangGraph agent for that conversation. Connectors not in the list are invisible — no schema leakage, no accidental calls.

**2.2 Request Flow**

User message → Agent Server → LangGraph agent (filtered tool set) → SAJHA tool call (with X-Worker-Data-Root + X-Service-Key headers) → Python tool class → External API (Teams Graph / Power BI REST / Confluence REST / Jira REST) → normalised JSON response → agent → user.

All external API calls are made server-side from the SAJHA MCP container. No credentials are exposed to the frontend or the user.

**2.3 Credential Isolation**

Credentials are per-deployment environment variables, not per-worker. All workers that share a connector use the same underlying service account / app registration. Future multi-tenant expansion can introduce per-worker credential overrides via workers.json.connector_overrides (out of scope for v1).

|                                  |
|----------------------------------|
| **3. Microsoft Teams Connector** |

**3.1 Overview**

The Teams connector uses the Microsoft Graph API to read channel messages, search conversations, retrieve meeting transcripts, and post messages. It shares the same Azure AD app registration as SharePoint — no second app is required if the combined permissions are granted.

**3.2 Credentials You Need to Provide**

To enable this connector, you need one Azure AD App Registration with the following:

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Credential** | **Type** | **Where to Get It** | **Notes** |
| **AZURE_TENANT_ID** | GUID | Azure Portal → Azure Active Directory → Overview → Tenant ID | Shared with SharePoint connector — already have this |
| **TEAMS_CLIENT_ID** | GUID | Azure Portal → App Registrations → your app → Application (client) ID | Can reuse SharePoint app if permissions are added |
| **TEAMS_CLIENT_SECRET** | Secret string | App Registration → Certificates & Secrets → New client secret | Store in .env — never in git |

**3.2.1 Microsoft Graph API Permissions Required**

In Azure Portal → App Registration → API Permissions → Add Microsoft Graph → Application permissions:

- ChannelMessage.Read.All — read all channel messages

- Chat.Read.All — read 1:1 and group chat messages

- Team.ReadBasic.All — list teams the app has access to

- Channel.ReadBasic.All — list channels

- User.Read.All — resolve user names from IDs

- OnlineMeetings.Read.All — read meeting transcripts and recordings

- ChannelMessage.Send — post messages (required only if posting is enabled)

After adding permissions, click "Grant admin consent for \<your org\>" — a Global Admin or Application Admin must approve. Without admin consent, all calls will return 403 Forbidden.

[Step-by-step: App Registration guide](https://learn.microsoft.com/en-us/graph/auth-register-app-v2)

[Permission reference: Microsoft Graph permissions](https://learn.microsoft.com/en-us/graph/permissions-reference)

**3.2.2 application.properties Keys**

Add to sajhamcpserver/config/application.properties:

connector.teams.enabled=true

connector.teams.tenant_id=\${AZURE_TENANT_ID}

connector.teams.client_id=\${TEAMS_CLIENT_ID}

connector.teams.client_secret=\${TEAMS_CLIENT_SECRET}

connector.teams.token_cache_ttl_seconds=3300

**3.3 Tool Inventory**

|  |  |  |
|:--:|:--:|:--:|
| **Tool Name (JSON config)** | **Operations** | **Description** |
| **teams_list_teams** | list_teams | List all Teams the service account has access to — returns team_id, display_name, description, member count |
| **teams_channel_messages** | list_channels, read_messages, search_messages | List channels in a team; read recent N messages from a channel; search messages by keyword across a team or all teams |
| **teams_meeting_transcript** | get_transcript, list_recordings | Retrieve full transcript for a completed Teams meeting by meeting_id; list available recordings in a date range |
| **teams_post_message** | post_message, reply_to_message | Post a new message to a channel or reply to an existing thread. Supports markdown formatting. Disabled by default — enable explicitly in enabled_tools |
| **teams_user_presence** | get_presence, get_user | Resolve user display names from object IDs; get availability/presence status for a user (for scheduling context) |

**3.4 Implementation File**

Create: sajhamcpserver/sajha/tools/impl/teams_tool.py

Classes: TeamsAuthenticator (shared token cache), TeamsBaseTool(BaseMCPTool), TeamsChannelTool, TeamsMeetingTool, TeamsPostTool, TeamsUserTool

Dependency: pip install msal (Microsoft Authentication Library for Python)

|                                  |
|----------------------------------|
| **4. Power BI Connector (Live)** |

**4.1 Overview**

The Power BI live connector replaces the existing generator stub (studio/powerbi_tool_generator.py) with runtime tools that authenticate against the Power BI REST API, execute DAX queries, export reports, and trigger dataset refreshes. This allows Digital Workers to pull live KPIs and metrics directly from Power BI rather than relying on exported snapshots.

**4.2 Credentials You Need to Provide**

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Credential** | **Type** | **Where to Get It** | **Notes** |
| **AZURE_TENANT_ID** | GUID | Azure AD → Overview (same as Teams/SharePoint) | Shared across all MS connectors |
| **POWERBI_CLIENT_ID** | GUID | Azure AD App Registration → Application (client) ID | Can be a dedicated Power BI app or the same app as Teams |
| **POWERBI_CLIENT_SECRET** | Secret string | App Registration → Certificates & Secrets | Store in .env |
| **POWERBI_WORKSPACE_IDS** | Comma-sep GUIDs | Power BI Service → workspace URL → the GUID in the path | Optional default list; tools accept workspace_id per call |

**4.2.1 Azure AD Permissions for Power BI**

In App Registration → API Permissions → Add "Power BI Service" → Application permissions:

- Dataset.Read.All — run DAX queries, read dataset metadata

- Dataset.ReadWrite.All — trigger refreshes

- Report.Read.All — list and export reports

- Workspace.Read.All — list workspaces

**4.2.2 Power BI Tenant Admin Settings**

A Power BI Fabric Admin must also enable these settings in the Power BI Admin Portal (app.powerbi.com → Settings → Admin portal → Tenant settings):

- Allow service principals to use Power BI APIs → Enabled (for the security group containing your app)

- Export reports as PPTX presentations → Enabled

- Export reports as PDF documents → Enabled

[Power BI service principal guide](https://learn.microsoft.com/en-us/power-bi/developer/embedded/embed-service-principal)

[Power BI REST API reference](https://learn.microsoft.com/en-us/rest/api/power-bi/)

**4.2.3 application.properties Keys**

connector.powerbi.enabled=true

connector.powerbi.tenant_id=\${AZURE_TENANT_ID}

connector.powerbi.client_id=\${POWERBI_CLIENT_ID}

connector.powerbi.client_secret=\${POWERBI_CLIENT_SECRET}

connector.powerbi.default_workspace_ids=\${POWERBI_WORKSPACE_IDS}

**4.3 Tool Inventory**

|  |  |  |
|:--:|:--:|:--:|
| **Tool Name** | **Operations** | **Description** |
| **powerbi_workspaces** | list_workspaces, get_workspace | List all workspaces the service principal has access to; get reports and datasets within a specific workspace |
| **powerbi_reports** | list_reports, get_report, export_report | List reports; get report metadata and pages; export a report as PDF or PPTX and return base64-encoded content for the agent to summarise |
| **powerbi_datasets** | list_datasets, get_dataset, query_dataset, refresh_dataset | List datasets; get schema and refresh history; execute a DAX query and return tabular results; trigger an on-demand refresh |
| **powerbi_dax_query** | execute_dax | Dedicated DAX execution tool — accepts workspace_id, dataset_id, and a DAX expression; returns structured JSON rows for the agent to interpret as metrics |

**4.4 Implementation File**

Create: sajhamcpserver/sajha/tools/impl/powerbi_live_tool.py

Classes: PowerBIAuthenticator (reuse token cache pattern), PowerBIBaseTool(BaseMCPTool), PowerBIWorkspaceTool, PowerBIReportTool, PowerBIDatasetTool, PowerBIDAXTool

Note: the existing studio/powerbi_tool_generator.py generates static tool configs — it is not affected. The new file implements live runtime calls.

|                             |
|-----------------------------|
| **5. Confluence Connector** |

**5.1 Overview**

The Confluence connector enables Digital Workers to search and retrieve content from Confluence Cloud — policy documents, runbooks, procedure pages, architecture wikis, and meeting notes. Workers such as the Regulatory & Policy Advisor, Operational Risk Analyst, and Audit workers particularly benefit from being able to pull current policy content directly rather than relying on static document uploads.

**5.2 Credentials You Need to Provide**

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Credential** | **Type** | **Where to Get It** | **Notes** |
| **CONFLUENCE_BASE_URL** | URL string | Your Confluence cloud URL, e.g. https://yourbank.atlassian.net | Include https://, no trailing slash |
| **CONFLUENCE_USER_EMAIL** | Email address | The email address of the Atlassian account used for the API token | Use a service account, not a personal account |
| **CONFLUENCE_API_TOKEN** | API token string | https://id.atlassian.com → Security → API tokens → Create API token | Store in .env — tokens do not expire unless revoked |
| **CONFLUENCE_CLOUD_ID** | GUID | GET https://yourbank.atlassian.net/\_edge/tenant_info → cloudId field | Used for newer v2 REST API calls; optional for v1 |

Authentication method: HTTP Basic Auth with base64(email:api_token). No OAuth app registration needed — API tokens are tied to the user account.

[Create an Atlassian API token](https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/)

[Confluence REST API v1 reference](https://developer.atlassian.com/cloud/confluence/rest/v1/intro/)

[Confluence REST API v2 reference](https://developer.atlassian.com/cloud/confluence/rest/v2/intro/)

**5.2.1 Confluence User Permissions**

The service account must be a member of (or granted view access to) every Confluence space the tools will read. Spaces with "Restricted" permissions that do not include the service account will return 403 — configure space permissions in Confluence Space Settings → Permissions.

**5.2.2 application.properties Keys**

connector.confluence.enabled=true

connector.confluence.base_url=\${CONFLUENCE_BASE_URL}

connector.confluence.user_email=\${CONFLUENCE_USER_EMAIL}

connector.confluence.api_token=\${CONFLUENCE_API_TOKEN}

connector.confluence.cloud_id=\${CONFLUENCE_CLOUD_ID}

connector.confluence.max_body_chars=8000

**5.3 Tool Inventory**

|  |  |  |
|:--:|:--:|:--:|
| **Tool Name** | **Operations** | **Description** |
| **confluence_search** | cql_search, text_search | Execute a CQL (Confluence Query Language) search or plain text search; returns page title, space, last updated, URL, and a content excerpt |
| **confluence_page** | get_page, get_page_by_title, get_children | Retrieve full page body (HTML stripped to plain text, limited by max_body_chars); get child pages; supports page_id or title + space_key lookup |
| **confluence_spaces** | list_spaces, get_space, list_space_pages | List all accessible spaces; get space metadata; list all pages in a space with pagination — useful for bulk ingestion |
| **confluence_page_write** | create_page, update_page | Create a new Confluence page or update an existing page with agent-generated content. Disabled by default in enabled_tools. |

|                       |
|-----------------------|
| **6. Jira Connector** |

**6.1 Overview**

The Jira connector enables Digital Workers to query issues, search backlogs, retrieve sprint metrics, create tickets, and update issue status. This is particularly valuable for Operational Risk, Audit, and Technology Risk workers who track remediation actions, findings, and control testing tasks in Jira.

**6.2 Credentials You Need to Provide**

|  |  |  |  |
|:--:|:--:|:--:|:--:|
| **Credential** | **Type** | **Where to Get It** | **Notes** |
| **JIRA_BASE_URL** | URL string | Your Jira cloud URL, e.g. https://yourbank.atlassian.net | Same domain as Confluence if on the same Atlassian Cloud account |
| **JIRA_USER_EMAIL** | Email address | Same service account email as Confluence | One API token works for both Jira and Confluence |
| **JIRA_API_TOKEN** | API token string | Same token as Confluence (https://id.atlassian.com → Security → API tokens) | Single token covers both products — store once in .env as ATLASSIAN_API_TOKEN |
| **JIRA_DEFAULT_PROJECT** | Project key string | Your primary Jira project key, e.g. RISK, AUDIT, TECK | Optional default; tools accept project_key per call |

Note: If your Jira and Confluence are on the same Atlassian Cloud account, JIRA_USER_EMAIL and JIRA_API_TOKEN can be the same values as CONFLUENCE_USER_EMAIL and CONFLUENCE_API_TOKEN. Consider using unified env var names ATLASSIAN_USER_EMAIL and ATLASSIAN_API_TOKEN.

[Jira Cloud REST API v3 reference](https://developer.atlassian.com/cloud/jira/platform/rest/v3/intro/)

[JQL reference (Jira Query Language)](https://support.atlassian.com/jira-service-management-cloud/docs/use-advanced-search-with-jira-query-language-jql/)

**6.2.1 Jira User Permissions**

The service account must have "Browse Projects" permission on every project the tools query, and "Create Issues" / "Edit Issues" if write tools are enabled. Set in Jira → Project Settings → People → Add your service account.

**6.2.2 application.properties Keys**

connector.jira.enabled=true

connector.jira.base_url=\${JIRA_BASE_URL}

connector.jira.user_email=\${ATLASSIAN_USER_EMAIL}

connector.jira.api_token=\${ATLASSIAN_API_TOKEN}

connector.jira.default_project=\${JIRA_DEFAULT_PROJECT}

connector.jira.max_results_per_call=50

**6.3 Tool Inventory**

|  |  |  |
|:--:|:--:|:--:|
| **Tool Name** | **Operations** | **Description** |
| **jira_search** | jql_search, text_search | Execute a JQL query or plain text search; returns issue key, summary, status, assignee, priority, created, updated, and labels. Supports pagination. |
| **jira_issue** | get_issue, get_comments, get_history | Get full issue details by issue key; retrieve all comments on an issue; get the change history (status transitions, field changes) |
| **jira_project** | list_projects, get_project, list_sprints, get_sprint | List accessible projects; get project metadata, components, versions; list active/closed sprints; get sprint details and sprint issue summary |
| **jira_write** | create_issue, update_issue, add_comment, transition_issue | Create a new Jira issue with fields; update field values on an existing issue; add a comment; transition an issue to a new status. Disabled by default. |
| **jira_metrics** | sprint_velocity, project_burndown, issue_counts_by_status | Compute sprint velocity, issue throughput by project, and current open/in-progress/done counts — useful for portfolio risk dashboards |

|                                                    |
|----------------------------------------------------|
| **7. SharePoint Connector — Current State & Gaps** |

**7.1 Overview**

SharePoint is the only connector that already exists in the codebase (sharepoint_tool.py, 3 JSON configs: sharepoint_documents, sharepoint_lists, sharepoint_search). This section documents the current state and gaps that should be addressed alongside the new connector builds.

|  |  |  |
|:--:|:--:|:--:|
| **Area** | **Current State** | **Gap / Action** |
| Auth config | Reads from sharepoint.site.url, azure.tenant.id, sharepoint.client.id, sharepoint.client.secret in JSON config | Migrate to connector.sharepoint.\* keys in application.properties for consistency with new connectors |
| Token cache | SharePointAuthenticator caches token but checks expiry naively | Refactor to use shared MicrosoftTokenCache class (shared with Teams, Power BI) |
| Site URL | Single site URL per tool config — hardcoded per deployment | Add site_url as per-call parameter, with default from application.properties |
| Graph API vs REST | Uses SharePoint REST API directly (/\_api/web/...) | Consider migrating to Microsoft Graph (/v1.0/sites/...) for consistency with Teams connector |
| Permissions | Sites.Read.All, Sites.ReadWrite.All, Files.Read.All defined in existing configs | Confirm admin consent granted; add Files.ReadWrite.All if write is needed |

**8. Combined Credential Setup Checklist**

Use this section as a checklist when setting up the connectors. All secrets go in your .env file (never in application.properties or git).

**8.1 Azure AD Setup (Teams + Power BI + SharePoint)**

1.  Log in to https://portal.azure.com with a Global Admin or Application Admin account

2.  Navigate to: Azure Active Directory → App registrations → New registration

3.  Name: "RiskGPT-MCP-Connector" (or reuse existing SharePoint app)

4.  Supported account types: "Accounts in this organizational directory only"

5.  Redirect URI: leave blank for service-to-service (client credentials flow)

6.  After creation, note: Application (client) ID → AZURE_CLIENT_ID

7.  Note Directory (tenant) ID → AZURE_TENANT_ID

8.  Certificates & Secrets → New client secret → copy value → TEAMS_CLIENT_SECRET / POWERBI_CLIENT_SECRET

9.  API Permissions → Add permission → Microsoft Graph → Application → add all Teams permissions listed in Section 3.2.1

10. API Permissions → Add permission → Power BI Service → Application → add all permissions listed in Section 4.2.1

11. Click "Grant admin consent for \<your org\>" — requires admin

**8.2 Atlassian Setup (Confluence + Jira)**

12. Log in to https://id.atlassian.com with the service account

13. Navigate to: Security → API tokens → Create API token

14. Label: "RiskGPT-MCP-Connector" → Create → copy value → ATLASSIAN_API_TOKEN

15. Note the service account email → ATLASSIAN_USER_EMAIL

16. Get your Confluence Cloud ID: GET https://yourbank.atlassian.net/\_edge/tenant_info → copy cloudId

17. In Confluence: Space Settings → Permissions → add the service account to each space (or grant global Can Use)

18. In Jira: Project Settings → People → add the service account with "Browse Projects" + "Create Issues" as needed

**8.3 .env File Template**

Add the following to your .env file (sajhamcpserver/.env or the Docker compose env file):

> # Microsoft Azure AD (shared: SharePoint, Teams, Power BI)
> AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
> TEAMS_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
> TEAMS_CLIENT_SECRET=your-teams-secret-here
> POWERBI_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
> POWERBI_CLIENT_SECRET=your-powerbi-secret-here
> POWERBI_WORKSPACE_IDS=ws-id-1,ws-id-2,ws-id-3
> # Atlassian (shared: Confluence + Jira)
> ATLASSIAN_USER_EMAIL=riskgpt-svc@yourbank.com
> ATLASSIAN_API_TOKEN=your-atlassian-api-token
> CONFLUENCE_BASE_URL=https://yourbank.atlassian.net
> CONFLUENCE_CLOUD_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
> JIRA_BASE_URL=https://yourbank.atlassian.net
> JIRA_DEFAULT_PROJECT=RISK

**9. Full Tool Inventory & Suggested Worker Mapping**

All 15 connector tools are platform-level — defined once in the MCP server and available to any worker whose enabled_tools list includes them. The table below shows which worker categories would typically benefit from each tool. Final assignment is done per-worker in workers.json.

|  |  |  |  |  |  |  |  |  |
|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| **Tool** | **Connector** | **Risk & LRC** | **Finance** | **Cap Mkts** | **Ops** | **Audit** | **Wealth** | **Technology** |
| sharepoint_documents | SharePoint | Y | Y | Y | Y | Y | Y | Y |
| sharepoint_lists | SharePoint | Y | Y | \- | Y | Y | \- | Y |
| sharepoint_search | SharePoint | Y | Y | Y | Y | Y | Y | Y |
| teams_list_teams | Teams | Y | Y | Y | \- | \- | \- | \- |
| teams_channel_messages | Teams | Y | Y | Y | Y | Y | \- | \- |
| teams_meeting_transcript | Teams | Y | \- | \- | Y | Y | \- | \- |
| teams_post_message | Teams | \- | \- | \- | Y | \- | \- | \- |
| powerbi_workspaces | Power BI | Y | Y | Y | \- | Y | \- | \- |
| powerbi_reports | Power BI | Y | Y | Y | \- | Y | \- | \- |
| powerbi_dax_query | Power BI | Y | Y | Y | \- | \- | \- | \- |
| confluence_search | Confluence | Y | Y | \- | Y | Y | \- | Y |
| confluence_page | Confluence | Y | \- | \- | Y | Y | \- | Y |
| jira_search | Jira | Y | \- | \- | Y | Y | \- | Y |
| jira_issue | Jira | Y | \- | \- | Y | Y | \- | Y |
| jira_write | Jira | \- | \- | \- | Y | Y | \- | \- |

Y = recommended enabled tool for this division. - = not applicable or high risk of misuse. Write tools (teams_post_message, confluence_page_write, jira_write) default to disabled and require explicit opt-in per worker.

**10. Acceptance Criteria**

|  |  |  |
|:--:|:--:|:--:|
| **AC** | **Connector** | **Acceptance Criterion** |
| **AC-01** | Teams | teams_channel_messages returns the last 20 messages from a specified channel given a valid team_id and channel_id, within 3 seconds |
| **AC-02** | Teams | teams_meeting_transcript returns a parsed transcript for a completed meeting; returns a clear error if transcript is unavailable or meeting is in progress |
| **AC-03** | Teams | teams_post_message is disabled by default; enabling it in enabled_tools and providing a valid channel_id results in a message posted and confirmed with a message_id |
| **AC-04** | Teams | If TEAMS_CLIENT_SECRET is missing or invalid, all Teams tools return a structured error { "error": "auth_failed", "connector": "teams", ... } — no unhandled exception |
| **AC-05** | Power BI | powerbi_dax_query executes a valid DAX expression against a dataset and returns structured tabular JSON rows within 10 seconds |
| **AC-06** | Power BI | powerbi_reports with export_report returns base64-encoded PDF content; the decoded PDF is a valid file matching the target report |
| **AC-07** | Power BI | Power BI Admin tenant setting "Allow service principals to use Power BI APIs" is verified enabled before deployment; deployment checklist includes this step |
| **AC-08** | Confluence | confluence_search returns page title, space_key, last_modified, URL, and a text excerpt for each result; supports CQL queries including space filter |
| **AC-09** | Confluence | confluence_page with a valid page_id returns the full page body stripped of HTML tags, capped at max_body_chars (configurable) |
| **AC-10** | Confluence | If the service account lacks view permission on a space, confluence_search returns a clear permission error, not a 500 or empty result |
| **AC-11** | Jira | jira_search with a JQL query returns issue key, summary, status, assignee, and priority for up to 50 results |
| **AC-12** | Jira | jira_metrics sprint_velocity returns velocity data for the last 3 sprints of a given project; returns a clear error if no sprints exist |
| **AC-13** | Jira | jira_write create_issue is disabled by default; when enabled and called with summary + project_key, creates an issue and returns the new issue key |
| **AC-14** | All | All connectors use application.properties keys with \${ENV_VAR} substitution — no hardcoded secrets in any JSON config or Python file |
| **AC-15** | All | Token/credential caching works across tool calls within a session — only one OAuth flow per token lifetime per connector, verified by log output |
| **AC-16** | All | Hot-reload picks up new tool JSON configs within 5 minutes without server restart; new tools appear in the MCP tool list endpoint |
| **AC-17** | All | connector.\*.enabled=false in application.properties prevents the tool from loading at startup and excludes it from the tool list |
| **AC-18** | All | Write-capable tools (teams_post_message, confluence_page_write, jira_write) are absent from workers where not in enabled_tools — confirmed by tool list API response |

**11. Implementation Order**

|  |  |  |  |  |
|:--:|:--:|:--:|:--:|:--:|
| **Phase** | **Deliverable** | **Connectors** | **Effort** | **Dependency** |
| **1** | Atlassian API token + credential verification script | Confluence, Jira | 0.5 day | Atlassian account API token created (Section 8.2) |
| **2** | Confluence tool: confluence_tool.py + 2 JSON configs | Confluence | 1 day | Phase 1 complete |
| **3** | Jira tool: jira_tool.py + 3 JSON configs | Jira | 1 day | Phase 1 complete (shares same Atlassian auth) |
| **4** | Azure AD app registration + admin consent + shared token cache | Teams, Power BI | 0.5 day | Azure AD admin access |
| **5** | Teams tool: teams_tool.py + 4 JSON configs | Teams | 2 days | Phase 4 + Graph API admin consent |
| **6** | Power BI live tool: powerbi_live_tool.py + 3 JSON configs + Power BI tenant setting | Power BI | 2 days | Phase 4 + Power BI Admin tenant setting |
| **7** | SharePoint refactor: migrate to connector.sharepoint.\* keys, shared token cache | SharePoint | 0.5 day | Phase 4 |
| **8** | Integration testing: AC-01 through AC-18, update workers.json with enabled_tools | All | 1 day | Phases 2-7 complete |

Total estimated effort: 8.5 days. Atlassian connectors (Confluence + Jira) can be delivered first in 2.5 days as they do not require Azure AD admin consent.
