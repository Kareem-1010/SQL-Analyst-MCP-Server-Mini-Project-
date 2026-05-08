"""
MCP Tool: insert_data
Bulk inserts rows into a table using parameterised SQL.
Accepts an optional `db_engine` to insert into a per-user database.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy import text
from db.database import engine as central_engine

logger = logging.getLogger(__name__)
TOOL_NAME = "insert_data"


def insert_data(table_name: str, rows: list[dict], db_engine=None) -> dict:
    """
    rows: list of dicts where keys are column names.
    """
    if not rows:
        return {"success": True, "tool_name": TOOL_NAME, "data": {"inserted": 0},
                "timestamp": datetime.now(timezone.utc).isoformat()}
    try:
        target_engine = db_engine or central_engine
        columns = list(rows[0].keys())
        placeholders = ", ".join([f":{c}" for c in columns])
        col_list = ", ".join(columns)
        sql = f"INSERT INTO {table_name} ({col_list}) VALUES ({placeholders})"

        with target_engine.begin() as conn:
            conn.execute(text(sql), rows)

        logger.info(f"[{TOOL_NAME}] Inserted {len(rows)} rows into '{table_name}'.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"table_name": table_name, "inserted": len(rows)},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False, "tool_name": TOOL_NAME, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
