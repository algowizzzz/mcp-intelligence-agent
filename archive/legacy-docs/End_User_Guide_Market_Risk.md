# B-Pulse Digital Worker — End User Guide
### Market Risk Division

---

## 1. Introduction

The B-Pulse Digital Worker is an AI-powered risk intelligence assistant built for the Market Risk team. It connects to your firm's internal data, documents, and collaboration tools, and lets you ask questions in plain language to get exposure summaries, regulatory analysis, market data, and more — all without writing SQL, opening multiple systems, or waiting for reports.

---

## 2. Accessing the Platform

### URL
Open your browser and navigate to the platform URL provided by your administrator (e.g. `https://your-domain.com` or `http://localhost:8000` for local deployments).

### First-Time Login — Onboarding Wizard

New accounts require a one-time setup the first time you sign in. You will be guided through a 3-step wizard:

**Step 1 — Welcome**
- You are shown which Digital Worker you have been assigned to (e.g. *Market Risk Worker*)
- Click **Get Started** to continue

**Step 2 — Your Profile**
- Enter your **Display Name** (your full name, minimum 2 characters)
- Your initials are generated automatically and shown as a preview — this appears as your avatar in the platform
- Click **Continue**

**Step 3 — Set Your Password**
- Enter a new password (**minimum 10 characters**)
- A strength indicator shows how strong your password is — aim for full bar (uppercase + number + special character)
- Confirm your password and click **Complete Setup**
- You are redirected automatically to the chat interface

> **Note:** Your username is provided by your administrator. If you forget your password after setup, contact your administrator — the login screen shows *"Forgot password? Contact your administrator."*

### Returning Login
- Enter your username and password and click **Sign In**
- After 5 failed attempts the account is locked — contact your administrator
- If you are already signed in, you are redirected automatically

### Role-based Redirect
After login, the platform routes you to the correct interface automatically:

| Role | Destination |
|------|-------------|
| User | Chat interface (`mcp-agent.html`) |
| Admin | Admin console (`admin.html`) |
| Super Admin | Admin console (`admin.html`) |

---

## 3. Chat Interface

Once signed in as a user, you land on the **chat interface**. The layout has three areas:

| Area | Purpose |
|------|---------|
| **Left sidebar** | Conversation history, saved chats, active workflow indicator |
| **Centre** | Chat window — type questions, view agent responses, see tool calls |
| **Right panel (Canvas)** | Opens automatically for reports, charts, and structured documents |

### Starting a Conversation
Type your question in the input box at the bottom and press **Enter** or click **Send**.

Pre-built example prompts appear on the welcome screen:
- *Get me the full picture on Royal Bank of Canada*
- *Run a QoQ trend on Goldman Sachs for the last 4 quarters*
- *What are the credit limits and utilization for TD Bank?*
- *Show VaR contribution for JPMorgan Chase at 99% confidence*
- *Latest news and ratings for Deutsche Bank*

---

## 4. What the Agent Can Do

The agent has access to 121+ tools across multiple data sources. All tool calls are visible in the chat as collapsible cards showing the input sent and the output received.

### Counterparty Risk (IRIS CCR)
- Current notional, MTM, PFE, and net exposure for any counterparty
- Credit limit lookup and utilisation percentage
- Historical exposure snapshots for quarter-end trend analysis
- VaR contribution, marginal VaR, and stress loss at configurable confidence levels
- Portfolio breach scan across all counterparties
- Multi-counterparty comparison tables

### Market Data
- Live stock quotes and price history (Yahoo Finance)
- Latest earnings summaries, analyst ratings, and price targets
- Sector and index data

### Regulatory & SEC Filings
- SEC EDGAR 10-K and 10-Q extraction (MD&A, risk factors, segments, financial statements)
- XBRL financial metrics and peer comparison
- Earnings call summaries

### Document Intelligence
- Read and search Word, Excel, and PDF files from your domain data library
- Full-text BM25 search across all uploaded documents
- Template filling for standard reports

### Web & News Intelligence
- Real-time news search via Tavily
- Domain-specific research (regulatory sites, central banks, rating agencies)
- Wikipedia lookups for background context

### Python & Analytics
- Run pandas/numpy/plotly code in a sandboxed environment
- Generate interactive charts (bar, line, area, scatter, histogram, pie, heatmap, box, treemap, waterfall)
- GARCH volatility modelling, portfolio optimisation (riskfolio), QuantLib pricing

