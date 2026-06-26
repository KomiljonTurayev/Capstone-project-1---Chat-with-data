# Data Insights App — Design Spec
**Date:** 2026-06-26
**Status:** Approved

---

## Overview

A Streamlit-based chat application that lets users query an e-commerce SQLite database using natural language. A Claude-powered agent converts questions into SQL queries, executes them safely, and returns structured answers. The UI also shows business dashboards and supports GitHub Issues for human escalation.

---

## Goals

- Allow non-technical users to ask data questions in plain language
- Never send the full dataset to the LLM — only query results or schema fragments
- Prevent any destructive database operations via a safety layer
- Provide at-a-glance business metrics alongside the chat
- Allow users (or the agent itself) to open a GitHub support ticket

---

## Data Model

SQLite database (`data/ecommerce.db`) seeded with Faker. All 4 tables combined exceed 500 entities.

### Tables

**`customers`** (~200 rows)
| Column | Type |
|--------|------|
| id | INTEGER PK |
| name | TEXT |
| email | TEXT |
| phone | TEXT |
| city | TEXT |
| created_at | DATE |

**`products`** (~50 rows)
| Column | Type |
|--------|------|
| id | INTEGER PK |
| name | TEXT |
| category | TEXT |
| price | REAL |
| stock | INTEGER |

**`orders`** (~300 rows)
| Column | Type |
|--------|------|
| id | INTEGER PK |
| customer_id | INTEGER FK |
| order_date | DATE |
| status | TEXT (pending/shipped/delivered/cancelled) |
| total_amount | REAL |

**`order_items`** (~500 rows)
| Column | Type |
|--------|------|
| id | INTEGER PK |
| order_id | INTEGER FK |
| product_id | INTEGER FK |
| quantity | INTEGER |
| unit_price | REAL |

---

## Agent Design

**Model:** `claude-sonnet-4-6` (Anthropic)

**System prompt responsibilities:**
- Instruct Claude to always call `get_schema()` before writing SQL
- Explicitly forbid generating SQL with DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, REPLACE
- Instruct Claude to suggest a support ticket when it cannot answer after 2 failed attempts
- Define response style: concise, data-focused, table format when listing results

**Conversation memory:** Full message history is kept in Streamlit `session_state` and passed to each Claude API call. No external memory store needed.

---

## Function Calling Tools (minimum 2, implementing 3)

### 1. `get_schema() → str`
Returns all table names, column names, and types as a formatted string. Called by the agent before writing any SQL so it knows the structure.

### 2. `query_database(sql: str) → str`
Executes a read-only SQL query against SQLite. Returns results as a formatted string (max 100 rows to stay within context limits).

**Safety filter (inside this function):**
```python
BLOCKED = ["DELETE", "DROP", "UPDATE", "INSERT",
           "ALTER", "TRUNCATE", "CREATE", "REPLACE"]
```
If any blocked keyword appears in the SQL (case-insensitive), the function raises a `PermissionError` with a clear message and logs the attempt. Never executes.

### 3. `create_github_issue(title: str, body: str) → str`
Uses `PyGithub` to create an issue in the configured repository. Returns the issue URL on success. Reads `GITHUB_TOKEN` and `GITHUB_REPO` from environment variables.

---

## Safety Design

Two-layer protection against destructive operations:

1. **System prompt layer** — Claude is instructed not to generate dangerous SQL. This is the first line of defence.
2. **Code layer** — `safety.py` validates every SQL string before execution. Even if the system prompt is bypassed, the code layer blocks it.

The safety validator logs every blocked attempt to the console with a `[SAFETY BLOCKED]` prefix.

---

## Console Logging

Every significant event is printed to stdout with a timestamp and category tag:

```
[2026-06-26 10:23:01] [USER]   Top 5 mahsulot nima?
[2026-06-26 10:23:01] [TOOL]   get_schema()
[2026-06-26 10:23:02] [TOOL]   query_database(SELECT p.name, ...)
[2026-06-26 10:23:02] [DB]     5 rows returned
[2026-06-26 10:23:03] [AGENT]  Response sent to UI
```

---

## UI Layout (Streamlit)

### Sidebar
- **Dataset Stats card:** total customers, products, orders, total revenue
- **Bar chart:** revenue by product category (Plotly)
- **Sample queries:** 5 clickable buttons that auto-fill the chat input

### Main Area
- **Chat history:** rendered with `st.chat_message`, supports markdown tables
- **Chat input:** `st.chat_input` at the bottom
- **Support ticket button:** always visible below chat; also appears as an inline suggestion from the agent when needed

---

## Support Ticket Logic

Triggered in two ways:

1. **Explicit** — user clicks "Open Support Ticket" button or types "support", "yordam", "muammo", "ticket"
2. **Implicit** — agent fails to answer a question after 2 tool call attempts; it proactively suggests opening a ticket

When triggered, the UI shows a small form (title + description pre-filled by agent context) and calls `create_github_issue()`.

---

## Project File Structure

```
capstone-chat-with-data/
├── app.py              # Streamlit entry point
├── agent.py            # Claude API calls + tool dispatch loop
├── tools.py            # get_schema, query_database, create_github_issue
├── database.py         # SQLite connection helper
├── safety.py           # SQL keyword validator
├── data/
│   └── ecommerce.db    # SQLite database (gitignored if large, seeded via script)
├── scripts/
│   └── seed_data.py    # Populates ecommerce.db using Faker
├── .env                # ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_REPO (not committed)
├── .env.example        # Template for required env vars
├── requirements.txt
└── README.md           # Setup instructions + workflow screenshots
```

---

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude API access |
| `GITHUB_TOKEN` | Personal access token for creating issues |
| `GITHUB_REPO` | Target repo in `owner/repo` format |

---

## Bonus: HF Spaces Deployment

- Add HF Spaces YAML metadata block to `README.md`
- Store secrets (`ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `GITHUB_REPO`) in HF Space settings
- SQLite `.db` file committed to repo (static seed data, ~2MB)
- No additional server infrastructure needed

---

## Out of Scope

- User authentication
- Multi-user session isolation
- Writing/updating database records (intentionally blocked)
- Real-time data sync
