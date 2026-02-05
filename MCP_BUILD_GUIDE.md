# MCP Build Guide — NetSuite Finance Assistant (Step-by-Step)

This document explains **how to build, understand, and extend** the MCP-based NetSuite Finance Assistant.
It is intended for engineers joining the project or reviewers who want a clear, end-to-end picture.

---

## 1) What we are building

We are building a **local MCP server (Python)** that exposes finance-focused tools.
Claude Desktop connects to this MCP server as a **connector** and calls these tools during conversation.

### Core principles
- Claude **never** connects to NetSuite directly
- All credentials and tokens live only in the MCP server
- NetSuite access is **read-only** (SuiteQL SELECT only)
- Business logic lives in tools, not in prompts
- Automation is **safe by default** (draft-first, dry-run sending)

---

## 2) High-level architecture

```
Claude Desktop
     |
     | (tool call via MCP)
     v
MCP Server (Python)
     |
     | (OAuth 2.0 + REST)
     v
NetSuite (SuiteQL, read-only)
```

---

## 3) End-to-end flow

1. User asks a question in Claude Desktop
2. Claude selects the appropriate MCP tool
3. Claude sends a structured tool call (JSON)
4. MCP server executes the mapped Python function
5. Python function queries NetSuite using SuiteQL
6. NetSuite returns structured JSON
7. Tool processes, aggregates, and scores data
8. MCP server returns structured output
9. Claude explains results in natural language

---

## 4) Repository structure

```
netsuite-mcp-finance-assistant/
├── mcp_server.py              # MCP tool registration + dispatch
├── finance_tools.py           # Finance logic (queries, aging, risk, emails)
├── netsuite_client.py         # OAuth 2.0 + SuiteQL REST client
├── .env.example               # Environment variable template
├── MCP_BUILD_GUIDE.md         # This file
├── README.md
└── tests/
```

---

## 5) NetSuite setup (one-time)

### A) Integration
- Create NetSuite Integration
- Enable OAuth 2.0
- Save Client ID and Client Secret

### B) Permissions
- Enable REST Web Services
- Enable SuiteQL / REST Query
- Use a role with **read-only finance access**

### C) Redirect URI
- Example:
  ```
  http://localhost:8000/oauth/callback
  ```
- Must match exactly in NetSuite and local config

---

## 6) Environment variables

Create a local `.env` file (never commit secrets).

Example:
```
NETSUITE_ACCOUNT_ID=...
NETSUITE_BASE_URL=https://<account>.suitetalk.api.netsuite.com
OAUTH_CLIENT_ID=...
OAUTH_CLIENT_SECRET=...
OAUTH_REDIRECT_URI=http://localhost:8000/oauth/callback

# Email (demo-safe)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=...
```

---

## 7) Authentication flow (OAuth 2.0)

1. User authorizes the integration in NetSuite
2. NetSuite redirects with an authorization code
3. MCP server exchanges code for access + refresh tokens
4. `NetSuiteClient` attaches token as:
   ```
   Authorization: Bearer <access_token>
   ```
5. Tokens are refreshed automatically when expired

Claude never sees tokens.

---

## 8) How data is fetched from NetSuite

All tools use **SuiteQL SELECT queries** via NetSuite REST Query API.

### Core records used
- `transaction` (Customer invoices, `type = 'CustInvc'`)
- `entity` (Customer name / identifier)

### Guardrails
- SELECT only
- No create, update, delete
- No payments or financial postings

---

## 9) MCP server responsibilities (`mcp_server.py`)

- Registers all tools with:
  - name
  - description
  - input schema
- Receives tool calls from Claude
- Dispatches calls to functions in `finance_tools.py`
- Returns structured JSON responses

---

## 10) Claude Desktop connector configuration

Example (Windows):

```json
{
  "mcpServers": {
    "netsuite-finance": {
      "command": "python",
      "args": ["mcp_server.py"],
      "cwd": "C:\\Path\\To\\netsuite-mcp-finance-assistant"
    }
  }
}
```

Restart Claude Desktop after adding.

---

## 11) Tools implemented (complete list)

### A) Core invoice & revenue tools

#### 1. `overdue_invoices(days)`
- Returns invoices overdue within N days
- Uses due date vs current date
- Supports collections visibility

#### 2. `unpaid_invoices_over_threshold(threshold)`
- Returns invoices with unpaid balance above threshold
- Highlights high-exposure invoices

#### 3. `total_revenue(start_date, end_date)`
- Aggregates total invoice revenue for a period
- Uses invoice transaction totals

#### 4. `top_customers_by_invoice_amount(start_date, end_date, top_n)`
- Groups invoices by customer
- Ranks customers by total billed amount

---

### B) Accounts receivable intelligence tools

#### 5. `ar_aging_summary_tool`
- Pulls all open invoices
- Buckets into aging ranges (current, 0–10, 11–20, 21–30, 31+)
- Returns totals, counts, and top overdue customers

#### 6. `customer_risk_profiles_tool`
- Aggregates invoices per customer
- Calculates:
  - overdue ratio
  - invoice age severity
  - weighted aging buckets
- Produces explainable risk scores (High / Medium / Low)

#### 7. `collections_priority_queue_tool`
- Combines:
  - risk score
  - overdue amount
  - invoice age
  - severity mix
- Ranks customers for collections follow-up
- Recommends next action

#### 8. `daily_ar_brief_tool`
- One-call summary for AR operations
- Includes:
  - aging snapshot
  - top risk customers
  - today’s collections priority queue
  - escalations

---

### C) Email workflow tools (safe by design)

#### 9. `draft_collections_emails_tool`
- Uses collections priority output
- Selects tone based on severity
- Generates subject + email body
- Drafts only (no sending)

#### 10. `send_collections_emails_tool`
- Sends or simulates sending emails
- Defaults:
  - `dry_run = true`
  - routes to `ar-test@company.com`
- Limits volume and supports test recipients

---

## 12) Demo prompts (tool-driven)

- Show me invoices overdue in the last 30 days
- Which invoices have more than $1,000 unpaid
- What is our total invoice revenue this quarter
- Who are our top 10 customers by invoice amount this quarter
- Give me an accounts receivable aging summary
- Which customers are high risk for late payment, and why
- Who should my accounts receivable team contact first today
- Give me today’s daily accounts receivable brief
- Draft collection emails for the highest-priority customers
- Send collection emails for the top priority customers in dry-run mode

---

## 13) Safety & governance defaults

- Read-only SuiteQL
- Deterministic tool logic
- No prompt-based calculations
- Email sending is opt-in and reviewable
- Test inbox routing for demos

---

## 14) How to add a new tool

1. Define the business question
2. Write SuiteQL SELECT query
3. Normalize and validate data
4. Add scoring or aggregation logic
5. Register tool in `mcp_server.py`
6. Add demo prompt
7. Test locally

---

## 15) Troubleshooting

- OAuth issues → redirect URI mismatch
- 401 errors → token expired or account mismatch
- SuiteQL errors → permissions or field names
- Tools not visible → MCP server path or restart Claude

---

## 16) Key takeaway

Claude reasons.
MCP orchestrates.
Tools execute.
NetSuite stays protected.
