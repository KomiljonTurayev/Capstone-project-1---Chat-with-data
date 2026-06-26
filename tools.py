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
    for row in tables:
        table_name = row[0]
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
        print(f"[{timestamp}] [DB]      {len(rows)} rows returned")
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
            print(f"[{timestamp}] [TOOL]    get_schema()")
            return get_schema()
        elif name == "query_database":
            sql = inputs["sql"]
            print(f"[{timestamp}] [TOOL]    query_database({sql[:60]}...)")
            return query_database(sql)
        elif name == "create_github_issue":
            print(f"[{timestamp}] [TOOL]    create_github_issue({inputs.get('title', '')[:40]})")
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
