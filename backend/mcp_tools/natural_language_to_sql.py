"""
MCP Tool: natural_language_to_sql
Converts a user's natural language question into a PostgreSQL SELECT query using Groq.
"""
import logging
import re
from datetime import datetime, timezone
from services.groq_service import groq_complete

logger = logging.getLogger(__name__)
TOOL_NAME = "natural_language_to_sql"


def natural_language_to_sql(question: str, schema_context: str) -> dict:
    try:
        prompt = f"""You are an expert PostgreSQL query generator.
Convert the following natural language request into a valid PostgreSQL SQL query.

Database schema:
{schema_context}

Rules:
- Generate ONLY a single SQL statement
- Allowed: SELECT, INSERT, UPDATE, DELETE (with WHERE clause), CREATE TABLE
- NOT allowed: DROP, TRUNCATE, ALTER SYSTEM, DELETE without WHERE, UPDATE without WHERE
- Use proper PostgreSQL syntax with correct quoting and type casting
- For INSERT, use the exact column names from the schema
- Return ONLY the raw SQL — no markdown, no backticks, no explanation

Request: {question}

SQL:"""

        raw = groq_complete(prompt).strip()

        # Strip markdown fences if present
        sql = re.sub(r"```(?:sql)?", "", raw, flags=re.IGNORECASE).replace("```", "").strip()

        logger.info(f"[{TOOL_NAME}] Generated SQL for: '{question[:60]}...'")
        return {
            "success": True,
            "tool_name": TOOL_NAME,
            "data": {"question": question, "sql": sql},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"[{TOOL_NAME}] Error: {e}")
        return {
            "success": False, "tool_name": TOOL_NAME, "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
