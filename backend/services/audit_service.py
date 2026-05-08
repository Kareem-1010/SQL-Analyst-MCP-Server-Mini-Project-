"""
Audit logging service - logs all critical operations for compliance and debugging.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def log_audit_event(
    db_session: Session,
    username: str,
    db_name: str,
    action: str,
    resource: Optional[str] = None,
    status: str = "success",
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """
    Log an audit event to the central database.
    
    Args:
        db_session: Central database session
        username: Username performing the action
        db_name: User's database name
        action: Type of action (login, query, delete, register, etc.)
        resource: Resource being accessed (table name, endpoint, etc.)
        status: success, failure, or warning
        details: JSON-serializable additional details
        ip_address: Client IP address
        user_agent: Client user agent string
    
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        from db.audit_models import AuditLog
        
        audit = AuditLog(
            username=username,
            db_name=db_name,
            action=action,
            resource=resource,
            status=status,
            details=json.dumps(details) if details else None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        db_session.add(audit)
        db_session.commit()
        logger.info(f"[audit] {action} by {username} - {status}")
        return True
    except Exception as e:
        logger.error(f"[audit] Failed to log event: {e}")
        return False


def log_query_audit(
    db_session: Session,
    username: str,
    db_name: str,
    sql: str,
    execution_time_ms: Optional[float] = None,
    rows_affected: Optional[int] = None,
    is_read_only: bool = True,
    requires_confirmation: bool = False,
    status: str = "success",
    error_message: Optional[str] = None
) -> bool:
    """
    Log a query execution for audit trail and analysis.
    
    Args:
        db_session: Central database session
        username: Username executing the query
        db_name: User's database
        sql: The SQL query that was executed
        execution_time_ms: Query execution time in milliseconds
        rows_affected: Number of rows affected
        is_read_only: Whether this is a read-only query
        requires_confirmation: Whether this operation requires confirmation
        status: success or failure
        error_message: Error message if status is failure
    
    Returns:
        bool: True if logged successfully, False otherwise
    """
    try:
        from db.audit_models import QueryAudit
        
        query_audit = QueryAudit(
            username=username,
            db_name=db_name,
            sql=sql,
            execution_time_ms=execution_time_ms,
            rows_affected=rows_affected,
            is_read_only=is_read_only,
            requires_confirmation=requires_confirmation,
            status=status,
            error_message=error_message,
        )
        db_session.add(query_audit)
        db_session.commit()
        logger.info(f"[query_audit] {username} - {'RO' if is_read_only else 'RW'} - {status}")
        return True
    except Exception as e:
        logger.error(f"[query_audit] Failed to log query: {e}")
        return False


def get_user_audit_log(
    db_session: Session,
    username: str,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Retrieve audit logs for a specific user.
    
    Args:
        db_session: Central database session
        username: Username to filter by
        limit: Number of records to retrieve
        offset: Pagination offset
    
    Returns:
        List of audit events
    """
    try:
        from db.audit_models import AuditLog
        
        logs = db_session.query(AuditLog).filter(
            AuditLog.username == username
        ).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()
        
        return [
            {
                "id": log.id,
                "action": log.action,
                "resource": log.resource,
                "status": log.status,
                "details": json.loads(log.details) if log.details else None,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"[audit] Failed to retrieve audit log: {e}")
        return []


def get_recent_audits(
    db_session: Session,
    days: int = 7,
    limit: int = 50
) -> list:
    """
    Get recent audit events across all users (for admin monitoring).
    
    Args:
        db_session: Central database session
        days: Number of days to look back
        limit: Maximum number of records
    
    Returns:
        List of recent audit events
    """
    try:
        from db.audit_models import AuditLog
        from datetime import datetime, timedelta, timezone
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        logs = db_session.query(AuditLog).filter(
            AuditLog.created_at >= cutoff
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                "username": log.username,
                "action": log.action,
                "status": log.status,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"[audit] Failed to retrieve recent audits: {e}")
        return []
