# RiskGPT Platform — Connector Credential Setup Guide

> **Source:** Converted from `RiskGPT_Connector_Setup_Guide.docx` on 2026-05-17. Diagrams and embedded images are summarised in prose; original .docx is no longer in the active tree (see git history if needed).

---

> **RiskGPT Platform**
> Connector Credential Setup Guide
> Step-by-step: Azure AD (Teams, Power BI, SharePoint) | Atlassian (Confluence, Jira)

|  |  |
|:---|:---|
| **Audience** | Developer or IT Admin with no prior Azure AD experience |
| **Time Required** | Azure AD setup: ~45 minutes (requires IT Admin) \| Atlassian: ~10 minutes |
| **What You Will Have After** | A completed .env file with all credentials ready to paste into the MCP server |
| **Classification** | CONFIDENTIAL — credentials produced are highly sensitive, treat like passwords |

**Contents**

**1. Before You Start — What You Are Setting Up**

You need credentials for two completely separate ecosystems. They do not interact with each other.

|  |  |  |
|:--:|:--:|:--:|
| **Ecosystem** | **Covers** | **What You Need Access To** |
| **Microsoft / Azure AD** | Teams, Power BI, SharePoint | Azure Portal (portal.azure.com) — requires a Global Admin or Application Admin in your Microsoft 365 tenant |
| **Atlassian** | Confluence, Jira | Your Atlassian account (id.atlassian.com) — only requires your own login, no admin needed to create an API token |

```
IMPORTANT
If you are not an Azure Global Admin or Application Admin, you will need to involve your IT/Cloud team for the Azure steps.
The Atlassian (Confluence/Jira) setup you can do yourself — it takes about 10 minutes and is covered in Section 4.
```

**1.1 Glossary — Terms You Will Encounter**

|  |  |
|:--:|:--:|
| **Term** | **What It Means in Plain English** |
| **Azure AD / Microsoft Entra ID** | Microsoft's identity and access management service. It's the system that manages who can log in to your bank's Microsoft 365 services (Teams, SharePoint, Power BI, etc.). Azure AD and Microsoft Entra ID are the same thing — Microsoft renamed it in 2023. |
| **App Registration** | A record in Azure AD that represents your application (RiskGPT MCP server). It's like creating a service account for an application, rather than a person. The app gets its own ID and can be granted permissions to call Microsoft APIs. |
| **Tenant** | Your organisation's instance of Azure AD. Every company that uses Microsoft 365 has exactly one tenant. The Tenant ID is a unique identifier (a GUID like "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx") for your organisation. |
| **Client ID** | The unique ID of your App Registration — like a username for the application. |
| **Client Secret** | A password for the application. You generate it once, copy it immediately (it's only shown once), and store it securely. If lost, you generate a new one. |
| **API Permissions** | The list of things your app is allowed to do — e.g., "read Teams messages", "export Power BI reports". You choose which permissions to add. |
| **Admin Consent** | A Global Admin must approve ("consent to") certain permissions before the app can use them. This is a one-time step. Without it, API calls return 403 Forbidden. |
| **GUID** | A globally unique identifier — looks like xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. Tenant ID, Client ID, Object ID, and Workspace ID are all GUIDs. |
| **Microsoft Graph API** | Microsoft's unified API for accessing Teams, SharePoint, Outlook, and other M365 services. RiskGPT calls this API when it reads Teams messages or SharePoint documents. |
| **Power BI REST API** | Separate API specifically for Power BI — used to list workspaces, export reports, and run DAX queries. Requires its own permission set in addition to Microsoft Graph. |
| **API Token (Atlassian)** | For Atlassian products (Confluence, Jira), authentication uses a simple token tied to your user account rather than an app registration. Much simpler than Azure AD. |

> **Part A: Microsoft / Azure AD Setup**
> Teams | Power BI | SharePoint

**2. Azure AD — App Registration**

One App Registration covers all three Microsoft connectors (Teams, Power BI, SharePoint). You create it once and add the appropriate permissions for each product.

> **ADMIN REQUIRED**
> You need to be a Global Administrator or Application Administrator in your Azure AD tenant to complete Steps 1–8.
> If you are not an admin, share this document with your IT/Cloud team and ask them to complete Part A for you.
> They will give you back three values: AZURE_TENANT_ID, CLIENT_ID, and CLIENT_SECRET.

**2.1 Access the Azure Portal**

1.  Open a browser and go to: https://portal.azure.com

2.  Sign in with your Microsoft 365 work account (the admin account).

3.  After signing in you will see the Azure home page with colourful service tiles.

```
IMPORTANT
If you see "You don't have access to this resource" or are prompted to request access, your account is not an admin. You need to ask an IT admin to proceed.
```

**2.2 Find Azure Active Directory / Microsoft Entra ID**

4.  In the top search bar (says "Search resources, services, and docs"), type: Microsoft Entra ID

5.  Click "Microsoft Entra ID" in the results. (This is the new name for Azure Active Directory — same thing.)

6.  You are now on the Entra ID overview page for your organisation.

|                                               |
|-----------------------------------------------|
| **portal.azure.com** → **Microsoft Entra ID** |

**2.2.1 Copy Your Tenant ID Right Now**

On the overview page, you will see a box labelled "Tenant information" on the right side. Inside it you will see "Tenant ID" with a value like xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.

7.  Click the copy icon next to the Tenant ID value.

8.  Paste it into your .env file as the value for AZURE_TENANT_ID.

| **AZURE_TENANT_ID** | Copied from Entra ID Overview → Tenant information → Tenant ID <br> xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| --- | --- |

**2.3 Create the App Registration**

|  |
|----|
| **portal.azure.com** → **Microsoft Entra ID** → **App registrations** → **+ New registration** |

9.  In the left sidebar of the Entra ID page, click "App registrations".

10. Click "+ New registration" at the top of the page.

11. Fill in the form:

<!-- -->

1)  Name: type RiskGPT-MCP-Connector (or any name you prefer)

