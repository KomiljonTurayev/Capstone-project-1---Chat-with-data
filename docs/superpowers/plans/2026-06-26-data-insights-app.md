# Data Insights App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Streamlit chat app where users query an e-commerce SQLite database in natural language via a Claude agent with function calling, safety filtering, and GitHub Issues support tickets.

**Architecture:** Claude agent receives user messages, calls `get_schema()` + `query_database(sql)` tools to fetch only the data needed, returns structured answers. A safety layer blocks all destructive SQL keywords before execution. Streamlit renders the chat alongside a live business dashboard in the sidebar.

**Tech Stack:** Python 3.11+, Streamlit, Anthropic SDK (`anthropic`), SQLite3, PyGithub, Plotly, Faker, python-dotenv, pytest

## Global Constraints

- Python 3.11+
- Model: `claude-sonnet-4-6`
- Database: SQLite at `data/ecommerce.db` — never PostgreSQL or other external DB
- LLM never receives full table dumps — only schema strings or query result rows (max 100)
- Blocked SQL keywords (case-insensitive): DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, REPLACE
- All console logs format: `[YYYY-MM-DD HH:MM:SS] [TAG]  message`
- No user authentication, no multi-user isolation
- All code in root of repo (main branch), no subdirectory packaging
- `.env` is never committed — use `.env.example` as template

---

## File Map

| File | Responsibility |
|------|---------------|
| `safety.py` | `validate_sql(sql)` — raises `PermissionError` on blocked keywords |
| `database.py` | `get_connection()` — returns `sqlite3.Connection` to `data/ecommerce.db` |
| `scripts/seed_data.py` | Creates tables + inserts 1050+ rows using Faker; idempotent |
| `tools.py` | `get_schema()`, `query_database(sql)`, `create_github_issue(title, body)`, `TOOL_DEFINITIONS` list |
| `agent.py` | `log(tag, msg)`, `SYSTEM_PROMPT`, `run_agent(messages) -> str` — Claude loop + tool dispatch |
| `app.py` | Streamlit UI: sidebar stats/chart/sample queries, chat area, support ticket form |
| `tests/test_safety.py` | Unit tests for safety validator |
| `tests/test_tools.py` | Unit tests for tools (mocked GitHub, real SQLite) |
| `tests/test_agent.py` | Unit tests for tool dispatch with mocked Anthropic client |
| `requirements.txt` | All dependencies pinned to minor version |
| `.env.example` | Template for ANTHROPIC_API_KEY, GITHUB_TOKEN, GITHUB_REPO |
| `README.md` | Setup guide + HF Spaces YAML metadata + workflow screenshots |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `data/.gitkeep`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

**Interfaces:**
- Produces: nothing consumed by code — just project skeleton

- [ ] **Step 1: Create requirements.txt**

```
anthropic>=0.40.0
streamlit>=1.40.0
python-dotenv>=1.0.0
PyGithub>=2.4.0
plotly>=5.24.0
pandas>=2.2.0
faker>=30.0.0
pytest>=8.3.0
pytest-mock>=3.14.0
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=owner/repository-name
```

- [ ] **Step 3: Create .gitignore**

```
.env
data/ecommerce.db
__pycache__/
*.pyc
.pytest_cache/
.streamlit/secrets.toml
```

- [ ] **Step 4: Create empty placeholder files**

Create `data/.gitkeep`, `scripts/__init__.py`, `tests/__init__.py` — all empty.

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install without errors.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .env.example .gitignore data/.gitkeep scripts/__init__.py tests/__init__.py
git commit -m "chore: project scaffolding and dependencies"
```

---

## Task 2: Database Layer

**Files:**
- Create: `database.py`
- Create: `scripts/seed_data.py`

**Interfaces:**
- Produces: `get_connection() -> sqlite3.Connection` (used by `tools.py`, `app.py`, `scripts/seed_data.py`)

- [ ] **Step 1: Write failing test**

Create `tests/test_database.py`:

```python
import sqlite3
import pytest
from database import get_connection

def test_get_connection_returns_connection():
    conn = get_connection()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()

