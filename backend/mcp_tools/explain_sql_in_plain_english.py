"""
MCP Tool: explain_sql_in_plain_english
Uses Groq LLM to explain what a SQL query does in simple, non-technical language.
"""
import logging
from datetime import datetime, timezone
from services.groq_service import groq_complete

logger = logging.getLogger(__name__)
TOOL_NAME = "explain_sql_in_plain_english"


def explain_sql_in_plain_english(sql: str, results_summary: str = "") -> dict:
    try:
        prompt = f"""You are a friendly data analyst explaining SQL to a non-technical user.
Explain what the following SQL query does in plain English (2-4 sentences max).
Be clear, friendly, and avoid technical jargon.

SQL Query:
{sql}

{f"Query returned: {results_summary}" if results_summary else ""}

Plain English explanation:"""

        explanation = groq_complete(prompt).strip()
        logger.info(f"[{TOOL_NAME}] Generated plain English explanation.")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"sql": sql, "explanation": explanation},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False, "tool_name": TOOL_NAME, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
