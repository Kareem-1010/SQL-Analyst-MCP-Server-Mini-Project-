"""
MCP Tool: check_query_safety
Validates a SQL string for dangerous operations before execution.
Rules:
  - No DROP / TRUNCATE statements
  - No DELETE without a WHERE clause
  - No EXEC / EXECUTE statements
  - No stacked statements (semicolon mid-query)
"""
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

TOOL_NAME = "check_query_safety"

_FORBIDDEN_PATTERNS = [
    (r"\bDROP\b", "DROP statements are not allowed."),
    (r"\bTRUNCATE\b", "TRUNCATE statements are not allowed."),
    (r"\bEXEC(UTE)?\b", "EXEC/EXECUTE statements are not allowed."),
    (r"\bALTER\s+SYSTEM\b", "ALTER SYSTEM is not allowed."),
    (r"\bPG_SLEEP\b", "pg_sleep is not allowed."),
    (r"\bCOPY\b", "COPY statements are not allowed."),
]


def check_query_safety(sql: str) -> dict:
    upper = sql.strip().upper()

    # Stacked statements guard
    statements = [s.strip() for s in sql.strip().split(";") if s.strip()]
    if len(statements) > 1:
        return _fail("Multiple statements (semicolons) are not allowed.")

    for pattern, message in _FORBIDDEN_PATTERNS:
        if re.search(pattern, upper):
            logger.warning(f"[{TOOL_NAME}] Blocked: {message} — Query: {sql[:100]}")
            return _fail(message)

    # DELETE without WHERE
    if re.search(r"\bDELETE\b", upper) and not re.search(r"\bWHERE\b", upper):
        msg = "DELETE without WHERE clause is not allowed."
        logger.warning(f"[{TOOL_NAME}] Blocked: {msg}")
        return _fail(msg)

    # UPDATE without WHERE
    if re.search(r"\bUPDATE\b", upper) and not re.search(r"\bWHERE\b", upper):
        msg = "UPDATE without WHERE clause is not allowed."
        logger.warning(f"[{TOOL_NAME}] Blocked: {msg}")
        return _fail(msg)

    logger.info(f"[{TOOL_NAME}] Query passed safety check.")
    return {
        "success": True,
        "tool_name": TOOL_NAME,
        "data": {"safe": True, "message": "Query passed all safety checks."},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _fail(reason: str) -> dict:
    return {
        "success": False,
        "tool_name": TOOL_NAME,
        "error": reason,
        "data": {"safe": False},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