def test_tables_exist_after_seed():
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {row[0] for row in tables}
    assert {"customers", "products", "orders", "order_items"}.issubset(table_names)
    conn.close()

def test_row_counts_meet_minimum():
    conn = get_connection()
    customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    orders = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    order_items = conn.execute("SELECT COUNT(*) FROM order_items").fetchone()[0]
    assert customers >= 200
    assert products >= 50
    assert orders >= 300
    assert order_items >= 500
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_database.py -v
```

Expected: ImportError — `database` module not found.

- [ ] **Step 3: Create database.py**

```python
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "ecommerce.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
```

- [ ] **Step 4: Create scripts/seed_data.py**

```python
import sys
import os
import sqlite3
import random
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from faker import Faker
from database import get_connection

fake = Faker()
random.seed(42)
Faker.seed(42)

CATEGORIES = ["Electronics", "Clothing", "Books", "Sports", "Home & Kitchen"]
STATUSES = ["pending", "shipped", "delivered", "cancelled"]

PRODUCT_NAMES = {
    "Electronics": ["Laptop", "Smartphone", "Headphones", "Tablet", "Smartwatch",
                    "Keyboard", "Mouse", "Monitor", "Webcam", "Speaker", "Camera"],
    "Clothing":    ["T-Shirt", "Jeans", "Jacket", "Sneakers", "Dress",
                    "Hoodie", "Shorts", "Boots", "Scarf", "Hat"],
    "Books":       ["Python Basics", "Data Science 101", "Clean Code", "Deep Learning",
                    "Fiction Novel", "History Book", "Cookbook", "Self-Help Guide"],
    "Sports":      ["Yoga Mat", "Dumbbell Set", "Running Shoes", "Water Bottle",
                    "Resistance Bands", "Jump Rope", "Gym Gloves", "Protein Shaker"],
    "Home & Kitchen": ["Coffee Maker", "Blender", "Air Fryer", "Toaster", "Kettle",
                       "Cutting Board", "Knife Set", "Storage Containers", "Vacuum"],
}


