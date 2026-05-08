"""
MCP Tool: optimize_query
Uses Groq LLM to suggest optimisations for a given SQL query.
"""
import logging
from datetime import datetime, timezone
from services.groq_service import groq_complete

logger = logging.getLogger(__name__)
TOOL_NAME = "optimize_query"


def optimize_query(sql: str, schema_context: str = "") -> dict:
    try:
        prompt = f"""You are a PostgreSQL query optimisation expert.
Analyse the following SQL query and suggest specific optimisations.
Focus on: indexes, query structure, joins, aggregations, and performance.

Schema context: {schema_context or 'Not provided'}

SQL Query:
{sql}

Provide:
1. Potential issues
2. Suggested optimisations
3. Optimised query (if applicable)
Keep response concise and actionable."""

        suggestion = groq_complete(prompt)
        logger.info(f"[{TOOL_NAME}] Generated optimisation suggestion.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"original_sql": sql, "optimisation_suggestion": suggestion},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False, "tool_name": TOOL_NAME, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
