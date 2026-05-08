"""
MCP Tool: explain_query
Runs EXPLAIN ANALYZE on a SQL query and returns the query plan.
"""
import logging
from datetime import datetime, timezone
from db.database import execute_raw
from mcp_tools.check_query_safety import check_query_safety

logger = logging.getLogger(__name__)
TOOL_NAME = "explain_query"


def explain_query(sql: str) -> dict:
    safety = check_query_safety(sql)
    if not safety["success"]:
        return {
            "success": False, "tool_name": TOOL_NAME, "error": safety["error"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    try:
        rows = execute_raw(f"EXPLAIN ANALYZE {sql}")
        plan = "\n".join([list(r.values())[0] for r in rows])
        logger.info(f"[{TOOL_NAME}] Generated EXPLAIN ANALYZE plan.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"plan": plan},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False, "tool_name": TOOL_NAME, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
