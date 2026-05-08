"""
Data ingestion service.
Parses CSV/Excel files with Pandas, auto-detects schema, then creates the
PostgreSQL table and bulk-inserts the data via MCP tools.
Accepts an optional `db_engine` to target a per-user database.
"""
import logging
import re
import pandas as pd
from io import BytesIO
from typing import Tuple

from mcp_tools.create_table import create_table
from mcp_tools.insert_data import insert_data

logger = logging.getLogger(__name__)

# Pandas dtype → PostgreSQL type mapping
DTYPE_MAP = {
    "int64": "bigint",
    "int32": "integer",
    "float64": "numeric",
    "float32": "numeric",
    "bool": "boolean",
    "object": "text",
    "datetime64[ns]": "timestamp",
    "datetime64[ns, UTC]": "timestamptz",
}


def _sanitise_column(name: str) -> str:
    """Lowercase column name, replace spaces/special chars with underscores."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    if name[0].isdigit():
        name = "col_" + name
    return name


def _sanitise_table_name(filename: str) -> str:
    """Derive a safe table name from the uploaded filename."""
    base = filename.rsplit(".", 1)[0]
    name = re.sub(r"[^a-z0-9_]", "_", base.strip().lower())
    if name[0].isdigit():
        name = "tbl_" + name
    return name[:60]  # PostgreSQL identifier limit is 63


def _infer_columns(df: pd.DataFrame) -> list[dict]:
    columns = []
    for col in df.columns:
        dtype_str = str(df[col].dtype)
        pg_type = DTYPE_MAP.get(dtype_str, "text")
        columns.append({
            "name": _sanitise_column(col),
            "type": pg_type,
            "nullable": True,
        })
    return columns


def ingest_file(file_bytes: bytes, filename: str, db_engine=None) -> Tuple[dict, str]:
    """
    Parse the uploaded file and load into PostgreSQL.
    Pass `db_engine` to target a specific (per-user) database.
    Returns (result_dict, table_name).
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    try:
        if ext == "csv":
            df = pd.read_csv(BytesIO(file_bytes))
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(BytesIO(file_bytes))
        else:
            return {"success": False, "error": f"Unsupported file type: {ext}"}, ""
    except Exception as e:
        return {"success": False, "error": f"Failed to parse file: {e}"}, ""

    # Sanitise column names
    df.columns = [_sanitise_column(c) for c in df.columns]

    table_name = _sanitise_table_name(filename)
    columns = _infer_columns(df)

    # Create table in the user's DB
    create_result = create_table(table_name, columns, if_not_exists=True, db_engine=db_engine)
    if not create_result["success"]:
        return create_result, table_name

    # Convert df to list of dicts, handle NaTs and NaNs
    rows = df.where(pd.notnull(df), None).to_dict(orient="records")
    insert_data(table_name, rows, db_engine=db_engine)

    preview = df.head(10).to_dict(orient="records")

    return {
        "success": True,
        "table_name": table_name,
        "row_count": len(df),
        "column_count": len(columns),
        "columns": columns,
        "preview": preview,
    }, table_name