2)  Supported account types: select "Accounts in this organizational directory only (Single tenant)"

3)  Redirect URI: leave blank — not needed for server-to-server calls

<!-- -->

12. Click the blue "Register" button at the bottom.

13. You are now on the app's overview page. You will see "Application (client) ID" near the top.

14. Copy this value — it is your CLIENT_ID.

| **TEAMS_CLIENT_ID (and POWERBI_CLIENT_ID)** | Copied from App Registration Overview → Application (client) ID <br> xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| --- | --- |

> **NOTE**
> Note: You can use the same Client ID for both Teams and Power BI — they are the same app registration.
> Set TEAMS_CLIENT_ID and POWERBI_CLIENT_ID to the same value in your .env file.

**2.4 Create a Client Secret (the App's Password)**

|  |
|----|
| **App Registration** → **Certificates & secrets** → **Client secrets** → **+ New client secret** |

15. In the left sidebar of your app, click "Certificates & secrets".

16. Click "+ New client secret".

17. Fill in the form:

<!-- -->

4)  Description: type RiskGPT MCP Server

5)  Expires: select "24 months" (or your organisation's standard rotation policy)

<!-- -->

18. Click "Add".

19. CRITICAL: A new row appears. You will see two columns — "Value" and "Secret ID". Copy the VALUE column immediately. This is the only time it will be shown in full. If you navigate away or refresh, it will be partially hidden forever and you will need to create a new one.

20. Paste the Value into your .env file.

| **TEAMS_CLIENT_SECRET (and POWERBI_CLIENT_SECRET)** | Copied from Certificates & secrets → Value (only visible once) <br> your-secret-value-here |
| --- | --- |

> **NOTE**
> You can use the same secret for both Teams and Power BI since they share an app registration.
> Set both TEAMS_CLIENT_SECRET and POWERBI_CLIENT_SECRET to the same value.
> Calendar reminder: set a reminder before the secret expires so you can regenerate it without service disruption.

**2.5 Add API Permissions — Microsoft Graph (for Teams)**

|  |
|----|
| **App Registration** → **API permissions** → **+ Add a permission** → **Microsoft Graph** → **Application permissions** |

21. In the left sidebar, click "API permissions".

22. Click "+ Add a permission".

23. A side panel opens. Click "Microsoft Graph".

24. Click "Application permissions" (not Delegated — you want the app to act on its own, not on behalf of a user).

25. In the search box, search for each permission below and check the checkbox next to it:

|  |  |
|:--:|:--:|
| **Permission Name** | **What It Enables** |
| **ChannelMessage.Read.All** | Read all messages in all Teams channels — needed by teams_channel_messages tool |
| **Chat.Read.All** | Read 1-on-1 and group chat messages |
| **Team.ReadBasic.All** | List teams — needed by teams_list_teams tool |
| **Channel.ReadBasic.All** | List channels within a team |
| **User.Read.All** | Look up user display names from their IDs (to show who sent messages) |
| **OnlineMeetings.Read.All** | Read meeting transcripts — needed by teams_meeting_transcript tool |
| **ChannelMessage.Send (optional)** | Post messages to channels — only add if you want the post tool enabled |

26. After checking all the permissions you want, click "Add permissions" at the bottom of the panel.

27. You will see them listed under "Configured permissions" but with a warning icon "Not granted for \<org\>".

The warning icon is normal — this is fixed in the next step (Admin Consent).

**2.6 Add API Permissions — Power BI Service**

|  |
|----|
| **API permissions** → **+ Add a permission** → **Power BI Service** → **Application permissions** |

28. Still on the "API permissions" page, click "+ Add a permission" again.

29. This time, scroll down in the panel until you see "Power BI Service" (it may be listed under "APIs my organization uses" — you may need to search for it).

30. Click "Power BI Service" → "Application permissions".

31. Check these permissions:

|  |  |
|:--:|:--:|
| **Permission Name** | **What It Enables** |
| **Dataset.Read.All** | Execute DAX queries, read dataset metadata and schema |
| **Dataset.ReadWrite.All** | Trigger on-demand dataset refreshes |
| **Report.Read.All** | List and export reports as PDF or PPTX |
| **Workspace.Read.All** | List workspaces and their contents |

32. Click "Add permissions".

**2.7 Add API Permissions — SharePoint (if not already done)**

|  |
|----|
| **API permissions** → **+ Add a permission** → **SharePoint** → **Application permissions** |

If your existing SharePoint connector was registered with a different app, you can skip this step. If you are consolidating everything into one app registration, add these:

|  |  |
|:--:|:--:|
| **Permission Name** | **What It Enables** |
| **Sites.Read.All** | Read files, lists, and site content across all SharePoint sites |
| **Sites.ReadWrite.All** | Upload and update files (only add if SharePoint write tools are needed) |
| **Files.Read.All** | Read all files across OneDrive and SharePoint |

**2.8 Grant Admin Consent — CRITICAL STEP**

> **ADMIN REQUIRED**
> This step makes all the permissions active. Without it, every API call will return "403 Forbidden".
> This must be done by a Global Administrator or Privileged Role Administrator.
> It only needs to be done once.

|                                                                         |
|-------------------------------------------------------------------------|
| **API permissions** → **Grant admin consent for \<Your Organisation\>** |

33. On the "API permissions" page, you will see a button near the top labelled "Grant admin consent for \<Your Organisation Name\>".

34. Click it.

35. A confirmation dialog appears: "Do you want to grant consent for the requested permissions for all accounts in \<org\>?" — click "Yes".

36. All permission rows should now show a green checkmark under the "Status" column.

37. If any row still shows the warning icon, refresh the page. If it persists, the account performing this step may not have the required admin role.

```
TIP
Green checkmarks = permissions active = API calls will work.
If you see any red icons or "Not granted", do not proceed — contact your Azure AD admin.
```

**2.9 Get Your Workspace and Report IDs for Power BI**

|                                                        |
|--------------------------------------------------------|
| **app.powerbi.com** → **Your Workspace or Report URL** |

Power BI workspace IDs and report IDs are embedded in the URL when you open them in a browser.

38. Open Power BI Service in your browser: https://app.powerbi.com

39. Navigate to a workspace you want to connect.

40. Look at the URL bar. It will look like:

|  |
|----|
| https://app.powerbi.com/groups/**WORKSPACE_ID**/reports/**REPORT_ID**/ReportSection |

41. Copy the WORKSPACE_ID (the GUID after /groups/) — this is your POWERBI_WORKSPACE_IDS value.

42. Copy the REPORT_ID if you want to reference specific reports in tool calls.

| **POWERBI_WORKSPACE_IDS** | GUID(s) from Power BI URL — /groups/<WORKSPACE_ID>/ — comma-separate multiple <br> xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx,yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy |
| --- | --- |

**2.10 Power BI Tenant Setting — Service Principal Access**

> **ADMIN REQUIRED**
> This is a separate setting in the Power BI Admin Portal — not in Azure AD.
> It must be enabled by a Power BI Administrator (Fabric Admin), who may be a different person from the Azure Admin.
> Without this setting, all Power BI API calls will return "Insufficient privileges" even if the Azure AD permissions are correct.

|  |
|----|
| **app.powerbi.com** → **Settings (gear icon)** → **Admin portal** → **Tenant settings** |

43. Go to https://app.powerbi.com and sign in as a Power BI Administrator.

44. Click the gear icon (Settings) at the top right.

45. Click "Admin portal".

46. In the left menu, click "Tenant settings".

47. Search for "service principals" in the page search or scroll to find the "Developer settings" group.

48. Find the setting called "Allow service principals to use Power BI APIs" and expand it.

49. Switch it to "Enabled".

50. Under "Apply to", you can apply to the whole organisation or a specific security group. For security, create a security group in Azure AD containing only your App Registration's service principal, and select that group.

51. Click "Apply". The setting takes effect within a few minutes.

52. Also enable "Export reports as PDF documents" and "Export reports as PPTX presentations" — these are in the same Tenant settings list under "Export and sharing settings".

**2.11 Test Your Azure AD Credentials**

Before adding credentials to the MCP server, verify they work with a simple curl command. Run this in your terminal (replace the placeholders):

```
# Test Azure AD token (replace the three placeholders)
curl -s -X POST \
"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token" \
-d "grant_type=client_credentials" \
-d "client_id={TEAMS_CLIENT_ID}" \
-d "client_secret={TEAMS_CLIENT_SECRET}" \
-d "scope=https://graph.microsoft.com/.default"
# Success: response contains {"access_token":"eyJ0...", "expires_in": 3599, ...}
# Failure: {"error":"unauthorized_client", ...} — admin consent not granted
# Failure: {"error":"invalid_client", ...} — wrong client_id or client_secret
```

> **Part B: Atlassian Setup**
> Confluence | Jira

**3. Atlassian API Token — Confluence & Jira**

Good news: Atlassian setup is much simpler. You do not need Azure AD, app registrations, or admin consent. You just create an API token tied to a service account, and both Confluence and Jira share that token.

**3.1 What You Need Before Starting**

- An Atlassian Cloud account (the service account that RiskGPT will use)

- Ideally a dedicated service account like riskgpt-svc@yourbank.com rather than a personal login

- Confluence and Jira must be on Atlassian Cloud (atlassian.net) — this guide does not cover Atlassian Data Center/Server

> **IMPORTANT**
> Use a shared service account, not your personal account. If your personal account is disabled or leaves the organisation, the API token stops working.
> Ask IT to create a service account in your Microsoft 365 / Atlassian Admin if you do not already have one.

**3.2 Create the API Token**

|  |
|----|
| **id.atlassian.com** → **Security** → **API tokens** → **Create API token** |

53. Open a browser and go to: https://id.atlassian.com

54. Sign in with the service account email and password.

55. Click your profile picture or name in the top right. Click "Manage account".

56. Click the "Security" tab.

57. Find the section "API tokens" and click "Create and manage API tokens".

58. Click the blue "Create API token" button.

59. In the dialog, enter a label: type RiskGPT-MCP-Connector

60. Click "Create".

61. CRITICAL: A dialog shows your token. Copy it immediately — it is only shown once. If you close this dialog without copying, you must delete it and create a new one.

62. Paste the token into your .env file.

| **ATLASSIAN_API_TOKEN** | Copied from id.atlassian.com → Security → API tokens (shown only once) <br> ATATxxxxxxxxxxxxxxxxxxxxxxxxxxxx |
| --- | --- |

| **ATLASSIAN_USER_EMAIL** | The email address of the service account you logged into id.atlassian.com with <br> riskgpt-svc@yourbank.com |
| --- | --- |

**3.3 Get Your Confluence and Jira URLs**

Your Confluence and Jira URLs are your Atlassian subdomain. They look like: https://yourbank.atlassian.net

63. Open your Confluence or Jira in a browser.

64. Copy the base URL — everything up to and including .atlassian.net (no trailing slash).

65. If your Confluence and Jira are on the same Atlassian Cloud account, the URL is the same for both.

| **CONFLUENCE_BASE_URL** | Your Atlassian Cloud base URL <br> https://yourbank.atlassian.net |
| --- | --- |

| **JIRA_BASE_URL** | Same as Confluence if on the same Atlassian Cloud account <br> https://yourbank.atlassian.net |
| --- | --- |

**3.4 Get Your Confluence Cloud ID**

Some Confluence API v2 calls need the Cloud ID. This is easy to retrieve:

66. In your terminal, run (replace with your actual URL):

```
curl https://yourbank.atlassian.net/_edge/tenant_info
# Response: {"cloudId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx", ...}
# Copy the cloudId value
```

67. Copy the cloudId value from the JSON response.

| **CONFLUENCE_CLOUD_ID** | cloudId from https://yourbank.atlassian.net/_edge/tenant_info <br> xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| --- | --- |

**3.5 Set Confluence Space Permissions**

|                                                                        |
|------------------------------------------------------------------------|
| **Confluence** → **Your Space** → **Space settings** → **Permissions** |

The service account must have view access to each Confluence space you want RiskGPT to read. There are two ways to grant this:

**Option A — Individual spaces (more controlled):**

6)  Open Confluence and navigate to the space (e.g., "Risk Management Policies")

