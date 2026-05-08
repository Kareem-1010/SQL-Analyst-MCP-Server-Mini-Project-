"""
Route: /api/mcp/{tool_name}
Generic MCP tool dispatcher — allows direct tool invocation via HTTP POST.
All tool calls that touch the database are scoped to the authenticated user's DB.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Any

from db.database import get_user_engine
from auth.dependencies import get_current_user
from mcp_tools.list_tables import list_tables
from mcp_tools.describe_table import describe_table
from mcp_tools.check_query_safety import check_query_safety
from mcp_tools.create_table import create_table
from mcp_tools.alter_table import alter_table
from mcp_tools.insert_data import insert_data
from mcp_tools.select_data import select_data
from mcp_tools.update_data import update_data
from mcp_tools.delete_data import delete_data
from mcp_tools.explain_query import explain_query
from mcp_tools.optimize_query import optimize_query
from mcp_tools.execute_sql_query import execute_sql_query
from mcp_tools.explain_sql_in_plain_english import explain_sql_in_plain_english
from mcp_tools.natural_language_to_sql import natural_language_to_sql

router = APIRouter(prefix="/api/mcp", tags=["mcp"])
logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    params: dict[str, Any] = {}


def _make_registry(user_engine):
    """Build a tool registry scoped to the given user engine."""
    return {
        "list_tables": lambda p: list_tables(db_engine=user_engine),
        "describe_table": lambda p: describe_table(p["table_name"], db_engine=user_engine),
        "check_query_safety": lambda p: check_query_safety(p["sql"]),
        "create_table": lambda p: create_table(
            p["table_name"], p["columns"], p.get("if_not_exists", True), db_engine=user_engine
        ),
        "alter_table": lambda p: alter_table(p["table_name"], p["add_columns"]),
        "insert_data": lambda p: insert_data(p["table_name"], p["rows"], db_engine=user_engine),
        "select_data": lambda p: select_data(
            p["table_name"], p.get("columns"), p.get("where"), p.get("order_by"), p.get("limit", 100)
        ),
        "update_data": lambda p: update_data(p["sql"]),
        "delete_data": lambda p: delete_data(p["sql"]),
        "explain_query": lambda p: explain_query(p["sql"]),
        "optimize_query": lambda p: optimize_query(p["sql"], p.get("schema_context", "")),
        "execute_sql_query": lambda p: execute_sql_query(
            p["sql"], p.get("params"), db_engine=user_engine
        ),
        "explain_sql_in_plain_english": lambda p: explain_sql_in_plain_english(
            p["sql"], p.get("results_summary", "")
        ),
        "natural_language_to_sql": lambda p: natural_language_to_sql(
            p["question"], p["schema_context"]
        ),
    }


@router.post("/{tool_name}")
def call_mcp_tool(
    tool_name: str,
    request: MCPRequest,
    current_user: dict = Depends(get_current_user),
):
    user_engine = get_user_engine(current_user["db_name"])
    registry = _make_registry(user_engine)

    if tool_name not in registry:
        raise HTTPException(status_code=404, detail=f"Unknown MCP tool: '{tool_name}'")
    try:
        result = registry[tool_name](request.params)
        return result
    except KeyError as e:
        raise HTTPException(status_code=422, detail=f"Missing required parameter: {e}")
    except Exception as e:
        logger.error(f"[mcp] Tool '{tool_name}' error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools")
def list_mcp_tools(current_user: dict = Depends(get_current_user)):
    user_engine = get_user_engine(current_user["db_name"])
    registry = _make_registry(user_engine)
    return {"tools": list(registry.keys()), "count": len(registry)}
