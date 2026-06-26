import os
from datetime import datetime

import anthropic
from dotenv import load_dotenv

from tools import TOOL_DEFINITIONS, dispatch_tool

load_dotenv()

_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
client = anthropic.Anthropic(api_key=_api_key) if _api_key else None

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
6. When the user asks for support or mentions a problem you cannot solve, call create_github_issue.
7. Keep answers data-focused and concise.
8. Always respond in English.
"""

SUPPORT_TRIGGERS = {"support", "ticket", "help", "human", "agent", "contact"}


def log(tag: str, message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{tag:<8}]  {message}")


def run_agent(messages: list) -> str:
    if not client:
        return "ANTHROPIC_API_KEY is not set. Please configure it in your .env file or HF Spaces secrets."

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