7)  In the bottom-left sidebar, click "Space settings"

8)  Click "Permissions"

9)  Under "Individual users", type the service account email and add it with at least "View" permission

10) Repeat for each space you want to expose to RiskGPT

**Option B — Global Can Use (easier, less controlled):**

11) Go to Confluence Admin → Global Permissions

12) Grant the service account "Can use" global permission

13) This lets the account access all non-restricted spaces

> **NOTE**
> Spaces marked as "Private" or with restrictions will still require explicit permission even with global "Can use".
> The RiskGPT connector will return a 403 error for any space the service account cannot view — it will not silently skip them.

**3.6 Set Jira Project Permissions**

|                                                                 |
|-----------------------------------------------------------------|
| **Jira** → **Your Project** → **Project settings** → **People** |

Similarly, the service account needs access to each Jira project:

14) Open Jira and navigate to the project (e.g., "RISK" or "AUDIT")

15) Click "Project settings" in the bottom-left sidebar

16) Click "People"

17) Click "Add people", search for the service account email, and add it with the "Service Desk Team" or "Member" role

18) For write tools (creating/updating issues), the role must include "Create Issues" and "Edit Issues" permissions

**3.7 Test Your Atlassian Credentials**

```
# Test Confluence access (replace email, token, and yourbank)
curl -u "riskgpt-svc@yourbank.com:YOUR_API_TOKEN" \
"https://yourbank.atlassian.net/wiki/rest/api/space?limit=5"
# Success: {"results": [...], "limit": 5, ...}
# Test Jira access
curl -u "riskgpt-svc@yourbank.com:YOUR_API_TOKEN" \
"https://yourbank.atlassian.net/rest/api/3/project/search?maxResults=5"
# Success: {"values": [...], "total": N}
# Failure: {"statusCode": 401} — wrong email or token
```

