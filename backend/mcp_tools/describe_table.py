"""
MCP Tool: describe_table
Returns column names, types, nullability and constraints for a given table.
Accepts an optional `db_engine` to query a per-user database.
"""
import logging
from datetime import datetime, timezone
from db.database import execute_raw

logger = logging.getLogger(__name__)

TOOL_NAME = "describe_table"


def describe_table(table_name: str, db_engine=None) -> dict:
    try:
        # Sanitise table name
        if not table_name.replace("_", "").isalnum():
            return {
                "success": False,
                "tool_name": TOOL_NAME,
                "error": "Invalid table name.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        columns = execute_raw(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.character_maximum_length,
                tc.constraint_type
            FROM information_schema.columns c
            LEFT JOIN information_schema.key_column_usage kcu
                ON c.table_name = kcu.table_name
               AND c.column_name = kcu.column_name
               AND c.table_schema = kcu.table_schema
            LEFT JOIN information_schema.table_constraints tc
                ON kcu.constraint_name = tc.constraint_name
               AND kcu.table_schema = tc.table_schema
            WHERE c.table_schema = 'public'
              AND c.table_name = :table_name
            ORDER BY c.ordinal_position
            """,
            {"table_name": table_name},
            db_engine=db_engine,
        )

        row_count = execute_raw(
            f"SELECT COUNT(*) AS cnt FROM {table_name}",  # nosec – name is sanitised
            db_engine=db_engine,
        )
        count = row_count[0]["cnt"] if row_count else 0

        logger.info(f"[{TOOL_NAME}] Described table '{table_name}' — {len(columns)} columns.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {
                "table_name": table_name,
                "columns": columns,
                "row_count": count,
            },
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
