"""
MCP Tool: list_tables
Returns all user-created table names in the connected PostgreSQL database.
Accepts an optional `db_engine` to query a per-user database.
"""
import logging
from datetime import datetime, timezone
from db.database import execute_raw

logger = logging.getLogger(__name__)

TOOL_NAME = "list_tables"


def list_tables(db_engine=None) -> dict:
    try:
        rows = execute_raw(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
              AND table_name != 'query_history'
            ORDER BY table_name
            """,
            db_engine=db_engine,
        )
        tables = [r["table_name"] for r in rows]
        logger.info(f"[{TOOL_NAME}] Found {len(tables)} tables.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"tables": tables, "count": len(tables)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False,
            "tool_name": TOOL_NAME,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