def create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            phone      TEXT,
            city       TEXT,
            created_at DATE    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT    NOT NULL,
            category TEXT    NOT NULL,
            price    REAL    NOT NULL,
            stock    INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id  INTEGER NOT NULL REFERENCES customers(id),
            order_date   DATE    NOT NULL,
            status       TEXT    NOT NULL,
            total_amount REAL    NOT NULL
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL REFERENCES orders(id),
            product_id  INTEGER NOT NULL REFERENCES products(id),
            quantity    INTEGER NOT NULL,
            unit_price  REAL    NOT NULL
        );
    """)
    conn.commit()


def seed_customers(conn: sqlite3.Connection, n: int = 200) -> list[int]:
    rows = []
    emails = set()
    while len(rows) < n:
        email = fake.unique.email()
        if email in emails:
            continue
        emails.add(email)
        start = date(2021, 1, 1)
        created = start + timedelta(days=random.randint(0, 1095))
        rows.append((fake.name(), email, fake.phone_number()[:20],
                     fake.city(), created.isoformat()))
    conn.executemany(
        "INSERT INTO customers (name, email, phone, city, created_at) VALUES (?,?,?,?,?)",
        rows,
    )
    conn.commit()
    return [r[0] for r in conn.execute("SELECT id FROM customers").fetchall()]


def seed_products(conn: sqlite3.Connection) -> list[int]:
    rows = []
    for category, names in PRODUCT_NAMES.items():
        for name in names:
            price = round(random.uniform(5.0, 999.99), 2)
            stock = random.randint(0, 200)
            rows.append((name, category, price, stock))
    conn.executemany(
        "INSERT INTO products (name, category, price, stock) VALUES (?,?,?,?)",
        rows,
    )
    conn.commit()
    return [r[0] for r in conn.execute("SELECT id FROM products").fetchall()]


def seed_orders(
    conn: sqlite3.Connection,
    customer_ids: list[int],
    product_ids: list[int],
    n: int = 300,
) -> None:
    for _ in range(n):
        customer_id = random.choice(customer_ids)
        start = date(2022, 1, 1)
        order_date = start + timedelta(days=random.randint(0, 730))
        status = random.choices(STATUSES, weights=[15, 20, 55, 10])[0]

        item_count = random.randint(1, 5)
        chosen_products = random.sample(product_ids, min(item_count, len(product_ids)))
        items = []
        total = 0.0
        for pid in chosen_products:
            qty = random.randint(1, 4)
            price = conn.execute(
                "SELECT price FROM products WHERE id=?", (pid,)
            ).fetchone()[0]
            total += qty * price
            items.append((pid, qty, price))

        cur = conn.execute(
            "INSERT INTO orders (customer_id, order_date, status, total_amount) VALUES (?,?,?,?)",
            (customer_id, order_date.isoformat(), status, round(total, 2)),
        )
        order_id = cur.lastrowid
        conn.executemany(
            "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
            [(order_id, pid, qty, price) for pid, qty, price in items],
        )
    conn.commit()


def already_seeded(conn: sqlite3.Connection) -> bool:
    try:
        count = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        return count > 0
    except sqlite3.OperationalError:
        return False


def main() -> None:
    conn = get_connection()
    if already_seeded(conn):
        print("Database already seeded — skipping.")
        conn.close()
        return
    print("Creating tables...")
    create_tables(conn)
    print("Seeding customers...")
    customer_ids = seed_customers(conn, 200)
    print("Seeding products...")
    product_ids = seed_products(conn)
    print("Seeding orders and order_items...")
    seed_orders(conn, customer_ids, product_ids, 300)
    counts = {
        t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        for t in ("customers", "products", "orders", "order_items")
    }
    print("Done!", counts)
    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run seed script**

```bash
python scripts/seed_data.py
```

Expected output:
```
Creating tables...
Seeding customers...
Seeding products...
Seeding orders and order_items...
Done! {'customers': 200, 'products': 46, 'orders': 300, 'order_items': 900+}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_database.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add database.py scripts/seed_data.py tests/test_database.py
git commit -m "feat: database layer and seed data (1050+ rows)"
```

---

## Task 3: Safety Layer

**Files:**
- Create: `safety.py`
- Create: `tests/test_safety.py`

**Interfaces:**
- Produces: `validate_sql(sql: str) -> None` — raises `PermissionError` with message if blocked keyword found (used by `tools.py`)

- [ ] **Step 1: Write failing test**

Create `tests/test_safety.py`:

```python
import pytest
from safety import validate_sql

@pytest.mark.parametrize("sql", [
    "DELETE FROM customers WHERE id=1",
    "delete from orders",
    "DROP TABLE products",
    "drop table products",
    "UPDATE customers SET name='x'",
    "INSERT INTO customers VALUES (1,'a','b',null,null,null)",
    "ALTER TABLE customers ADD COLUMN x TEXT",
    "TRUNCATE TABLE orders",
    "CREATE TABLE foo (id INTEGER)",
    "REPLACE INTO customers VALUES (1,'a','b',null,null,null)",
    "SELECT * FROM customers; DROP TABLE orders;",
])
def test_dangerous_sql_is_blocked(sql):
    with pytest.raises(PermissionError, match="blocked"):
        validate_sql(sql)

@pytest.mark.parametrize("sql", [
    "SELECT * FROM customers",
    "SELECT COUNT(*) FROM orders",
    "SELECT p.name, SUM(oi.quantity) FROM products p JOIN order_items oi ON p.id=oi.product_id GROUP BY p.name",
    "SELECT c.name, SUM(o.total_amount) FROM customers c JOIN orders o ON c.id=o.customer_id GROUP BY c.id ORDER BY 2 DESC LIMIT 5",
])
def test_safe_sql_passes(sql):
    validate_sql(sql)  # must not raise
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_safety.py -v
```

Expected: ImportError — `safety` module not found.

- [ ] **Step 3: Create safety.py**

```python
import re
from datetime import datetime

BLOCKED_KEYWORDS = [
    "DELETE", "DROP", "UPDATE", "INSERT",
    "ALTER", "TRUNCATE", "CREATE", "REPLACE",
]

_BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def validate_sql(sql: str) -> None:
    match = _BLOCKED_PATTERN.search(sql)
    if match:
        keyword = match.group(1).upper()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [SAFETY BLOCKED]  keyword '{keyword}' in: {sql[:80]}")
        raise PermissionError(
            f"SQL operation blocked: '{keyword}' is not allowed. "
            "Only SELECT queries are permitted."
        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_safety.py -v
```

Expected: all 15 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add safety.py tests/test_safety.py
git commit -m "feat: SQL safety validator blocks destructive operations"
```

---

## Task 4: Tools

**Files:**
- Create: `tools.py`
- Create: `tests/test_tools.py`

**Interfaces:**
- Consumes: `validate_sql(sql)` from `safety.py`, `get_connection()` from `database.py`
- Produces:
  - `get_schema() -> str`
  - `query_database(sql: str) -> str`
  - `create_github_issue(title: str, body: str) -> str`
  - `TOOL_DEFINITIONS: list[dict]` — Anthropic tool schemas (used by `agent.py`)
  - `dispatch_tool(name: str, inputs: dict) -> str` — routes tool name to function (used by `agent.py`)

- [ ] **Step 1: Write failing tests**

Create `tests/test_tools.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from tools import get_schema, query_database, create_github_issue, dispatch_tool

def test_get_schema_contains_table_names():
    schema = get_schema()
    assert "customers" in schema
    assert "products" in schema
    assert "orders" in schema
    assert "order_items" in schema

def test_get_schema_contains_column_names():
    schema = get_schema()
    assert "email" in schema
    assert "total_amount" in schema
    assert "category" in schema

def test_query_database_returns_results():
    result = query_database("SELECT COUNT(*) as cnt FROM customers")
    assert "cnt" in result or "200" in result or "count" in result.lower()

def test_query_database_blocks_dangerous_sql():
    with pytest.raises(PermissionError):
        query_database("DELETE FROM customers")

def test_query_database_limits_rows():
    result = query_database("SELECT * FROM order_items")
    # result should be a string, not crash
    assert isinstance(result, str)
    # count result rows — header + data, max 101 lines
    lines = [l for l in result.strip().split("\n") if l.strip()]
    assert len(lines) <= 102  # header + 100 rows + possible footer note

def test_create_github_issue_returns_url(mocker):
    mock_repo = MagicMock()
    mock_issue = MagicMock()
    mock_issue.html_url = "https://github.com/owner/repo/issues/1"
    mock_repo.create_issue.return_value = mock_issue

    mock_github = mocker.patch("tools.Github")
    mock_github.return_value.get_repo.return_value = mock_repo

    mocker.patch.dict("os.environ", {
        "GITHUB_TOKEN": "fake-token",
        "GITHUB_REPO": "owner/repo",
    })

    url = create_github_issue("Test Issue", "Test body")
    assert url == "https://github.com/owner/repo/issues/1"
    mock_repo.create_issue.assert_called_once_with(title="Test Issue", body="Test body")

def test_dispatch_tool_routes_get_schema():
    result = dispatch_tool("get_schema", {})
    assert "customers" in result

def test_dispatch_tool_routes_query_database():
    result = dispatch_tool("query_database", {"sql": "SELECT COUNT(*) FROM products"})
    assert isinstance(result, str)

def test_dispatch_tool_unknown_tool():
    result = dispatch_tool("nonexistent_tool", {})
    assert "Unknown tool" in result
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_tools.py -v
```

Expected: ImportError — `tools` module not found.

- [ ] **Step 3: Create tools.py**

```python
import os
import sqlite3
from datetime import datetime

from github import Github

from database import get_connection
from safety import validate_sql

MAX_ROWS = 100


def get_schema() -> str:
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    lines = []
    for (table_name,) in tables:
        cols = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        col_defs = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        lines.append(f"Table: {table_name} ({col_defs})")
    conn.close()
    return "\n".join(lines)


def query_database(sql: str) -> str:
    validate_sql(sql)
    conn = get_connection()
    try:
        cur = conn.execute(sql)
        rows = cur.fetchmany(MAX_ROWS)
        if not rows:
            return "Query returned no results."
        col_names = [d[0] for d in cur.description]
        header = " | ".join(col_names)
        separator = "-" * len(header)
        data_lines = [" | ".join(str(v) for v in row) for row in rows]
        result = "\n".join([header, separator] + data_lines)
        extra = cur.fetchone()
        if extra:
            result += f"\n(Showing first {MAX_ROWS} rows only)"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [DB]     {len(rows)} rows returned")
        return result
    finally:
        conn.close()


def create_github_issue(title: str, body: str) -> str:
    token = os.environ["GITHUB_TOKEN"]
    repo_name = os.environ["GITHUB_REPO"]
    gh = Github(token)
    repo = gh.get_repo(repo_name)
    issue = repo.create_issue(title=title, body=body)
    return issue.html_url


def dispatch_tool(name: str, inputs: dict) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        if name == "get_schema":
            print(f"[{timestamp}] [TOOL]   get_schema()")
            return get_schema()
        elif name == "query_database":
            sql = inputs["sql"]
            print(f"[{timestamp}] [TOOL]   query_database({sql[:60]}...)")
            return query_database(sql)
        elif name == "create_github_issue":
            print(f"[{timestamp}] [TOOL]   create_github_issue({inputs.get('title', '')[:40]})")
            return create_github_issue(inputs["title"], inputs["body"])
        else:
            return f"Unknown tool: {name}"
    except PermissionError as e:
        return f"[BLOCKED] {e}"
    except Exception as e:
        return f"[ERROR] {e}"


TOOL_DEFINITIONS = [
    {
        "name": "get_schema",
        "description": (
            "Returns the full database schema: table names and their columns with types. "
            "Always call this first before writing any SQL query."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "query_database",
        "description": (
            "Executes a read-only SQL SELECT query against the e-commerce database "
            "and returns results as a formatted table. Maximum 100 rows returned. "
            "Never use DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, or REPLACE."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A valid SQLite SELECT query.",
                }
            },
            "required": ["sql"],
        },
    },
    {
        "name": "create_github_issue",
        "description": (
            "Creates a GitHub support ticket so a human agent can help the user. "
            "Use this when the user asks for support, mentions a problem you cannot solve, "
            "or after 2 failed attempts to answer a question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Short, clear issue title summarising the user's problem.",
                },
                "body": {
                    "type": "string",
                    "description": (
                        "Detailed description of the user's question or problem, "
                        "including what was tried and what failed."
                    ),
                },
            },
            "required": ["title", "body"],
        },
    },
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_tools.py -v
```

Expected: all 9 tests PASS (test_create_github_issue uses mocker — requires `pytest-mock`).

- [ ] **Step 5: Commit**

```bash
git add tools.py tests/test_tools.py
git commit -m "feat: tools — get_schema, query_database, create_github_issue + Anthropic definitions"
```

---

## Task 5: Agent

**Files:**
- Create: `agent.py`
- Create: `tests/test_agent.py`

**Interfaces:**
- Consumes: `TOOL_DEFINITIONS` from `tools.py`, `dispatch_tool(name, inputs)` from `tools.py`
- Produces: `run_agent(messages: list[dict]) -> str` (used by `app.py`)
- Produces: `log(tag: str, message: str) -> None` (internal utility, also usable from `app.py`)

- [ ] **Step 1: Write failing tests**

Create `tests/test_agent.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from agent import log, run_agent

def test_log_prints_formatted_message(capsys):
    log("USER", "hello world")
    captured = capsys.readouterr()
    assert "[USER]" in captured.out
    assert "hello world" in captured.out

def test_run_agent_returns_string_on_end_turn(mocker):
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [MagicMock(type="text", text="Here is your answer.")]

    mock_client = mocker.patch("agent.client")
    mock_client.messages.create.return_value = mock_response

    result = run_agent([{"role": "user", "content": "Hello"}])
    assert result == "Here is your answer."

def test_run_agent_dispatches_tool_and_continues(mocker):
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "get_schema"
    tool_block.id = "tool_123"
    tool_block.input = {}

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "The schema is..."

    tool_response = MagicMock()
    tool_response.stop_reason = "tool_use"
    tool_response.content = [tool_block]

    end_response = MagicMock()
    end_response.stop_reason = "end_turn"
    end_response.content = [text_block]

    mock_client = mocker.patch("agent.client")
    mock_client.messages.create.side_effect = [tool_response, end_response]

    mock_dispatch = mocker.patch("agent.dispatch_tool", return_value="schema result")

    result = run_agent([{"role": "user", "content": "What tables exist?"}])
    assert result == "The schema is..."
    mock_dispatch.assert_called_once_with("get_schema", {})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent.py -v
```

Expected: ImportError — `agent` module not found.

- [ ] **Step 3: Create agent.py**

```python
import os
from datetime import datetime

import anthropic
from dotenv import load_dotenv

from tools import TOOL_DEFINITIONS, dispatch_tool

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

SYSTEM_PROMPT = """You are a helpful data analyst assistant for an e-commerce business.
You help users understand their data by querying the SQLite database.

