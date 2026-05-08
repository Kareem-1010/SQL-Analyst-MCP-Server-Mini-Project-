"""
MCP Tool: create_table
Creates a new PostgreSQL table from a column specification dict.
Accepts an optional `db_engine` to create a table in a per-user database.
"""
import re
import logging
from datetime import datetime, timezone
from db.database import execute_raw

logger = logging.getLogger(__name__)
TOOL_NAME = "create_table"

ALLOWED_TYPES = {
    "text", "varchar", "integer", "bigint", "float", "numeric",
    "boolean", "date", "timestamp", "timestamptz", "jsonb", "serial",
}


def create_table(table_name: str, columns: list[dict], if_not_exists: bool = True, db_engine=None) -> dict:
    """
    columns: [{"name": "col1", "type": "text", "nullable": True, "primary_key": False}, ...]
    """
    try:
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", table_name):
            return _fail("Invalid table name.")

        col_defs = []
        for col in columns:
            col_name = col["name"]
            col_type = col.get("type", "text").lower()

            # Sanitise
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", col_name):
                return _fail(f"Invalid column name: {col_name}")
            base_type = col_type.split("(")[0].split(" ")[0]
            if base_type not in ALLOWED_TYPES:
                return _fail(f"Unsupported column type: {col_type}")

            nullable = "" if col.get("nullable", True) else " NOT NULL"
            pk = " PRIMARY KEY" if col.get("primary_key", False) else ""
            col_defs.append(f"{col_name} {col_type}{nullable}{pk}")

        exists_clause = "IF NOT EXISTS " if if_not_exists else ""
        ddl = f"CREATE TABLE {exists_clause}{table_name} ({', '.join(col_defs)})"

        execute_raw(ddl, db_engine=db_engine)
        logger.info(f"[{TOOL_NAME}] Created table '{table_name}'.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"table_name": table_name, "ddl": ddl},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return _fail(str(e))


def _fail(msg):
    return {
        "success": False, "tool_name": TOOL_NAME, "error": msg,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
