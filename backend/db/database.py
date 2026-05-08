from sqlalchemy import create_engine, text, event, pool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.exc import OperationalError, DatabaseError
from dotenv import load_dotenv
import os
import logging
import re
import time
from datetime import datetime, timezone
from urllib.parse import unquote

load_dotenv()

logger = logging.getLogger(__name__)

# Central DB URL — hosts the `users` table and audit logs
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/sqlanalyst")
QUERY_TIMEOUT = int(os.getenv("QUERY_TIMEOUT_SECONDS", "30"))
ENABLE_LOGS = os.getenv("SQL_ECHO", "false").lower() == "true"
MAX_RETRIES = 3
RETRY_DELAY = 1  # seconds

# ── Central engine (users table) ────────────────────────────────────────────
try:
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_recycle=3600,
        echo=ENABLE_LOGS,
        connect_args={
            "connect_timeout": QUERY_TIMEOUT,
            "keepalives": 1,
            "keepalives_idle": 30,
        },
    )
    
    # Add connection pool listeners for better error handling
    @event.listens_for(pool.Pool, "connect")
    def receive_connect(dbapi_conn, connection_record):
        """Set session timeout and other session parameters on new connections."""
        cursor = dbapi_conn.cursor()
        cursor.execute(f"SET statement_timeout TO {QUERY_TIMEOUT * 1000}")
        cursor.close()
    
    logger.info("[db] Central database engine created successfully")