**4. Completed .env File — Copy and Fill In**

Once you have all values collected, paste this into your sajhamcpserver/.env file (or your Docker compose env file). Replace every placeholder with the real value.

> # ================================================
> # RiskGPT MCP Server — Connector Credentials
> # CONFIDENTIAL — do not commit to git
> # ================================================
> # Microsoft Azure AD — shared by Teams, Power BI, SharePoint
> AZURE_TENANT_ID=paste-your-tenant-id-here
> # Teams connector
> TEAMS_CLIENT_ID=paste-your-client-id-here
> TEAMS_CLIENT_SECRET=paste-your-client-secret-here
> # Power BI connector (same app registration as Teams)
> POWERBI_CLIENT_ID=same-as-TEAMS_CLIENT_ID
> POWERBI_CLIENT_SECRET=same-as-TEAMS_CLIENT_SECRET
> POWERBI_WORKSPACE_IDS=workspace-guid-1,workspace-guid-2
> # SharePoint connector (same app registration)
> SHAREPOINT_TENANT_ID=same-as-AZURE_TENANT_ID
> SHAREPOINT_CLIENT_ID=same-as-TEAMS_CLIENT_ID
> SHAREPOINT_CLIENT_SECRET=same-as-TEAMS_CLIENT_SECRET
> SHAREPOINT_SITE_URL=https://yourbank.sharepoint.com/sites/your-site
> # Atlassian — shared by Confluence and Jira
> ATLASSIAN_USER_EMAIL=riskgpt-svc@yourbank.com
> ATLASSIAN_API_TOKEN=paste-your-atlassian-token-here
> CONFLUENCE_BASE_URL=https://yourbank.atlassian.net
> CONFLUENCE_CLOUD_ID=from /_edge/tenant_info curl command
> JIRA_BASE_URL=https://yourbank.atlassian.net
> JIRA_DEFAULT_PROJECT=RISK

