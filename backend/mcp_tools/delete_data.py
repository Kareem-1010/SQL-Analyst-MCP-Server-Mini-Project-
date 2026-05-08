"""
MCP Tool: delete_data
Executes a DELETE statement — WHERE clause is MANDATORY (enforced by check_query_safety).
"""
import logging
from datetime import datetime, timezone
from mcp_tools.execute_sql_query import execute_sql_query

logger = logging.getLogger(__name__)
TOOL_NAME = "delete_data"


def delete_data(sql: str) -> dict:
    """sql must include a WHERE clause, otherwise check_query_safety blocks it."""
    result = execute_sql_query(sql)
    result["tool_name"] = TOOL_NAME
    return result