except Exception as e:
    logger.error(f"[db] Failed to create central engine: {e}")
    raise

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency: yields a central DB session (for the users table)."""
    db = SessionLocal()
    try:
        yield db
    except OperationalError as e:
        logger.error(f"[db] Operational error in session: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Create all tables defined in models (central DB).
    Implements retry logic for connection failures.
    """
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            from db import models  # noqa: F401
            from db import auth_models  # noqa: F401
            from db import audit_models  # noqa: F401
            
            Base.metadata.create_all(bind=engine)
            _migrate_central_schema()
            logger.info("[db] Central database tables initialised successfully")
            return
        except OperationalError as e:
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                logger.error(f"[db] Failed to initialize database after {MAX_RETRIES} retries: {e}")
                raise
            logger.warning(f"[db] Database connection failed, retrying in {RETRY_DELAY}s ({retry_count}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"[db] Unexpected error during database initialization: {e}")
            raise


def _migrate_central_schema():
    """Backfill columns for databases created before the current schema."""
    statements = [
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS email VARCHAR(255)",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS display_name VARCHAR(100)",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS last_login TIMESTAMPTZ",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS failed_login_attempts INTEGER DEFAULT 0",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS account_locked BOOLEAN DEFAULT FALSE",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS last_password_change TIMESTAMPTZ",
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

    logger.info("[db] Central schema migration applied successfully")


# ── Per-user engine factory ──────────────────────────────────────────────────
_user_engines: dict = {}


def _build_user_db_url(db_name: str) -> str:
    """
    Swap the database name in the central DATABASE_URL.
    Works for postgresql://user:pass@host:port/dbname
    """
    if not db_name:
        raise ValueError("Database name cannot be empty")
    base = re.sub(r"/[^/]+$", f"/{db_name}", DATABASE_URL)
    return base


def get_user_engine(db_name: str):
    """
    Return (and cache) a SQLAlchemy engine connected to `db_name`.
    Call this with the per-user database name, e.g. 'db_alice'.
    Implements connection pooling and automatic reconnection.
    """
    if not db_name:
        raise ValueError("Database name is required")
    
    if db_name not in _user_engines:
        try:
            url = _build_user_db_url(db_name)
            user_engine = create_engine(
                url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
                echo=ENABLE_LOGS,
                connect_args={
                    "connect_timeout": QUERY_TIMEOUT,
                    "keepalives": 1,
                    "keepalives_idle": 30,
                },
            )
            
            # Test connection
            with user_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            _user_engines[db_name] = user_engine
            logger.info(f"[db] Created and tested engine for database '{db_name}'")
        except Exception as e:
            logger.error(f"[db] Failed to create engine for '{db_name}': {e}")
            raise
    
    return _user_engines[db_name]


def get_user_session(db_name: str):
    """
    Return a new SQLAlchemy Session bound to the user's DB engine.
    
    Args:
        db_name: User's database name (e.g., 'db_alice')
    
    Returns:
        SQLAlchemy Session instance
    
    Raises:
        ValueError: If db_name is invalid or database doesn't exist
    """
    try:
        user_engine = get_user_engine(db_name)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=user_engine)
        return Session()
    except Exception as e:
        logger.error(f"[db] Failed to create session for '{db_name}': {e}")
        raise


def init_user_db(db_name: str):
    """
    Create the query_history and other tables inside the user's database.
    Called once right after the per-user database is created.
    
    Args:
        db_name: User's database name
    
    Raises:
        Exception: If table creation fails
    """
    try:
        from sqlalchemy import MetaData, Table, Column, Integer, String, Text, Float, DateTime
        from sqlalchemy.sql import func as sa_func

        user_engine = get_user_engine(db_name)
        meta = MetaData()
        
        # Query history table
        Table(
            "query_history", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_query", Text, nullable=False),
            Column("generated_sql", Text, nullable=True),
            Column("result_summary", Text, nullable=True),
            Column("row_count", Integer, nullable=True),
            Column("execution_time_ms", Float, nullable=True),
            Column("status", String(20), default="success"),
            Column("error_message", Text, nullable=True),
            Column("created_at", DateTime(timezone=True), server_default=sa_func.now()),
        )
        
        # User settings/preferences table
        Table(
            "user_preferences", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("key", String(100), nullable=False, unique=True),
            Column("value", Text, nullable=True),
            Column("created_at", DateTime(timezone=True), server_default=sa_func.now()),
        )
        
        # Query cache table (for performance optimization)
        Table(
            "query_cache", meta,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("query_hash", String(64), nullable=False, unique=True, index=True),
            Column("sql", Text, nullable=False),
            Column("result", Text, nullable=False),  # JSON-serialized
            Column("created_at", DateTime(timezone=True), server_default=sa_func.now()),
            Column("expires_at", DateTime(timezone=True), nullable=True),
        )
        
        meta.create_all(bind=user_engine)
        logger.info(f"[db] Initialised tables in user database '{db_name}'")
    except Exception as e:
        logger.error(f"[db] Failed to initialize user database '{db_name}': {e}")
        raise


def create_postgres_database(db_name: str):
    """
    Create a new PostgreSQL database named `db_name` using the admin (central) engine.
    Must run outside a transaction — uses autocommit via raw psycopg2 connection.
    
    Args:
        db_name: Name of the new database (e.g., 'db_alice')
    
    Raises:
        Exception: If database creation fails
    """
    import psycopg2
    from urllib.parse import urlparse

    if not db_name:
        raise ValueError("Database name cannot be empty")
    
    # Validate database name (alphanumeric + underscore, max 63 chars for PostgreSQL)
    if not re.match(r'^[a-z0-9_]+$', db_name) or len(db_name) > 63:
        raise ValueError(f"Invalid database name: {db_name}")

    parsed = urlparse(DATABASE_URL)
    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=username,
                password=password,
                dbname=parsed.path.lstrip("/"),
                connect_timeout=QUERY_TIMEOUT,
            )
            conn.autocommit = True
            
            try:
                with conn.cursor() as cur:
                    # Check if the database already exists
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
                    if cur.fetchone():
                        logger.info(f"[db] PostgreSQL database '{db_name}' already exists")
                        return
                    
                    # Create the database
                    cur.execute(f'CREATE DATABASE "{db_name}" ENCODING = \'UTF8\'')
                    logger.info(f"[db] PostgreSQL database '{db_name}' created successfully")
                    return
            finally:
                conn.close()
        
        except psycopg2.OperationalError as e:
            retry_count += 1
            if retry_count >= MAX_RETRIES:
                logger.error(f"[db] Failed to create database '{db_name}' after {MAX_RETRIES} retries: {e}")
                raise
            logger.warning(f"[db] Database creation failed, retrying in {RETRY_DELAY}s ({retry_count}/{MAX_RETRIES})")
            time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.error(f"[db] Unexpected error creating database '{db_name}': {e}")
            raise


