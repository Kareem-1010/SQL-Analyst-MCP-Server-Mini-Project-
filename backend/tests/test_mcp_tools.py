"""
Unit tests for MCP tools.
Run: pytest tests/test_mcp_tools.py -v
These tests use mocking so no actual DB connection is needed.
"""
import pytest
from unittest.mock import patch, MagicMock


# --- check_query_safety ---

from mcp_tools.check_query_safety import check_query_safety


def test_safety_blocks_drop():
    result = check_query_safety("DROP TABLE users")
    assert result["success"] is False
    assert "DROP" in result["error"]


def test_safety_blocks_truncate():
    result = check_query_safety("TRUNCATE TABLE orders")
    assert result["success"] is False
    assert "TRUNCATE" in result["error"]


def test_safety_blocks_delete_without_where():
    result = check_query_safety("DELETE FROM customers")
    assert result["success"] is False
    assert "WHERE" in result["error"]


def test_safety_allows_delete_with_where():
    result = check_query_safety("DELETE FROM customers WHERE id = 1")
    assert result["success"] is True
    assert result["data"]["safe"] is True


def test_safety_blocks_update_without_where():
    result = check_query_safety("UPDATE products SET price = 0")
    assert result["success"] is False


def test_safety_allows_select():
    result = check_query_safety("SELECT * FROM users WHERE active = true")
    assert result["success"] is True
    assert result["data"]["safe"] is True


def test_safety_blocks_stacked_statements():
    result = check_query_safety("SELECT 1; DROP TABLE users")
    assert result["success"] is False


def test_safety_blocks_exec():
    result = check_query_safety("EXEC sp_something")
    assert result["success"] is False


# --- execute_sql_query (with mocked DB) ---

@patch("mcp_tools.execute_sql_query.execute_raw")
def test_execute_sql_query_success(mock_raw):
    mock_raw.return_value = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    from mcp_tools.execute_sql_query import execute_sql_query
    result = execute_sql_query("SELECT id, name FROM users")
    assert result["success"] is True
    assert result["data"]["row_count"] == 2
    assert "id" in result["data"]["columns"]


@patch("mcp_tools.execute_sql_query.execute_raw")
def test_execute_sql_query_blocked_by_safety(mock_raw):
    from mcp_tools.execute_sql_query import execute_sql_query
    result = execute_sql_query("DROP TABLE users")
    assert result["success"] is False
    mock_raw.assert_not_called()


# --- list_tables (with mocked DB) ---

@patch("mcp_tools.list_tables.execute_raw")
def test_list_tables(mock_raw):
    mock_raw.return_value = [{"table_name": "sales"}, {"table_name": "products"}]
    from mcp_tools.list_tables import list_tables
    result = list_tables()
    assert result["success"] is True
    assert "sales" in result["data"]["tables"]
    assert result["data"]["count"] == 2


# --- describe_table (with mocked DB) ---

@patch("mcp_tools.describe_table.execute_raw")
def test_describe_table(mock_raw):
    mock_raw.side_effect = [
        [{"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": None, "character_maximum_length": None, "constraint_type": "PRIMARY KEY"}],
        [{"cnt": 42}],
    ]
    from mcp_tools.describe_table import describe_table
    result = describe_table("products")
    assert result["success"] is True
    assert result["data"]["row_count"] == 42
    assert result["data"]["columns"][0]["column_name"] == "id"


def test_describe_table_invalid_name():
    from mcp_tools.describe_table import describe_table
    result = describe_table("users; DROP TABLE users--")
    assert result["success"] is False
    assert "Invalid" in result["error"]