### Collaboration Tools (if enabled by admin)
- Outlook: read, search, reply, and send emails
- Teams: read channel messages, get meeting details, send messages
- SharePoint: browse sites, read and search documents
- Confluence: search and read wiki pages
- Jira: view issues, create tickets, add comments
- Power BI: list workspaces, reports, and trigger dataset refresh

---

## 5. The Canvas Panel

For longer responses — reports, analyses, regulatory documents — the agent opens the **Canvas Panel** on the right side of the screen automatically.

- The canvas streams content in real time as the agent writes
- It only opens **after** all data has been retrieved — never with placeholder content
- The chat bubble shows a one-line summary; full content is in the canvas

### Canvas Controls

| Button | Action |
|--------|--------|
| **Export as Word** | Downloads the canvas content as a `.docx` file |
| **↓ Save** | Saves the document to your personal data folder (My Data) |
| **✕** | Closes the canvas (chat remains) |
| **View Report** (in chat bubble) | Re-opens the canvas for this message |

### Charts
When the agent generates a chart, it appears in the canvas as an interactive Plotly iframe:
- Hover over data points for values
- Use the Plotly toolbar (top-right of chart) to zoom, pan, download as PNG
- Click **View Chart** in the chat bubble to re-open

---

## 6. File Uploads

You can upload files to give the agent context for your question.

**Supported formats:** PDF, Word (.docx), Excel (.xlsx/.xls), CSV, JSON, Parquet, Markdown (.md), TXT, PNG, JPG  
**Max file size:** 50 MB per file

To upload: use the attachment icon in the chat input, or ask your admin to add files to the Domain Data library.

---

## 7. Workflows

Workflows are pre-built multi-step analysis sequences saved as Markdown files. When a workflow is active, the agent follows its steps automatically.

- Browse available workflows from the left sidebar under **Workflows**
- Click a workflow to preview it in the canvas
- Click **Select this Workflow** to attach it to the current conversation
- Ask your question as normal — the agent executes the workflow steps

---

## 8. Conversation History

- All conversations are saved automatically in the left sidebar
- Click any previous conversation to restore it — the full message history and tool outputs are restored
- Reports and charts from previous conversations can be re-opened via the **View Report** / **View Chart** buttons in each message

---

## 9. Settings & Preferences

Click **Settings** in the left sidebar to access:
- **Theme toggle** — switch between Dark and Light mode
- **Change Password** — requires your current password plus a new password (minimum 10 characters)

---

## 10. Example Queries

### Counterparty Risk
```
What is the current net exposure and PFE for Barclays?
Show me all counterparties with utilisation above 80%
Run a quarterly exposure trend for Goldman Sachs over the last 4 quarters
Which counterparties have a credit rating below BBB?
```

### Market Intelligence
```
Latest news on Deutsche Bank from the last 7 days
Get me RBC's Q4 2024 earnings summary from their 10-K filing
Compare Tier 1 capital ratios for JPMorgan, Citi, and Wells Fargo
What is the current price and 52-week range for BAC?
```

### Analytics & Reporting
```
Generate a bar chart of VaR contributions by desk
Run a GARCH(1,1) volatility model on EURUSD using the last 252 days
Build a heatmap of counterparty exposure by sector and rating
Export the top 20 counterparties by net MTM as an Excel file
```

### Collaboration
```
Search my Outlook for emails from risk@bank.com in the last 30 days
What did the Risk Committee Teams channel discuss this week?
Create a Jira ticket for the limit breach on Nomura
Find the FRTB policy document in Confluence
```

---

## 11. Troubleshooting

| Issue | Action |
|-------|--------|
| Blank page after login | Hard refresh (`Cmd+Shift+R` / `Ctrl+Shift+R`) |
| "Session expired" message | Sign out and sign back in |
| Agent not responding | Check the context gauge (top right) — if near 100%, start a new conversation |
| Tool call shows an error | The agent retries automatically; if it persists, rephrase your question |
| Canvas didn't open | Scroll up in chat — a **View Report** button appears on the message |
| Chart shows 404 | The chart file may have been cleaned up — regenerate by repeating the query |
| Forgot password | Contact your administrator (self-service reset not available) |
| Account locked | 5 failed login attempts locks the account — contact your administrator |

---

## 12. Data Privacy & Security

- All conversations are scoped to your assigned worker — other workers cannot see your data
- Files you upload to **My Data** are private to your account
- Files in **Domain Data** are shared within your worker (visible to all users on that worker)
- Files in the **Shared Library** are accessible across all workers
- Your session token expires after 7 days — you will be prompted to sign in again

---

*For administrator functions (managing users, tools, domain data, workflows) see the **Admin User Guide**.*
