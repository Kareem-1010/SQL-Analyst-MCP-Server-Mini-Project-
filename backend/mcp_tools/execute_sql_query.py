"""
MCP Tool: execute_sql_query
Executes a SQL query ONLY after it passes check_query_safety.
Returns rows as list of dicts, capped at MAX_RESULT_ROWS.
Accepts an optional `db_engine` to run against a per-user database.
"""
import time
import logging
import os
from datetime import datetime, timezone
from db.database import execute_raw
from mcp_tools.check_query_safety import check_query_safety

logger = logging.getLogger(__name__)

TOOL_NAME = "execute_sql_query"
MAX_ROWS = int(os.getenv("MAX_RESULT_ROWS", "1000"))


def execute_sql_query(sql: str, params: dict = None, db_engine=None) -> dict:
    # Safety gate
    safety = check_query_safety(sql)
    if not safety["success"]:
        return {
            "success": False,
            "tool_name": TOOL_NAME,
            "error": f"Safety check failed: {safety['error']}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    start = time.perf_counter()
    try:
        raw = execute_raw(sql, params or {}, db_engine=db_engine)
        elapsed = round((time.perf_counter() - start) * 1000, 2)

        # DML operations (INSERT/UPDATE/DELETE/DDL) return a rowcount dict
        if isinstance(raw, dict) and raw.get("dml"):
            rowcount = raw.get("rowcount", 0)
            logger.info(f"[{TOOL_NAME}] DML OK — {rowcount} rows affected in {elapsed}ms.")
            return {
                "success": True,
                "tool_name": TOOL_NAME,
                "data": {
                    "rows": [],
                    "row_count": rowcount,
                    "rows_affected": rowcount,
                    "execution_time_ms": elapsed,
                    "truncated": False,
                    "columns": [],
                    "type": "dml",
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        # SELECT operations return a list of row dicts
        rows = raw
        truncated = len(rows) >= MAX_ROWS
        rows = rows[:MAX_ROWS]

        logger.info(f"[{TOOL_NAME}] Query OK — {len(rows)} rows in {elapsed}ms.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": elapsed,
                "truncated": truncated,
                "columns": list(rows[0].keys()) if rows else [],
                "type": "select",
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.error(f"[{TOOL_NAME}] Error after {elapsed}ms: {e}")
        return {
            "success": False,
            "tool_name": TOOL_NAME,
            "error": str(e),
            "data": {"execution_time_ms": elapsed},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