**5. Completion Checklist**

Use this checklist to confirm setup is complete before handing credentials to the development team.

|  |  |  |  |
|:--:|:--:|:--:|:--:|
|  | **Task** | **Who** | **Done?** |
| **A1** | Azure Tenant ID copied into .env as AZURE_TENANT_ID | Azure Admin |  |
| **A2** | App Registration created in Azure AD / Entra ID | Azure Admin |  |
| **A3** | Client ID copied into .env as TEAMS_CLIENT_ID / POWERBI_CLIENT_ID | Azure Admin |  |
| **A4** | Client Secret created and copied into .env (secret expiry date noted) | Azure Admin |  |
| **A5** | Microsoft Graph permissions added (Section 2.5) | Azure Admin |  |
| **A6** | Power BI Service permissions added (Section 2.6) | Azure Admin |  |
| **A7** | Admin consent granted — all permissions show green checkmarks | Global Admin |  |
| **A8** | Power BI tenant setting "Allow service principals to use Power BI APIs" enabled | PBI Admin |  |
| **A9** | Power BI workspace IDs identified and added to .env | Developer |  |
| **A10** | Azure AD token test (Section 2.11) returns access_token successfully | Developer |  |
| **B1** | Service account created for Atlassian (dedicated, not personal) | IT / Admin |  |
| **B2** | Atlassian API token created and copied into .env | Yourself |  |
| **B3** | Service account email added to .env as ATLASSIAN_USER_EMAIL | Yourself |  |
| **B4** | Confluence base URL and Cloud ID added to .env | Yourself |  |
| **B5** | Service account granted view permission on relevant Confluence spaces | Conf Admin |  |
| **B6** | Service account granted browse access on relevant Jira projects | Jira Admin |  |
| **B7** | Confluence test (Section 3.7) returns space list successfully | Developer |  |
| **B8** | Jira test (Section 3.7) returns project list successfully | Developer |  |
| **C1** | Completed .env file provided securely to developer (not via email — use a secrets vault or 1Password) | Admin |  |
| **C2** | .env file confirmed not committed to git (.gitignore includes .env) | Developer |  |
| **C3** | Secret expiry date added to team calendar for TEAMS_CLIENT_SECRET | Admin |  |