RULES:
1. Always call get_schema() FIRST before writing any SQL query.
2. Never generate SQL with: DELETE, DROP, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, REPLACE.
3. Only write SELECT queries.
4. Return results in a clear, concise format. Use markdown tables when listing multiple rows.
5. If you cannot answer a question after 2 attempts, suggest opening a support ticket.
6. When the user mentions "support", "yordam", "muammo", or "ticket", call create_github_issue.
7. Keep answers data-focused and concise.
"""

SUPPORT_TRIGGERS = {"support", "yordam", "muammo", "ticket", "help", "human"}


def log(tag: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tag:<8}]  {message}")


def run_agent(messages: list[dict]) -> str:
    failed_attempts = 0

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            log("AGENT", "Response sent to UI")
            return text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result = dispatch_tool(block.name, block.input)
                if "[ERROR]" in result:
                    failed_attempts += 1
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            messages = messages + [
                {"role": "assistant", "content": response.content},
                {"role": "user", "content": tool_results},
            ]

            if failed_attempts >= 2:
                messages = messages + [{
                    "role": "user",
                    "content": (
                        "You have failed to answer this question twice. "
                        "Please suggest opening a support ticket using create_github_issue."
                    ),
                }]
                failed_attempts = 0
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add agent.py tests/test_agent.py
git commit -m "feat: Claude agent with tool dispatch loop and console logging"
```

---

## Task 6: Streamlit UI

**Files:**
- Create: `app.py`

**Interfaces:**
- Consumes: `run_agent(messages) -> str` from `agent.py`
- Consumes: `get_connection()` from `database.py`
- Consumes: `create_github_issue(title, body)` from `tools.py`
- Consumes: `log(tag, message)` from `agent.py`

No automated unit tests for Streamlit — verify manually by running the app.

- [ ] **Step 1: Create app.py**

```python
import os
import streamlit as st
import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

from agent import run_agent, log, SUPPORT_TRIGGERS
from database import get_connection
from tools import create_github_issue

load_dotenv()

st.set_page_config(
    page_title="Data Insights App",
    page_icon="🛒",
    layout="wide",
)

SAMPLE_QUERIES = [
    "Top 5 mahsulotni sotuvlar bo'yicha ko'rsat",
    "Oylik daromad dinamikasini ko'rsat",
    "Eng faol 5 mijozni ko'rsat",
    "Kategoriya bo'yicha umumiy daromadni ko'rsat",
    "Oxirgi 10 buyurtmani ko'rsat",
]


def load_sidebar_stats() -> dict:
    conn = get_connection()
    stats = {
        "customers": conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0],
        "products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "orders": conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue": conn.execute(
            "SELECT COALESCE(ROUND(SUM(total_amount),2),0) FROM orders WHERE status='delivered'"
        ).fetchone()[0],
    }
    conn.close()
    return stats


def load_category_chart() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.status = 'delivered'
        GROUP BY p.category
        ORDER BY revenue DESC
        """,
        conn,
    )
    conn.close()
    return df