def drop_user_database(db_name: str, force: bool = False):
    """
    Drop a user's database (careful operation - used for cleanup).
    
    Args:
        db_name: Database to drop
        force: If True, force drop even if connections exist
    
    Raises:
        Exception: If operation fails
    """
    import psycopg2
    from urllib.parse import urlparse

    if not force and db_name.startswith("db_sqlanalyst"):
        raise ValueError("Cannot drop protected database")

    parsed = urlparse(DATABASE_URL)
    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    
    try:
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=username,
            password=password,
            dbname=parsed.path.lstrip("/"),
            connect_timeout=QUERY_TIMEOUT,
        )
        conn.autocommit = True
        
        try:
            with conn.cursor() as cur:
                if force:
                    # Terminate all connections to the database
                    cur.execute(f"""
                        SELECT pg_terminate_backend(pg_stat_activity.pid)
                        FROM pg_stat_activity
                        WHERE pg_stat_activity.datname = %s
                        AND pid <> pg_backend_pid()
                    """, (db_name,))
                
                cur.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
                logger.info(f"[db] Dropped database '{db_name}'")
                
                # Clear from cache
                if db_name in _user_engines:
                    del _user_engines[db_name]
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"[db] Failed to drop database '{db_name}': {e}")
        raise


def execute_raw(sql: str, params: dict = None, timeout: int = None, db_engine=None):
    """
    Execute raw SQL and return results.
    - SELECT/RETURNING → list of dicts
    - INSERT/UPDATE/DELETE/DDL → {"rowcount": n, "dml": True}
    
    Uses engine.begin() so writes are committed automatically.
    Pass `db_engine` to run against a user-specific database instead of the central one.
    
    Args:
        sql: SQL query to execute
        params: Query parameters (for parameterized queries)
        timeout: Query timeout in seconds (defaults to QUERY_TIMEOUT)
        db_engine: Engine to use (defaults to central engine)
    
    Returns:
        List of dicts for SELECT queries, or dict with rowcount for DML
    
    Raises:
        ValueError: If SQL is unsafe or parameters are invalid
        DatabaseError: If query execution fails
    """
    if not sql or not sql.strip():
        raise ValueError("SQL query cannot be empty")
    
    t = timeout or QUERY_TIMEOUT
    target = db_engine or engine
    
    try:
        with target.begin() as conn:
            conn.execute(text(f"SET LOCAL statement_timeout = {t * 1000}"))
            result = conn.execute(text(sql), params or {})
            
            if result.returns_rows:
                return [dict(row._mapping) for row in result]
            else:
                return {"rowcount": result.rowcount, "dml": True}
    except DatabaseError as e:
        logger.error(f"[db] Database error executing query: {e}")
        raise
    except Exception as e:
        logger.error(f"[db] Error executing raw SQL: {e}")
        raise


def check_db_health() -> dict:
    """
    Check the health of the central database connection.
    
    Returns:
        dict with health status and details
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as health"))
            conn.commit()
            
        return {
            "status": "healthy",
            "database": "central",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"[db] Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "central",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def check_user_db_health(db_name: str) -> dict:
    """
    Check the health of a specific user's database.
    
    Args:
        db_name: User's database name
    
    Returns:
        dict with health status and details
    """
    try:
        user_engine = get_user_engine(db_name)
        with user_engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as health"))
            conn.commit()
        
        return {
            "status": "healthy",
            "database": db_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"[db] Health check failed for '{db_name}': {e}")
        return {
            "status": "unhealthy",
            "database": db_name,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

