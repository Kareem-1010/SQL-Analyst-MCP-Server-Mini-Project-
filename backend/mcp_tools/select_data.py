"""
MCP Tool: select_data
Constructs and executes a parameterised SELECT query.
"""
import logging
from datetime import datetime, timezone
from mcp_tools.execute_sql_query import execute_sql_query

logger = logging.getLogger(__name__)
TOOL_NAME = "select_data"


def select_data(
    table_name: str,
    columns: list[str] = None,
    where: str = None,
    order_by: str = None,
    limit: int = 100,
) -> dict:
    try:
        cols = ", ".join(columns) if columns else "*"
        sql = f"SELECT {cols} FROM {table_name}"
        if where:
            sql += f" WHERE {where}"
        if order_by:
            sql += f" ORDER BY {order_by}"
        sql += f" LIMIT {min(limit, 1000)}"

        result = execute_sql_query(sql)
        result["tool_name"] = TOOL_NAME
        return result
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False,
            "tool_name": TOOL_NAME,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