def init_session_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "show_ticket_form" not in st.session_state:
        st.session_state.show_ticket_form = False
    if "pending_query" not in st.session_state:
        st.session_state.pending_query = None


def render_sidebar() -> None:
    with st.sidebar:
        st.title("🛒 Data Insights")
        st.subheader("📊 Dataset Info")

        stats = load_sidebar_stats()
        col1, col2 = st.columns(2)
        col1.metric("Mijozlar", stats["customers"])
        col2.metric("Mahsulotlar", stats["products"])
        col1.metric("Buyurtmalar", stats["orders"])
        col2.metric("Daromad", f"${stats['revenue']:,.0f}")

        st.divider()
        st.subheader("📈 Kategoriya daromadi")
        df = load_category_chart()
        if not df.empty:
            fig = px.bar(df, x="category", y="revenue", color="category",
                         labels={"revenue": "Daromad ($)", "category": "Kategoriya"})
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)

        st.divider()
        st.subheader("💡 Namuna so'rovlar")
        for q in SAMPLE_QUERIES:
            if st.button(q, use_container_width=True, key=f"sample_{q[:20]}"):
                st.session_state.pending_query = q
                st.rerun()


def render_ticket_form() -> None:
    st.divider()
    with st.expander("🎫 Support Ticket", expanded=st.session_state.show_ticket_form):
        last_user_msg = next(
            (m["content"] for m in reversed(st.session_state.messages) if m["role"] == "user"),
            "",
        )
        title = st.text_input("Muammo sarlavhasi", value=f"Support: {last_user_msg[:60]}")
        body = st.text_area(
            "Tavsif",
            value=f"Foydalanuvchi savoli: {last_user_msg}\n\nQo'shimcha ma'lumot: ",
            height=120,
        )
        if st.button("GitHub Issue yaratish", type="primary"):
            with st.spinner("Ticket yaratilmoqda..."):
                try:
                    url = create_github_issue(title, body)
                    log("TICKET", f"GitHub issue created: {url}")
                    st.success(f"Ticket yaratildi: [Issue ko'rish]({url})")
                    st.session_state.show_ticket_form = False
                except Exception as e:
                    st.error(f"Xato: {e}")


