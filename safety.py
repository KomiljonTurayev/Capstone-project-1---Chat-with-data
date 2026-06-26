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
