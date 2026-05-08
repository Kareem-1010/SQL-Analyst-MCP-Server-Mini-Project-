"""
Route: /api/analytics
Aggregated query statistics for the authenticated user's database.
  GET /api/analytics          — overall stats + recent trend
  GET /api/analytics/timeline — query count per day (last 30 days)
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from db.database import get_user_engine, get_user_session
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


@router.get("")
def get_analytics(current_user: dict = Depends(get_current_user)):
    """Return aggregated query stats for the dashboard."""
    db_name = current_user["db_name"]
    db_session = get_user_session(db_name)
    user_engine = get_user_engine(db_name)
    try:
        # Overall stats
        stats = db_session.execute(text("""
            SELECT
                COUNT(*)                                          AS total_queries,
                COUNT(*) FILTER (WHERE status = 'success')       AS successful,
                COUNT(*) FILTER (WHERE status = 'error')         AS failed,
                ROUND(AVG(execution_time_ms) FILTER (WHERE status = 'success')::numeric, 2)
                                                                  AS avg_exec_ms,
                ROUND(MAX(execution_time_ms)::numeric, 2)         AS max_exec_ms,
                ROUND(MIN(execution_time_ms) FILTER (WHERE execution_time_ms IS NOT NULL)::numeric, 2)
                                                                  AS min_exec_ms
            FROM query_history
        """)).mappings().first()

        # Top 5 most-queried tables (extract first table name from generated_sql)
        top_tables = db_session.execute(text("""
            SELECT
                LOWER(
                    (regexp_matches(generated_sql, 'FROM\\s+(\\w+)', 'i'))[1]
                ) AS table_name,
                COUNT(*) AS query_count
            FROM query_history
            WHERE generated_sql IS NOT NULL
              AND generated_sql ~* 'FROM\\s+\\w+'
            GROUP BY 1
            ORDER BY 2 DESC
            LIMIT 5
        """)).mappings().all()

        # Last 14 days query volume
        timeline = db_session.execute(text("""
            SELECT
                DATE(created_at) AS day,
                COUNT(*)         AS total,
                COUNT(*) FILTER (WHERE status = 'success') AS success,
                COUNT(*) FILTER (WHERE status = 'error')   AS error
            FROM query_history
            WHERE created_at >= NOW() - INTERVAL '14 days'
            GROUP BY 1
            ORDER BY 1
        """)).mappings().all()

        # Query type breakdown (SELECT vs DML)
        types = db_session.execute(text("""
            SELECT
                CASE
                    WHEN generated_sql ~* '^\\s*(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE)'
                    THEN 'DML'
                    ELSE 'SELECT'
                END AS query_type,
                COUNT(*) AS count
            FROM query_history
            WHERE generated_sql IS NOT NULL
            GROUP BY 1
        """)).mappings().all()

        # Table count in user's DB
        from mcp_tools.list_tables import list_tables
        tables_result = list_tables(db_engine=user_engine)
        table_count = len(tables_result["data"]["tables"]) if tables_result["success"] else 0

        success_rate = 0.0
        if stats and stats["total_queries"] and stats["total_queries"] > 0:
            success_rate = round(stats["successful"] / stats["total_queries"] * 100, 1)

        return {
            "total_queries": stats["total_queries"] if stats else 0,
            "successful": stats["successful"] if stats else 0,
            "failed": stats["failed"] if stats else 0,
            "success_rate": success_rate,
            "avg_exec_ms": float(stats["avg_exec_ms"] or 0) if stats else 0,
            "max_exec_ms": float(stats["max_exec_ms"] or 0) if stats else 0,
            "min_exec_ms": float(stats["min_exec_ms"] or 0) if stats else 0,
            "table_count": table_count,
            "top_tables": [
                {"table": r["table_name"], "count": r["query_count"]}
                for r in top_tables
            ],
            "timeline": [
                {
                    "day": str(r["day"]),
                    "total": r["total"],
                    "success": r["success"],
                    "error": r["error"],
                }
                for r in timeline
            ],
            "query_types": [
                {"type": r["query_type"], "count": r["count"]}
                for r in types
            ],
        }

    except Exception as e:
        logger.error(f"[analytics] Error: {e}")
        return {
            "total_queries": 0, "successful": 0, "failed": 0,
            "success_rate": 0, "avg_exec_ms": 0, "max_exec_ms": 0, "min_exec_ms": 0,
            "table_count": 0, "top_tables": [], "timeline": [], "query_types": [],
        }
    finally:
        db_session.close()