def is_support_request(text: str) -> bool:
    return any(trigger in text.lower() for trigger in SUPPORT_TRIGGERS)


def main() -> None:
    init_session_state()
    render_sidebar()

    st.title("💬 Data Insights — Chat with your data")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if st.session_state.pending_query:
        user_input = st.session_state.pending_query
        st.session_state.pending_query = None
    else:
        user_input = st.chat_input("Savolingizni yozing...")

    if user_input:
        log("USER", user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        if is_support_request(user_input):
            st.session_state.show_ticket_form = True

        with st.chat_message("assistant"):
            with st.spinner("Tahlil qilinmoqda..."):
                response = run_agent(st.session_state.messages)
        
        if "support ticket" in response.lower() or "create_github_issue" in response.lower():
            st.session_state.show_ticket_form = True

        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()

    render_ticket_form()

    if not st.session_state.show_ticket_form:
        if st.button("🎫 Support Ticket ochish", use_container_width=False):
            st.session_state.show_ticket_form = True
            st.rerun()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Copy .env and verify env vars set**

```bash
cp .env.example .env
# .env ga uchta qiymatni to'ldiring:
# ANTHROPIC_API_KEY=...
# GITHUB_TOKEN=...
# GITHUB_REPO=owner/repo
```

- [ ] **Step 3: Run the app and verify manually**

```bash
streamlit run app.py
```

Verify in browser:
- Sidebar shows stats (4 metrics, bar chart, 5 sample query buttons)
- Chat input is visible
- Clicking a sample query sends it to the agent
- Agent responds with data (not raw SQL, not full table dump)
- Console shows log lines like `[USER]`, `[TOOL]`, `[DB]`, `[AGENT]`
- "Support Ticket ochish" button opens the form
- Submitting the form creates a GitHub issue and shows the URL

- [ ] **Step 4: Commit**

```bash
git add app.py
git commit -m "feat: Streamlit UI with chat, sidebar dashboard, and support ticket form"
```

---

## Task 7: README and HF Spaces Config

**Files:**
- Create: `README.md`

**Interfaces:**
- Produces: nothing consumed by code — documentation only

- [ ] **Step 1: Create README.md**

```markdown
---
title: Data Insights App
emoji: 🛒
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: "1.40.0"
app_file: app.py
pinned: false
---

# 🛒 Data Insights App — Chat with your E-commerce Data

A Streamlit chatbot powered by Claude that lets you query an e-commerce database
using plain language. No SQL knowledge required.

## Features

- **Natural language queries** — Ask anything about orders, products, customers
- **Business dashboard** — Live stats and category revenue chart in the sidebar
- **Safety layer** — DELETE, DROP, UPDATE and other destructive operations are blocked
- **Support tickets** — Open a GitHub Issue directly from the chat
- **Console logging** — Every tool call and DB query is logged to the terminal

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
ANTHROPIC_API_KEY=your_anthropic_api_key
GITHUB_TOKEN=your_github_personal_access_token
GITHUB_REPO=owner/repository-name
```

- Get an Anthropic API key at https://console.anthropic.com
- Get a GitHub token at GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) — grant `repo` scope