**6. Common Errors & How to Fix Them**

|  |  |  |
|:--:|:--:|:--:|
| **Error** | **Likely Cause** | **Fix** |
| **403 Forbidden — Azure AD** | Admin consent not granted | Go to App Registration → API permissions → Grant admin consent for \<org\> |
| **invalid_client** | Wrong Client ID or Client Secret | Double-check the Client ID (Application ID) and that the Secret has not expired. Generate a new secret if needed. |
| **unauthorized_client** | App not allowed to use client_credentials flow, or permissions not admin-consented | Ensure Application permissions (not Delegated) are used. Re-grant admin consent. |
| **Insufficient privileges — Power BI** | Power BI tenant setting not enabled | Power BI Admin must enable "Allow service principals to use Power BI APIs" in Admin Portal → Tenant settings |
| **401 Unauthorized — Atlassian** | Wrong email or API token | Verify the exact email and token. The token value is the entire string from the creation dialog. |
| **403 on Confluence space** | Service account not in the space permissions | Go to Confluence → Space Settings → Permissions → add the service account |
| **AADSTS7000215** | Invalid client secret — expired or wrong | Generate a new client secret in Azure AD → Certificates & secrets. Update .env with new value. |
| **Response is empty / no results** | Service account has no access to any spaces/projects/teams | Verify the service account is a member of at least one Team, Confluence space, or Jira project |

Once all checklist items are complete, hand the .env file to the developer and they can wire it into the MCP server. The connector tools will be available within 5 minutes via the hot-reload mechanism.
