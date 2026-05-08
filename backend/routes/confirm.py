"""
Route: /api/query/confirm
Handles confirmation of destructive/dangerous SQL operations.

POST /api/query/validate  — Check if query requires confirmation
POST /api/query/confirm   — Execute query after user confirms
"""
import logging
import hashlib
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db, get_user_session, execute_raw
from auth.dependencies import get_current_user
from services.query_validator import check_query_safety_extended, explain_query_operation, extract_affected_tables
from services.audit_service import log_audit_event, log_query_audit

router = APIRouter(prefix="/api/query", tags=["query"])
logger = logging.getLogger(__name__)

# In-memory store for pending confirmations (session-based)
# In production, use Redis for distributed systems
_pending_confirmations: dict = {}


class QueryValidationRequest(BaseModel):
    """Validate if a query requires confirmation."""
    sql: str


class QueryValidationResponse(BaseModel):
    """Response from query validation."""
    is_safe: bool
    requires_confirmation: bool
    reason: str
    explanation: str
    affected_tables: list[str]
    confirmation_token: Optional[str] = None


class QueryConfirmationRequest(BaseModel):
    """Confirm and execute a destructive query."""
    sql: str
    confirmation_token: Optional[str] = None
    user_confirms: bool = False


class QueryConfirmationResponse(BaseModel):
    """Response from query execution."""
    success: bool
    message: str
    rowcount: Optional[int] = None
    error: Optional[str] = None


def _generate_confirmation_token(sql: str, username: str) -> str:
    """Generate a secure token for confirming a specific query."""
    combined = f"{sql}|{username}|{json.dumps(sql)}"
    return hashlib.sha256(combined.encode()).hexdigest()


@router.post("/validate", response_model=QueryValidationResponse)
def validate_query(
    request: QueryValidationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Validate a SQL query and determine if it requires confirmation.
    
    Returns information about:
    - Whether query is safe
    - If confirmation is required
    - Human-readable explanation of what the query does
    - Tables affected by the query
    - Confirmation token (if confirmation required)
    """
    sql = request.sql.strip()
    username = current_user["username"]
    db_name = current_user["db_name"]
    
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")
    
    try:
        # Check query safety
        is_safe, requires_confirmation, reason = check_query_safety_extended(sql)
        
        # Generate confirmation token if needed
        confirmation_token = None
        if requires_confirmation:
            confirmation_token = _generate_confirmation_token(sql, username)
            _pending_confirmations[confirmation_token] = {
                "sql": sql,
                "username": username,
                "db_name": db_name,
                "timestamp": __import__("time").time()
            }
        
        # Get human-readable explanation
        explanation = explain_query_operation(sql)
        affected_tables = extract_affected_tables(sql)
        
        # Log validation
        log_audit_event(
            db, username, db_name, "query_validate",
            resource=f"validate_{'safe' if is_safe else 'unsafe'}",
            status="success",
            details={
                "requires_confirmation": requires_confirmation,
                "affected_tables": affected_tables
            }
        )
        
        return QueryValidationResponse(
            is_safe=is_safe,
            requires_confirmation=requires_confirmation,
            reason=reason,
            explanation=explanation,
            affected_tables=affected_tables,
            confirmation_token=confirmation_token
        )
    
    except ValueError as e:
        logger.warning(f"[query] Safety validation failed for {username}: {e}")
        log_audit_event(
            db, username, db_name, "query_validate",
            status="failure",
            details={"error": str(e)}
        )
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[query] Unexpected error during validation: {e}")
        raise HTTPException(status_code=500, detail="Error validating query")


@router.post("/confirm", response_model=QueryConfirmationResponse)
def confirm_and_execute(
    request: QueryConfirmationRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Execute a destructive query after user explicitly confirms.
    
    Requires:
    - Valid confirmation token from /validate endpoint
    - user_confirms flag set to True
    - Matching username in token
    
    Logs the execution in audit trail.
    """
    sql = request.sql.strip()
    username = current_user["username"]
    db_name = current_user["db_name"]
    
    if not sql:
        raise HTTPException(status_code=400, detail="SQL query cannot be empty")
    
    if not request.user_confirms:
        raise HTTPException(
            status_code=400,
            detail="User must explicitly confirm dangerous operation"
        )
    
    try:
        # Re-validate query safety
        is_safe, requires_confirmation, reason = check_query_safety_extended(sql)
        
        if not is_safe:
            raise ValueError("Query failed safety validation")
        
        # If confirmation required, verify token
        if requires_confirmation:
            if not request.confirmation_token:
                raise ValueError("Confirmation token required for this operation")
            
            if request.confirmation_token not in _pending_confirmations:
                log_audit_event(
                    db, username, db_name, "query_confirm",
                    status="failure",
                    details={"reason": "invalid_token"}
                )
                raise ValueError("Invalid or expired confirmation token")
            
            pending = _pending_confirmations[request.confirmation_token]
            if pending["username"] != username or pending["sql"] != sql:
                log_audit_event(
                    db, username, db_name, "query_confirm",
                    status="failure",
                    details={"reason": "token_mismatch"}
                )
                raise ValueError("Confirmation token does not match")
            
            # Clean up token
            del _pending_confirmations[request.confirmation_token]
        
        # Get user's database connection
        user_session = get_user_session(db_name)
        user_engine = user_session.bind
        
        try:
            # Execute the query
            import time
            start_time = time.time()
            
            result = execute_raw(sql, timeout=30, db_engine=user_engine)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            # Extract rowcount
            rowcount = None
            if isinstance(result, dict) and "rowcount" in result:
                rowcount = result["rowcount"]
            
            # Log successful execution
            log_audit_event(
                db, username, db_name, "query_execute",
                status="success",
                details={
                    "requires_confirmation": requires_confirmation,
                    "execution_time_ms": execution_time_ms,
                    "rowcount": rowcount
                }
            )
            
            log_query_audit(
                db, username, db_name, sql,
                execution_time_ms=execution_time_ms,
                rows_affected=rowcount,
                is_read_only=False,
                requires_confirmation=requires_confirmation,
                status="success"
            )
            
            logger.info(f"[query] {username} executed {len(sql)} chars SQL - {rowcount or 0} rows affected")
            
            return QueryConfirmationResponse(
                success=True,
                message=f"Query executed successfully. Rows affected: {rowcount or 0}",
                rowcount=rowcount
            )
        
        finally:
            user_session.close()
    
    except ValueError as e:
        logger.warning(f"[query] Execution failed for {username}: {e}")
        log_audit_event(
            db, username, db_name, "query_execute",
            status="failure",
            details={"error": str(e)}
        )
        log_query_audit(
            db, username, db_name, sql,
            is_read_only=False,
            requires_confirmation=requires_confirmation if 'requires_confirmation' in locals() else False,
            status="failure",
            error_message=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"[query] Unexpected error executing query: {e}")
        log_audit_event(
            db, username, db_name, "query_execute",
            status="failure",
            details={"error": str(e), "error_type": type(e).__name__}
        )
        raise HTTPException(status_code=500, detail="Error executing query: " + str(e)[:100])


@router.get("/pending-confirmations")
def list_pending_confirmations(current_user: dict = Depends(get_current_user)):
    """
    List pending confirmations for the current user (debug endpoint).
    In production, remove or restrict this.
    """
    username = current_user["username"]
    pending = [
        {
            "token": token,
            "sql_length": len(data["sql"]),
            "age_seconds": __import__("time").time() - data["timestamp"]
        }
        for token, data in _pending_confirmations.items()
        if data["username"] == username
    ]
    return {"pending_confirmations": pending}
