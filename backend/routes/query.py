"""
Route: /api/query
Full AI Workflow (scoped to the authenticated user's database):
  1. Rate-limit check (10 req/min per user)
  2. NL → SQL (Groq, multi-turn aware)
  3. check_query_safety
  4. execute_sql_query  (user's DB)
  5. explain_sql_in_plain_english (Groq)
  6. optimize_query suggestion (Groq)
  7. [optional] AI Insights (Groq)
  8. Save to query_history (user's DB)

POST /api/query         — full AI query flow
POST /api/query/stream  — SSE streaming variant
POST /api/query/insights — generate insights for existing result
POST /api/query/suggest  — suggest questions for a given table
"""
import time
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text

from db.database import get_user_engine, get_user_session
from mcp_tools.list_tables import list_tables
from mcp_tools.describe_table import describe_table
from mcp_tools.natural_language_to_sql import natural_language_to_sql
from mcp_tools.check_query_safety import check_query_safety
from mcp_tools.execute_sql_query import execute_sql_query
from mcp_tools.explain_sql_in_plain_english import explain_sql_in_plain_english
from mcp_tools.optimize_query import optimize_query
from auth.dependencies import get_current_user
from services.rate_limiter import check_rate_limit
from services.groq_service import (
    groq_complete_multi, groq_insights, groq_suggest_queries, groq_stream
)

router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


class ConversationMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str
    table_name: Optional[str] = None
    conversation_history: list[ConversationMessage] = []
    include_insights: bool = False


class InsightsRequest(BaseModel):
    sql: str
    rows: list[dict]
    columns: list[str]
    row_count: int


class SuggestRequest(BaseModel):
    table_name: str


def _build_schema_context(table_name: str | None, db_engine) -> str:
    """Build a schema context string for the Groq prompt using the user's DB."""
    if table_name:
        desc = describe_table(table_name, db_engine=db_engine)
        if desc["success"]:
            cols = desc["data"]["columns"]
            col_str = ", ".join([f"{c['column_name']} ({c['data_type']})" for c in cols])
            return f"Table: {table_name}\nColumns: {col_str}"

    # Get all tables from user's DB
    tables_result = list_tables(db_engine=db_engine)
    if not tables_result["success"] or not tables_result["data"]["tables"]:
        return "No tables available."

    context_parts = []
    for t in tables_result["data"]["tables"][:10]:  # limit to 10 tables
        desc = describe_table(t, db_engine=db_engine)
        if desc["success"]:
            cols = desc["data"]["columns"]
            col_str = ", ".join([f"{c['column_name']} ({c['data_type']})" for c in cols])
            context_parts.append(f"Table: {t}\nColumns: {col_str}")
    return "\n\n".join(context_parts)


def _save_history(db_session, user_query, generated_sql, result_summary, row_count,
                  execution_time_ms, status, error_message=None):
    """Save a query history entry to the user's own query_history table."""
    try:
        from datetime import datetime, timezone
        db_session.execute(
            text("""
                INSERT INTO query_history
                    (user_query, generated_sql, result_summary, row_count,
                     execution_time_ms, status, error_message, created_at)
                VALUES
                    (:user_query, :generated_sql, :result_summary, :row_count,
                     :execution_time_ms, :status, :error_message, :created_at)
            """),
            {
                "user_query": user_query,
                "generated_sql": generated_sql,
                "result_summary": result_summary,
                "row_count": row_count,
                "execution_time_ms": execution_time_ms,
                "status": status,
                "error_message": error_message,
                "created_at": datetime.now(timezone.utc),
            }
        )
        db_session.commit()
    except Exception as e:
        logger.error(f"[query] Failed to save history: {e}")
        db_session.rollback()


def _build_nl_prompt_with_context(question: str, schema_context: str,
                                   conversation_history: list[ConversationMessage]) -> list[dict]:
    """Build multi-turn messages for NL→SQL with conversation context."""
    system = (
        "You are an expert SQL analyst. Convert natural language questions to precise SQL queries. "
        "Return ONLY the SQL query, no explanation, no markdown code fences. "
        f"Available schema:\n{schema_context}"
    )
    messages = []
    # Add last 6 turns of history for context
    for msg in conversation_history[-6:]:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": f"Generate SQL for: {question}"})
    return messages, system


