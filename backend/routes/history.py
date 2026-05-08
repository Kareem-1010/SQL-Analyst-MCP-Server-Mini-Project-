"""
Route: /api/history
Returns the last 100 query history entries for the authenticated user (from their own DB).
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from db.database import get_user_engine, get_user_session
from auth.dependencies import get_current_user
import logging

router = APIRouter(prefix="/api", tags=["history"])
logger = logging.getLogger(__name__)


@router.get("/history")
def get_history(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    db_name = current_user["db_name"]
    db_session = get_user_session(db_name)
    try:
        result = db_session.execute(
            text("""
                SELECT id, user_query, generated_sql, result_summary,
                       row_count, execution_time_ms, status, error_message, created_at
                FROM query_history
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"limit": min(limit, 100)},
        )
        rows = result.mappings().all()
        return [
            {
                "id": r["id"],
                "user_query": r["user_query"],
                "generated_sql": r["generated_sql"],
                "result_summary": r["result_summary"],
                "row_count": r["row_count"],
                "execution_time_ms": r["execution_time_ms"],
                "status": r["status"],
                "error_message": r["error_message"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[history] Error for user '{current_user['username']}': {e}")
        return []
    finally:
        db_session.close()
