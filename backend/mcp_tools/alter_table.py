"""
MCP Tool: alter_table
Adds new columns to an existing table.
"""
import re
import logging
from datetime import datetime, timezone
from db.database import execute_raw
from mcp_tools.create_table import ALLOWED_TYPES

logger = logging.getLogger(__name__)
TOOL_NAME = "alter_table"


def alter_table(table_name: str, add_columns: list[dict]) -> dict:
    """
    add_columns: [{"name": "col", "type": "text", "nullable": True}, ...]
    """
    try:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            return _fail("Invalid table name.")

        results = []
        for col in add_columns:
            col_name = col["name"]
            col_type = col.get("type", "text").lower()

            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                return _fail(f"Invalid column name: {col_name}")
            base_type = col_type.split("(")[0]
            if base_type not in ALLOWED_TYPES:
                return _fail(f"Unsupported type: {col_type}")

            nullable = "" if col.get("nullable", True) else " NOT NULL DEFAULT ''"
            ddl = f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {col_name} {col_type}{nullable}"
            execute_raw(ddl)
            results.append({"column": col_name, "ddl": ddl})

        logger.info(f"[{TOOL_NAME}] Altered table '{table_name}' — {len(results)} columns added.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"table_name": table_name, "alterations": results},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return _fail(str(e))


def _fail(msg):
    return {"success": False, "tool_name": TOOL_NAME, "error": msg, "timestamp": datetime.now(timezone.utc).isoformat()}