### 4. Seed the database

```bash
python scripts/seed_data.py
```

### 5. Run the app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

## Running Tests

```bash
pytest tests/ -v
```

## Workflow Example

> Screenshots go here — add after real usage

1. App opens with sidebar showing dataset stats and category chart
2. User clicks a sample query or types a custom question
3. Agent calls `get_schema()` then `query_database()` and returns formatted results
4. User opens a support ticket when needed — a GitHub Issue is created automatically

## Deploying to HF Spaces

1. Push this repo to a Hugging Face Space (set SDK to Streamlit)
2. Add secrets in Space settings:
   - `ANTHROPIC_API_KEY`
   - `GITHUB_TOKEN`
   - `GITHUB_REPO`
3. The app starts automatically — no build step needed

## Architecture

```
User (browser) → Streamlit (app.py) → Agent (agent.py) → Claude API
                                                        ↓
                                              Tools (tools.py)
                                         ┌────────┬────────┬──────────┐
                                      get_schema  query_db  github_issue
                                                     ↓
                                              safety.py (validator)
                                                     ↓
                                              SQLite (ecommerce.db)
```
```

- [ ] **Step 2: Add real screenshots**

After the app is working:
- Take a screenshot of the sidebar with stats and chart
- Take a screenshot of the chat with a sample query and agent response
- Take a screenshot of the support ticket form
- Save to `docs/screenshots/` and add `![screenshot](docs/screenshots/xxx.png)` lines to README

- [ ] **Step 3: Run full test suite one final time**

```bash
pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: README with HF Spaces metadata, setup guide, and architecture"
```

---

## Self-Review Against Spec

| Spec Requirement | Covered by Task |
|-----------------|----------------|
| Agent assists users in getting DB info | Task 5 (`run_agent`) |
| Datasource not sent fully to LLM | Task 4 (`query_database` max 100 rows, `get_schema` only schema) |
| UI shows business info (stats, charts) | Task 6 (sidebar metrics + Plotly bar chart) |
| UI has sample queries | Task 6 (5 clickable buttons) |
| Agent prints logs to console | Task 5 (`log()`) + Task 4 (`dispatch_tool`) |
| Support ticket — explicit trigger | Task 6 (button + keyword detection) |
| Support ticket — implicit trigger | Task 5 (2 failed attempts) |
| Support ticket via GitHub Issues | Task 4 (`create_github_issue`) |
| Function calling is a must | Tasks 4+5 (3 tools with Anthropic schema) |
| At least 2 different tools | Task 4 (3 tools: get_schema, query_database, create_github_issue) |
| Python | All tasks |
| Streamlit UI | Task 6 |
| 500+ rows of data | Task 2 (1050+ rows) |
| Safety: blocks dangerous operations | Task 3 (2-layer: system prompt + code) |
| README with screenshots | Task 7 |
| HF Spaces bonus | Task 7 (YAML metadata in README) |
| .env not committed | Task 1 (.gitignore) |
