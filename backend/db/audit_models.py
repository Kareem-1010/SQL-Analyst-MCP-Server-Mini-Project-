"""
SQLAlchemy models for audit logging in central database.
Tracks all critical operations across all users.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.sql import func
from db.database import Base


class AuditLog(Base):
    """
    Central audit log tracking all user actions across the system.
    Stored in central database for security & compliance.
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), nullable=False, index=True)
    db_name = Column(String(70), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)  # login, query, delete, register, etc.
    resource = Column(String(255), nullable=True)  # table name, endpoint, etc.
    status = Column(String(20), default="success")  # success, failure, warning
    details = Column(Text, nullable=True)  # JSON-serialized details
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class QueryAudit(Base):
    """
    Per-user query audit trail (stored in central DB for compliance).
    Tracks query execution details for analysis and debugging.
    """
    __tablename__ = "query_audits"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), nullable=False, index=True)
    db_name = Column(String(70), nullable=False, index=True)
    sql = Column(Text, nullable=False)
    execution_time_ms = Column(Float, nullable=True)
    rows_affected = Column(Integer, nullable=True)
    is_read_only = Column(Boolean, default=True, index=True)
    requires_confirmation = Column(Boolean, default=False)
    status = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class PasswordHistory(Base):
    """
    Track password changes for security compliance.
    """
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
