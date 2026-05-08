"""
SQLAlchemy model for the User table stored in the CENTRAL sqlanalyst database.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Index
from sqlalchemy.sql import func
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(60), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    db_name = Column(String(70), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    display_name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True, index=True)
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # Composite index for faster lookups
    __table_args__ = (
        Index('idx_username_active', 'username', 'is_active'),
    )
