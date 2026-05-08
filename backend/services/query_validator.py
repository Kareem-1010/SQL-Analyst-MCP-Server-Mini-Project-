"""
Advanced query validation and destructive operation detection.
Identifies DELETE, UPDATE, DROP, and other dangerous queries that require confirmation.
"""
import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

# Dangerous keywords and patterns
DESTRUCTIVE_KEYWORDS = {
    "DROP", "TRUNCATE", "DELETE", "UPDATE", "ALTER", "GRANT", "REVOKE",
    "COPY", "MOVE", "REINDEX", "VACUUM", "ANALYZE", "REFRESH", "EXECUTE"
}

READ_ONLY_KEYWORDS = {
    "SELECT", "EXPLAIN", "WITH"
}

UNSAFE_FUNCTIONS = {
    "pg_sleep", "system", "exec", "eval", "compile",
    "os.system", "subprocess", "shutil.rmtree"
}


def _tokenize_sql(sql: str) -> List[str]:
    """
    Basic SQL tokenization - split by whitespace and common delimiters.
    Returns tokens in uppercase for comparison.
    """
    # Remove comments
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Split and normalize
    tokens = re.findall(r'\b\w+\b|[\(\);,]', sql.upper())
    return tokens


def _has_where_clause(sql: str) -> bool:
    """Check if SQL statement has a WHERE clause."""
    tokens = _tokenize_sql(sql)
    return "WHERE" in tokens


def _has_limit_clause(sql: str) -> bool:
    """Check if SQL statement has a LIMIT clause."""
    tokens = _tokenize_sql(sql)
    return "LIMIT" in tokens


def _is_read_only_query(sql: str) -> bool:
    """Determine if query is read-only (SELECT, EXPLAIN, WITH, etc.)."""
    tokens = _tokenize_sql(sql)
    if not tokens:
        return False
    first_keyword = tokens[0]
    return first_keyword in READ_ONLY_KEYWORDS or first_keyword.startswith("WITH")


def check_query_safety_extended(sql: str) -> Tuple[bool, bool, str]:
    """
    Enhanced query safety check.
    
    Returns:
        (is_safe: bool, requires_confirmation: bool, reason: str)
    
    Raises:
        ValueError: If query contains absolutely unsafe operations
    """
    if not sql or not sql.strip():
        return False, False, "Empty SQL query"
    
    sql_upper = sql.upper().strip()
    tokens = _tokenize_sql(sql)
    
    # Check for multiple statements (command injection protection)
    if ";" in sql:
        statement_count = len([s for s in sql.split(";") if s.strip()])
        if statement_count > 1:
            raise ValueError("Multiple SQL statements in one query are not allowed")
    
    # Check for absolutely unsafe operations
    for unsafe_func in UNSAFE_FUNCTIONS:
        if unsafe_func.upper() in sql_upper or f"'{unsafe_func}'" in sql_upper:
            raise ValueError(f"Query contains unsafe function: {unsafe_func}")
    
    # Check for read-only queries
    if _is_read_only_query(sql):
        return True, False, "Safe read-only query"
    
    # Check for dangerous keywords
    first_keyword = tokens[0] if tokens else ""
    
    # TRUNCATE - always requires confirmation
    if first_keyword == "TRUNCATE":
        return True, True, "TRUNCATE requires confirmation - will delete all rows"
    
    # DELETE - requires confirmation if no WHERE clause
    if first_keyword == "DELETE":
        if not _has_where_clause(sql):
            return True, True, "DELETE without WHERE clause requires confirmation - would delete ALL rows"
        return True, True, "DELETE requires confirmation"
    
    # UPDATE - requires confirmation if no WHERE clause
    if first_keyword == "UPDATE":
        if not _has_where_clause(sql):
            return True, True, "UPDATE without WHERE clause requires confirmation - would update ALL rows"
        return True, True, "UPDATE requires confirmation"
    
    # ALTER TABLE - requires confirmation
    if first_keyword == "ALTER":
        return True, True, "ALTER TABLE requires confirmation - may affect data structure"
    
    # DROP - always requires confirmation
    if first_keyword == "DROP":
        return True, True, "DROP requires confirmation - will delete the entire object"
    
    # CREATE TABLE - might be okay, but requires confirmation to be safe
    if first_keyword == "CREATE":
        if len(tokens) > 1 and tokens[1] in ["TABLE", "INDEX", "VIEW", "DATABASE"]:
            return True, True, "CREATE operation requires confirmation"
        return True, False, "CREATE operation allowed"
    
    # GRANT/REVOKE - security sensitive
    if first_keyword in ["GRANT", "REVOKE"]:
        return True, True, "Permission change requires confirmation"
    
    # INSERT - check for bulk inserts
    if first_keyword == "INSERT":
        return True, True, "INSERT operation requires confirmation"
    
    # COPY - data loading, requires confirmation
    if first_keyword in ["COPY", "IMPORT"]:
        return True, True, "Data import requires confirmation"
    
    # Default: unknown operation
    if first_keyword in DESTRUCTIVE_KEYWORDS:
        return True, True, f"{first_keyword} operation requires confirmation"
    
    return True, False, "Query validation passed"


def extract_affected_tables(sql: str) -> List[str]:
    """
    Attempt to extract table names from SQL query.
    Returns list of table names that might be affected.
    """
    tables = []
    
    # Pattern matching for common SQL structures
    patterns = [
        r'FROM\s+(\w+)',
        r'INTO\s+(\w+)',
        r'UPDATE\s+(\w+)',
        r'DELETE\s+FROM\s+(\w+)',
        r'TABLE\s+(\w+)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, sql.upper())
        tables.extend(matches)
    
    # Remove duplicates and return
    return list(set([t.lower() for t in tables]))


def explain_query_operation(sql: str) -> str:
    """
    Generate a human-readable explanation of what the query does.
    Useful for confirmation dialogs and audit logs.
    """
    tokens = _tokenize_sql(sql)
    if not tokens:
        return "Empty query"
    
    first_keyword = tokens[0]
    tables = extract_affected_tables(sql)
    table_str = f" on table(s): {', '.join(tables)}" if tables else ""
    
    explanations = {
        "SELECT": f"Read data{table_str}",
        "INSERT": f"Add new records{table_str}",
        "UPDATE": f"Modify records{table_str}",
        "DELETE": f"Remove records{table_str}",
        "CREATE": f"Create new object{table_str}",
        "ALTER": f"Modify object structure{table_str}",
        "DROP": f"Delete object{table_str}",
        "TRUNCATE": f"Clear all data{table_str}",
        "EXPLAIN": f"Analyze query{table_str}",
    }
    
    return explanations.get(first_keyword, f"Execute {first_keyword} operation{table_str}")
