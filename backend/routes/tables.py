"""
Route: /api/tables
List all tables and describe a specific table in the authenticated user's database.
Also provides: per-table stats, and table deletion.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import text
from mcp_tools.list_tables import list_tables
from mcp_tools.describe_table import describe_table
from db.database import get_user_engine
from auth.dependencies import get_current_user
from services.schema_retrieval import rank_relevant_tables

router = APIRouter(prefix="/api", tags=["tables"])
logger = logging.getLogger(__name__)


@router.get("/tables")
def get_tables(current_user: dict = Depends(get_current_user)):
    user_engine = get_user_engine(current_user["db_name"])
    result = list_tables(db_engine=user_engine)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result["data"]


@router.get("/schema/recommendations")
def get_table_recommendations(
    question: str = Query(..., min_length=3, description="Natural language question to match against schema"),
    top_k: int = Query(5, ge=1, le=10),
    current_user: dict = Depends(get_current_user),
):
    """Rank the most relevant tables/columns for a natural-language question."""
    user_engine = get_user_engine(current_user["db_name"])
    result = rank_relevant_tables(question, user_engine, top_k=top_k)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.get("/tables/{table_name}")
def get_table_details(table_name: str, current_user: dict = Depends(get_current_user)):
    user_engine = get_user_engine(current_user["db_name"])
    result = describe_table(table_name, db_engine=user_engine)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result["data"]


@router.get("/tables/{table_name}/stats")
def get_table_stats(table_name: str, current_user: dict = Depends(get_current_user)):
    """Return row count, approximate size, and column count for a table."""
    user_engine = get_user_engine(current_user["db_name"])
    # Validate table exists first
    desc = describe_table(table_name, db_engine=user_engine)
    if not desc["success"]:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")
    col_count = len(desc["data"]["columns"])
    try:
        with user_engine.connect() as conn:
            row = conn.execute(
                text("SELECT COUNT(*) as cnt FROM :tbl"),
                {"tbl": table_name},
            ).mappings().first()
            # pg_total_relation_size only works for postgres
            size_row = conn.execute(
                text(
                    "SELECT pg_size_pretty(pg_total_relation_size(:tbl)) AS size"
                ),
                {"tbl": table_name},
            ).mappings().first()
            return {
                "table": table_name,
                "row_count": row["cnt"] if row else 0,
                "column_count": col_count,
                "size": size_row["size"] if size_row else "N/A",
            }
    except Exception:
        # Fallback: simple count with quoted identifier
        try:
            with user_engine.connect() as conn:
                cnt = conn.execute(
                    text(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
                ).scalar()
                return {
                    "table": table_name,
                    "row_count": cnt,
                    "column_count": col_count,
                    "size": "N/A",
                }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tables/{table_name}")
def delete_table(table_name: str, current_user: dict = Depends(get_current_user)):
    """Drop a table from the user's database."""
    user_engine = get_user_engine(current_user["db_name"])
    # Validate it exists
    desc = describe_table(table_name, db_engine=user_engine)
    if not desc["success"]:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found.")
    try:
        with user_engine.connect() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))
            conn.commit()
        logger.info(f"[tables] User '{current_user['username']}' dropped table '{table_name}'.")
        return {"success": True, "message": f"Table '{table_name}' dropped successfully."}
    except Exception as e:
        logger.error(f"[tables] Drop table error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
