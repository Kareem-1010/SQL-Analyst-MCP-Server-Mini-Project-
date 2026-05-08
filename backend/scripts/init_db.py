#!/usr/bin/env python3
"""
Database initialization script for QueryMind AI.
Sets up the central PostgreSQL database and required extensions.
Run this before starting the application.

Usage:
    python scripts/init_db.py
    python scripts/init_db.py --clean  # Reset everything
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from urllib.parse import urlparse
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
from urllib.parse import unquote

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def parse_db_url(db_url: str) -> dict:
    """Parse PostgreSQL connection URL."""
    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "user": unquote(parsed.username) if parsed.username else "postgres",
        "password": unquote(parsed.password) if parsed.password else "",
        "dbname": parsed.path.lstrip("/") or "sqlanalyst",
    }


def connect_to_postgres(host: str, port: int, user: str, password: str, dbname: str = "postgres"):
    """Create connection to PostgreSQL."""
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=dbname,
            connect_timeout=10,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        return conn
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        raise


def create_database(conn, db_name: str):
    """Create the central database if it doesn't exist."""
    with conn.cursor() as cur:
        # Check if database exists
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (db_name,)
        )
        
        if cur.fetchone():
            logger.info(f"✅ Database '{db_name}' already exists")
            return False
        
        # Create database
        try:
            cur.execute(
                f"CREATE DATABASE \"{db_name}\" ENCODING = 'UTF8' "
                f"LC_COLLATE = 'en_US.UTF-8' LC_CTYPE = 'en_US.UTF-8'"
            )
            logger.info(f"✅ Created database '{db_name}'")
            return True
        except psycopg2.Error as e:
            logger.error(f"Failed to create database: {e}")
            raise


def enable_extensions(conn):
    """Enable useful PostgreSQL extensions."""
    extensions = ["uuid-ossp", "pgcrypto"]
    
    with conn.cursor() as cur:
        for ext in extensions:
            try:
                cur.execute(f"CREATE EXTENSION IF NOT EXISTS \"{ext}\"")
                logger.info(f"✅ Enabled extension '{ext}'")
            except psycopg2.Error as e:
                logger.warning(f"Could not enable extension '{ext}': {e}")


def create_central_tables(conn):
    """Create central database tables."""
    with conn.cursor() as cur:
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(60) UNIQUE NOT NULL,
                hashed_password VARCHAR(128) NOT NULL,
                db_name VARCHAR(70) NOT NULL UNIQUE,
                email VARCHAR(255),
                display_name VARCHAR(100),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMPTZ
            )
        """)
        # Create indexes separately
        cur.execute("CREATE INDEX IF NOT EXISTS idx_username ON users(username)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_email ON users(email)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON users(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_is_active ON users(is_active)")
        logger.info("✅ Created 'users' table")
        
        # Audit logs table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id SERIAL PRIMARY KEY,
                username VARCHAR(60) NOT NULL,
                db_name VARCHAR(70) NOT NULL,
                action VARCHAR(50) NOT NULL,
                resource VARCHAR(255),
                status VARCHAR(20) DEFAULT 'success',
                details TEXT,
                ip_address VARCHAR(45),
                user_agent VARCHAR(500),
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Create indexes for audit_logs
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_logs(username)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at)")
        logger.info("✅ Created 'audit_logs' table")
        
        # Query audits table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_audits (
                id SERIAL PRIMARY KEY,
                username VARCHAR(60) NOT NULL,
                db_name VARCHAR(70) NOT NULL,
                sql TEXT NOT NULL,
                execution_time_ms FLOAT,
                rows_affected INTEGER,
                is_read_only BOOLEAN DEFAULT TRUE,
                requires_confirmation BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'success',
                error_message TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        # Create indexes for query_audits
        cur.execute("CREATE INDEX IF NOT EXISTS idx_query_username ON query_audits(username)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_query_read_only ON query_audits(is_read_only)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_query_created ON query_audits(created_at)")
        logger.info("✅ Created 'query_audits' table")
        
        # Password history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS password_history (
                id SERIAL PRIMARY KEY,
                username VARCHAR(60) NOT NULL,
                hashed_password VARCHAR(128) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_password_history_username ON password_history(username)")
        logger.info("✅ Created 'password_history' table")


def clean_database(conn, db_name: str):
    """Drop the central database (careful operation)."""
    with conn.cursor() as cur:
        # Terminate all connections
        cur.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid()
        """, (db_name,))
        
        # Drop database
        try:
            cur.execute(f"DROP DATABASE IF EXISTS \"{db_name}\"")
            logger.info(f"✅ Dropped database '{db_name}'")
        except psycopg2.Error as e:
            logger.error(f"Failed to drop database: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Initialize QueryMind AI database"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Drop and recreate the database (WARNING: destructive)"
    )
    parser.add_argument(
        "--db-url",
        default=os.getenv("DATABASE_URL"),
        help="Database URL (default: DATABASE_URL env var)"
    )
    
    args = parser.parse_args()
    
    if not args.db_url:
        logger.error("DATABASE_URL not set. Please set it via .env or --db-url")
        sys.exit(1)
    
    # Parse connection details
    db_config = parse_db_url(args.db_url)
    db_name = db_config.pop("dbname")
    
    logger.info(f"🔧 Initializing database: {db_name}")
    logger.info(f"   Host: {db_config['host']}:{db_config['port']}")
    
    # Connect to PostgreSQL (default database)
    conn = connect_to_postgres(**db_config, dbname="postgres")
    
    try:
        # Clean if requested
        if args.clean:
            confirm = input(
                f"⚠️  This will DELETE the '{db_name}' database. Type 'yes' to confirm: "
            )
            if confirm == "yes":
                clean_database(conn, db_name)
            else:
                logger.info("Skipped database cleanup")
        
        # Create database
        create_database(conn, db_name)
        
        # Connect to the new database
        conn.close()
        db_config["dbname"] = db_name
        conn = connect_to_postgres(**db_config)
        
        # Create extensions
        logger.info("🔌 Enabling extensions...")
        enable_extensions(conn)
        
        # Create tables
        logger.info("📋 Creating tables...")
        create_central_tables(conn)
        
        logger.info("✅ Database initialization complete!")
        logger.info(f"   Connection: {db_config['host']}:{db_config['port']}/{db_name}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
