"""
SQL Analyst MCP Server — FastAPI Application Entry Point
Production-grade, multi-tenant SQL analytics platform with AI-powered insights.
"""
import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from dotenv import load_dotenv
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from db.database import init_db, check_db_health
from routes.upload import router as upload_router
from routes.tables import router as tables_router
from routes.query import router as query_router
from routes.history import router as history_router
from routes.mcp import router as mcp_router
from routes.auth import router as auth_router
from routes.analytics import router as analytics_router
from routes.confirm import router as confirm_router

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "querymind_requests_total",
    "Total HTTP requests served by QueryMind AI",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "querymind_request_latency_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle management.
    Initializes database on startup, cleanup on shutdown.
    """
    logger.info("🚀 Starting SQL Analyst MCP Server…")
    try:
        init_db()
        logger.info("✅ Central database initialised")
        
        health = check_db_health()
        if health["status"] == "healthy":
            logger.info("✅ Database connection verified")
        else:
            logger.warning(f"⚠️ Database health check warning: {health.get('error')}")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    yield
    logger.info("🛑 Shutting down SQL Analyst MCP Server")


app = FastAPI(
    title="QueryMind AI — SQL Analyst MCP Server",
    description=(
        "Research-grade, multi-tenant AI-powered SQL analytics platform. "
        "Per-user database isolation, JWT auth, MCP tool orchestration, "
        "Groq LLaMA 3 integration with double-confirmation for destructive ops."
    ),
    version="4.0.0",
    lifespan=lifespan,
)

# CORS Configuration
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Collect request count and latency metrics for experiments."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start

    route_path = request.url.path
    if route_path.startswith("/api/"):
        route_path = "/api/*"

    REQUEST_COUNT.labels(request.method, route_path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, route_path).observe(elapsed)
    return response


# ── Global Error Handler ────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with proper logging and response."""
    logger.error(f"[exception] {type(exc).__name__}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred. Please try again later.",
            "request_path": request.url.path,
        }
    )


# ── Include Routers ────────────────────────────────────────────────────────

app.include_router(auth_router)         # /api/auth — public (no JWT needed)
app.include_router(confirm_router)      # /api/query/{validate,confirm} — destructive query confirmation
app.include_router(upload_router)
app.include_router(tables_router)
app.include_router(query_router)
app.include_router(history_router)
app.include_router(mcp_router)
app.include_router(analytics_router)    # /api/analytics


# ── Public Endpoints ────────────────────────────────────────────────────────

@app.get("/", tags=["system"])
def root():
    """Root endpoint — confirms server is running."""
    return {
        "message": "QueryMind AI — SQL Analyst MCP Server is running",
        "version": "4.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "4.0.0",
        "timestamp": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc
        ).isoformat(),
    }


@app.get("/api/system/info", tags=["system"])
def system_info():
    """Public endpoint — comprehensive system metadata for documentation."""
    return {
        "product": "QueryMind AI",
        "tagline": "Enterprise-grade AI-Powered SQL Analytics Platform",
        "version": "4.0.0",
        "status": "production",
        "architecture": {
            "backend": "FastAPI 0.111+ (Python 3.11+, async/await, WebSockets)",
            "ai_engine": "Groq LLaMA 3.3 70B (1000+ tokens/sec)",
            "database": "PostgreSQL 14+ (per-user isolated databases, connection pooling)",
            "auth": "JWT HS256 with secure password hashing (bcrypt)",
            "protocol": "MCP (Model Context Protocol) v1.0",
            "caching": "Redis-ready for distributed deployments",
        },
        "security": {
            "features": [
                "Per-user database isolation",
                "JWT token-based authentication",
                "Password strength validation (12+ chars, complexity)",
                "Double-confirmation for destructive SQL (DELETE, UPDATE, DROP, etc.)",
                "Audit logging for all operations",
                "Query safety validation (blocks SQL injection patterns)",
                "Rate limiting (per-user, per-endpoint)",
                "CORS with whitelist",
                "HTTPS-ready (configurable)",
            ],
            "compliance": [
                "Query audit trail with timestamps",
                "User action logging",
                "Data isolation guarantees",
                "Configurable query timeout (prevents runaway queries)",
            ],
        },
        "features": [
            "Natural Language → SQL (NL→SQL with Groq)",
            "Multi-turn conversation context",
            "Real-time SSE streaming responses",
            "Semantic schema retrieval for top-k table ranking",
            "13 MCP security validation tools",
            "Per-user database isolation",
            "Double-confirmation for destructive SQL",
            "AI-generated insights from results",
            "Query optimization suggestions",
            "Schema-aware SQL suggestions",
            "CSV/Excel data ingestion",
            "Interactive data visualization (Recharts)",
            "Query history & analytics",
            "Query execution caching",
            "Prometheus metrics endpoint for experiments",
            "Request rate limiting",
            "Comprehensive audit logs",
        ],
        "mcp_tools": {
            "safety_validation": [
                "check_query_safety",
                "explain_sql_in_plain_english",
            ],
            "query_execution": [
                "execute_sql_query",
                "natural_language_to_sql",
                "explain_query",
                "optimize_query",
            ],
            "metadata": [
                "list_tables",
                "describe_table",
            ],
            "data_manipulation": [
                "create_table",
                "alter_table",
                "insert_data",
                "select_data",
                "update_data",
                "delete_data",
            ],
        },
        "api_endpoints": {
            "authentication": [
                "POST /api/auth/register",
                "POST /api/auth/login",
                "POST /api/auth/logout",
                "POST /api/auth/change-password",
                "GET /api/auth/me",
            ],
            "query_confirmation": [
                "POST /api/query/validate",
                "POST /api/query/confirm",
            ],
            "queries": [
                "POST /api/query",
                "POST /api/query/stream",
                "GET /api/history",
            ],
            "data_management": [
                "GET /api/tables",
                "GET /api/tables/{name}",
                "POST /api/upload",
            ],
        },
        "research": {
            "title": "QueryMind: Multi-Tenant AI-Driven SQL Analytics with MCP Orchestration",
            "abstract": (
                "QueryMind is a research-grade analytics platform combining "
                "Model Context Protocol (MCP) tool orchestration with per-user database isolation. "
                "It demonstrates production-ready patterns for secure, scalable AI-SQL integration."
            ),
            "contributions": [
                "MCP tool-chain pattern for safe AI SQL execution with validation gates",
                "Per-user PostgreSQL isolation via JWT-scoped database routing",
                "Double-confirmation pattern for destructive operations (2FA for SQL)",
                "Real-time AI explanations with streaming LLM responses",
                "TF-IDF schema retrieval for semantic table ranking",
                "Prometheus metrics for reproducible evaluation",
                "Token-bucket rate limiting for fair multi-tenant resource allocation",
                "Comprehensive audit logging for compliance and debugging",
            ],
            "technologies": [
                "FastAPI (modern async Python framework)",
                "SQLAlchemy (ORM with query parameter safety)",
                "PostgreSQL (ACID transactions, isolation levels)",
                "Groq API (high-throughput LLM inference)",
                "Pydantic (data validation)",
            ],
        },
    }


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint for benchmarking and monitoring."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