@router.post("/query")
def run_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    # Rate limit check
    if not check_rate_limit(current_user["username"]):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 10 queries per minute.")

    start = time.perf_counter()
    db_name = current_user["db_name"]
    user_engine = get_user_engine(db_name)
    db_session = get_user_session(db_name)

    user_query = request.question
    generated_sql = None
    result_summary = None
    row_count = None
    exec_time = None

    try:
        schema_context = _build_schema_context(request.table_name, user_engine)

        # Step 1: NL → SQL (with multi-turn context if available)
        if request.conversation_history:
            messages, system = _build_nl_prompt_with_context(
                request.question, schema_context, request.conversation_history
            )
            raw_sql = groq_complete_multi(messages, system_prompt=system, max_tokens=512)
            # Clean the SQL response
            raw_sql = raw_sql.strip()
            if raw_sql.startswith("```"):
                raw_sql = raw_sql.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            sql = raw_sql
            generated_sql = sql
        else:
            nl_result = natural_language_to_sql(request.question, schema_context)
            if not nl_result["success"]:
                raise HTTPException(status_code=500, detail=f"SQL generation failed: {nl_result['error']}")
            sql = nl_result["data"]["sql"]
            generated_sql = sql

        # Step 2: Safety check
        safety = check_query_safety(sql)
        if not safety["success"]:
            raise HTTPException(status_code=400, detail=f"Query blocked: {safety['error']}")

        # Step 3: Execute against user's DB
        exec_result = execute_sql_query(sql, db_engine=user_engine)
        if not exec_result["success"]:
            raise HTTPException(status_code=500, detail=f"Execution error: {exec_result['error']}")

        rows = exec_result["data"]["rows"]
        row_count = exec_result["data"]["row_count"]
        exec_time = exec_result["data"]["execution_time_ms"]
        query_type = exec_result["data"].get("type", "select")
        rows_affected = exec_result["data"].get("rows_affected", row_count)
        columns = exec_result["data"]["columns"]

        # Step 4: Plain English explanation
        if query_type == "dml":
            result_summary = f"{rows_affected} row(s) affected"
        else:
            result_summary = f"{row_count} row(s) returned"

        explain_result = explain_sql_in_plain_english(sql, result_summary)
        explanation = explain_result["data"]["explanation"] if explain_result["success"] else ""

        # Step 5: Optimisation suggestion (non-blocking, skip for DML)
        optimization = ""
        if query_type == "select":
            opt_result = optimize_query(sql, schema_context)
            optimization = opt_result["data"]["optimisation_suggestion"] if opt_result["success"] else ""

        # Step 6: AI Insights (optional)
        insights = []
        if request.include_insights and rows and len(rows) > 0:
            insights = groq_insights(sql, rows, columns, row_count)

        # Persist history in user's DB
        _save_history(db_session, user_query, generated_sql, result_summary, row_count,
                      exec_time, "success")

        total_elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.info(f"[query] User '{current_user['username']}' — Completed in {total_elapsed}ms.")

        return {
            "success": True,
            "question": request.question,
            "sql": sql,
            "rows": rows,
            "row_count": row_count,
            "rows_affected": rows_affected,
            "columns": columns,
            "execution_time_ms": exec_time,
            "truncated": exec_result["data"]["truncated"],
            "explanation": explanation,
            "optimization_suggestion": optimization,
            "query_type": query_type,
            "insights": insights,
            "total_elapsed_ms": total_elapsed,
        }

    except HTTPException as e:
        _save_history(db_session, user_query, generated_sql, None, None, None, "error",
                      str(e.detail))
        raise
    except Exception as e:
        _save_history(db_session, user_query, generated_sql, None, None, None, "error", str(e))
        logger.error(f"[query] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()


@router.post("/query/stream")
def stream_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    SSE streaming endpoint — generates SQL, executes it, then streams the explanation
    token-by-token from Groq.
    Yields Server-Sent Events in the format: data: <json>\n\n
    """
    if not check_rate_limit(current_user["username"]):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    db_name = current_user["db_name"]
    user_engine = get_user_engine(db_name)
    db_session = get_user_session(db_name)

    def _event_generator():
        generated_sql = None
        try:
            schema_context = _build_schema_context(request.table_name, user_engine)

            # NL → SQL
            nl_result = natural_language_to_sql(request.question, schema_context)
            if not nl_result["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': nl_result['error']})}\n\n"
                return
            sql = nl_result["data"]["sql"]
            generated_sql = sql

            # Emit the SQL immediately
            yield f"data: {json.dumps({'type': 'sql', 'sql': sql})}\n\n"

            # Safety check
            safety = check_query_safety(sql)
            if not safety["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': safety['error']})}\n\n"
                _save_history(db_session, request.question, sql, None, None, None, "error", safety["error"])
                return

            # Execute
            exec_result = execute_sql_query(sql, db_engine=user_engine)
            if not exec_result["success"]:
                yield f"data: {json.dumps({'type': 'error', 'message': exec_result['error']})}\n\n"
                _save_history(db_session, request.question, sql, None, None, None, "error", exec_result["error"])
                return

            rows = exec_result["data"]["rows"]
            row_count = exec_result["data"]["row_count"]
            exec_time = exec_result["data"]["execution_time_ms"]
            query_type = exec_result["data"].get("type", "select")
            rows_affected = exec_result["data"].get("rows_affected", row_count)
            columns = exec_result["data"]["columns"]
            result_summary = f"{rows_affected} row(s) affected" if query_type == "dml" else f"{row_count} row(s) returned"

            # Emit result metadata
            yield f"data: {json.dumps({'type': 'result', 'rows': rows, 'columns': columns, 'row_count': row_count, 'rows_affected': rows_affected, 'execution_time_ms': exec_time, 'query_type': query_type})}\n\n"

            # Stream the explanation
            explain_prompt = (
                f"In 2-3 sentences, explain what this SQL query does and what the results mean:\n"
                f"SQL: {sql}\nResults: {result_summary}"
            )
            full_explanation = ""
            for chunk in groq_stream(
                explain_prompt,
                system_prompt="You are a helpful data analyst. Be concise and clear."
            ):
                full_explanation += chunk
                yield f"data: {json.dumps({'type': 'explanation_chunk', 'chunk': chunk})}\n\n"

            # Optimization tip (only for SELECT)
            optimization = ""
            if query_type == "select":
                opt_result = optimize_query(sql, schema_context)
                optimization = opt_result["data"]["optimisation_suggestion"] if opt_result["success"] else ""

            _save_history(db_session, request.question, sql, result_summary, row_count, exec_time, "success")
            yield f"data: {json.dumps({'type': 'done', 'explanation': full_explanation, 'optimization': optimization})}\n\n"

        except Exception as e:
            logger.error(f"[query/stream] Error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        finally:
            db_session.close()

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/query/insights")
def get_query_insights(
    request: InsightsRequest,
    current_user: dict = Depends(get_current_user),
):
    """Generate AI insights for an already-executed query result."""
    if not check_rate_limit(current_user["username"]):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")
    insights = groq_insights(request.sql, request.rows, request.columns, request.row_count)
    return {"insights": insights}


@router.post("/query/suggest")
def suggest_queries(
    request: SuggestRequest,
    current_user: dict = Depends(get_current_user),
):
    """Suggest 5 natural language questions for a given table."""
    db_name = current_user["db_name"]
    user_engine = get_user_engine(db_name)
    schema_context = _build_schema_context(request.table_name, user_engine)
    suggestions = groq_suggest_queries(schema_context, request.table_name)
    return {"suggestions": suggestions}

import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from db.database import get_user_engine, get_user_session
from mcp_tools.list_tables import list_tables
from mcp_tools.describe_table import describe_table
from mcp_tools.natural_language_to_sql import natural_language_to_sql
from mcp_tools.check_query_safety import check_query_safety
from mcp_tools.execute_sql_query import execute_sql_query
from mcp_tools.explain_sql_in_plain_english import explain_sql_in_plain_english
from mcp_tools.optimize_query import optimize_query
from auth.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["query"])
logger = logging.getLogger(__name__)


class QueryRequest(BaseModel):
    question: str
    table_name: str | None = None


def _build_schema_context(table_name: str | None, db_engine) -> str:
    """Build a schema context string for the Groq prompt using the user's DB."""
    if table_name:
        desc = describe_table(table_name, db_engine=db_engine)
        if desc["success"]:
            cols = desc["data"]["columns"]
            col_str = ", ".join([f"{c['column_name']} ({c['data_type']})" for c in cols])
            return f"Table: {table_name}\nColumns: {col_str}"

    # Get all tables from user's DB
    tables_result = list_tables(db_engine=db_engine)
    if not tables_result["success"] or not tables_result["data"]["tables"]:
        return "No tables available."

    context_parts = []
    for t in tables_result["data"]["tables"][:10]:  # limit to 10 tables
        desc = describe_table(t, db_engine=db_engine)
        if desc["success"]:
            cols = desc["data"]["columns"]
            col_str = ", ".join([f"{c['column_name']} ({c['data_type']})" for c in cols])
            context_parts.append(f"Table: {t}\nColumns: {col_str}")
    return "\n\n".join(context_parts)


def _save_history(db_session, user_query, generated_sql, result_summary, row_count,
                  execution_time_ms, status, error_message=None):
    """Save a query history entry to the user's own query_history table."""
    try:
        from datetime import datetime, timezone
        db_session.execute(
            text("""
                INSERT INTO query_history
                    (user_query, generated_sql, result_summary, row_count,
                     execution_time_ms, status, error_message, created_at)
                VALUES
                    (:user_query, :generated_sql, :result_summary, :row_count,
                     :execution_time_ms, :status, :error_message, :created_at)
            """),
            {
                "user_query": user_query,
                "generated_sql": generated_sql,
                "result_summary": result_summary,
                "row_count": row_count,
                "execution_time_ms": execution_time_ms,
                "status": status,
                "error_message": error_message,
                "created_at": datetime.now(timezone.utc),
            }
        )
        db_session.commit()
    except Exception as e:
        logger.error(f"[query] Failed to save history: {e}")
        db_session.rollback()


@router.post("/query")
def run_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    start = time.perf_counter()
    db_name = current_user["db_name"]
    user_engine = get_user_engine(db_name)
    db_session = get_user_session(db_name)

    user_query = request.question
    generated_sql = None
    result_summary = None
    row_count = None
    exec_time = None

    try:
        schema_context = _build_schema_context(request.table_name, user_engine)

        # Step 1: NL → SQL
        nl_result = natural_language_to_sql(request.question, schema_context)
        if not nl_result["success"]:
            raise HTTPException(status_code=500, detail=f"SQL generation failed: {nl_result['error']}")
        sql = nl_result["data"]["sql"]
        generated_sql = sql

        # Step 2: Safety check
        safety = check_query_safety(sql)
        if not safety["success"]:
            raise HTTPException(status_code=400, detail=f"Query blocked: {safety['error']}")

        # Step 3: Execute against user's DB
        exec_result = execute_sql_query(sql, db_engine=user_engine)
        if not exec_result["success"]:
            raise HTTPException(status_code=500, detail=f"Execution error: {exec_result['error']}")

        rows = exec_result["data"]["rows"]
        row_count = exec_result["data"]["row_count"]
        exec_time = exec_result["data"]["execution_time_ms"]
        query_type = exec_result["data"].get("type", "select")
        rows_affected = exec_result["data"].get("rows_affected", row_count)

        # Step 4: Plain English explanation
        if query_type == "dml":
            result_summary = f"{rows_affected} row(s) affected"
        else:
            result_summary = f"{row_count} row(s) returned"

        explain_result = explain_sql_in_plain_english(sql, result_summary)
        explanation = explain_result["data"]["explanation"] if explain_result["success"] else ""

        # Step 5: Optimisation suggestion (non-blocking, skip for DML)
        optimization = ""
        if query_type == "select":
            opt_result = optimize_query(sql, schema_context)
            optimization = opt_result["data"]["optimisation_suggestion"] if opt_result["success"] else ""

        # Persist history in user's DB
        _save_history(db_session, user_query, generated_sql, result_summary, row_count,
                      exec_time, "success")

        total_elapsed = round((time.perf_counter() - start) * 1000, 2)
        logger.info(f"[query] User '{current_user['username']}' — Completed in {total_elapsed}ms.")

        return {
            "success": True,
            "question": request.question,
            "sql": sql,
            "rows": rows,
            "row_count": row_count,
            "rows_affected": rows_affected,
            "columns": exec_result["data"]["columns"],
            "execution_time_ms": exec_time,
            "truncated": exec_result["data"]["truncated"],
            "explanation": explanation,
            "optimization_suggestion": optimization,
            "query_type": query_type,
        }

    except HTTPException as e:
        _save_history(db_session, user_query, generated_sql, None, None, None, "error",
                      str(e.detail))
        raise
    except Exception as e:
        _save_history(db_session, user_query, generated_sql, None, None, None, "error", str(e))
        logger.error(f"[query] Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_session.close()
