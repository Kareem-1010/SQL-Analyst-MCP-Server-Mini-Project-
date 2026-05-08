"""
MCP Tool: update_data
Executes an UPDATE statement — always requires a WHERE clause (enforced by check_query_safety).
"""
import logging
from datetime import datetime, timezone
from mcp_tools.execute_sql_query import execute_sql_query

logger = logging.getLogger(__name__)
TOOL_NAME = "update_data"


def update_data(sql: str) -> dict:
    """sql must be a full UPDATE ... SET ... WHERE ... statement."""
    result = execute_sql_query(sql)
    result["tool_name"] = TOOL_NAME
    return result
