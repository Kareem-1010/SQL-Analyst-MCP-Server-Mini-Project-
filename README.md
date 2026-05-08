# QueryMind AI — Enterprise SQL Analytics Platform

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688)
![React](https://img.shields.io/badge/React-19-61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14%2B-336791)
![IEEE](https://img.shields.io/badge/Paper-IEEE%20Access%202025-blue)

> **Research-grade, multi-tenant AI SQL analytics platform with MCP-orchestrated safety validation,
> destructive query double-confirmation, and JWT-scoped per-user database isolation.**

**Version**: 4.0.0 | **Status**: Production-Ready | **License**: MIT

---

## 📄 Research Paper

This repository is the reference implementation for the IEEE paper:

> **"QueryMind: A Multi-Tenant AI-Driven SQL Analytics System with MCP-Orchestrated Safety Validation"**
> *IEEE Access 2025 — Under Review*

📖 **[Read the full paper → PAPER.md](PAPER.md)**
📊 **[Reproduce experiments → experiments/](experiments/README.md)**

```bibtex
@article{querymind2025,
  title   = {QueryMind: A Multi-Tenant AI-Driven SQL Analytics System with
             MCP-Orchestrated Safety Validation},
  author  = {[Author Name]},
  journal = {IEEE Access},
  year    = {2025},
  note    = {Under Review},
  url     = {https://github.com/[author]/sql-analyst-mcp}
}
```

---

## 🎯 Product Overview

QueryMind AI is an enterprise-grade SQL analytics platform that combines:
- **Natural Language Queries** — Ask questions in English, get SQL results via Groq LLaMA 3.3 70B
- **Multi-Tenant Architecture** — Each user gets a completely isolated PostgreSQL database
- **4-Layer MCP Safety Pipeline** — Token analysis, WHERE enforcement, function blocking, stacked detection
- **Double-Confirmation Gate (DCG)** — Cryptographic confirmation required for all destructive SQL
- **Audit Logging** — Full GDPR-compliant compliance trail for all operations
- **TF-IDF Schema Retrieval** — Context-aware, schema-ranked NL-to-SQL prompt building

### 🔬 Research Contributions (IEEE Paper)

| Contribution | Description |
|-------------|-------------|
| **C1: MCP Safety Pipeline** | 4-layer SQL validation; F1=0.96 on 52-case benchmark |
| **C2: Double-Confirmation Gate** | HMAC-SHA256 token; 100% prevents unconfirmed destructive SQL |
| **C3: JWT-Scoped DB Isolation** | Provable cross-tenant isolation at the database level |
| **C4: Open Benchmark** | 52 labeled SQL cases with adversarial inputs; reproducible |
| **C5: Semantic Schema Retrieval** | TF-IDF ranking for context-aware NL-to-SQL |

---

## ⚡ Quick Facts

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.11+, JavaScript/React 19 |
| **Database** | PostgreSQL 14+ (per-user isolation) |
| **AI Engine** | Groq API (LLaMA 3.3 70B) |
| **Auth** | JWT HS256, Bcrypt (12-round) |
| **Safety F1** | 0.9565 on 52-case benchmark |
| **Threat Defense** | 100% on T1/T3/T4/T6 threat categories |
| **Validation Latency** | p99 < 15ms |
| **Deployment** | Docker, Systemd, Nginx-ready |

---

## 🏗️ Technology Stack

### Frontend
- **React 19** — Latest React with hooks & concurrent rendering
- **Vite 5** — Lightning-fast module bundler & dev server
- **Framer Motion** — Smooth animations & gestures
- **Recharts** — Interactive data visualizations
- **Axios** — HTTP client with request/response interceptors

### Backend
- **FastAPI 0.111** — Modern async Python web framework
- **SQLAlchemy 2.0** — ORM with core SQL + query builder
- **Psycopg2** — PostgreSQL driver with connection pooling
- **Python-Jose** — JWT token handling (HS256)
- **Bcrypt** — Secure password hashing (12-round)
- **Groq API** — High-throughput LLM inference (LLaMA 3.3 70B)
- **scikit-learn** — TF-IDF schema retrieval and ranking
- **Prometheus Client** — Metrics endpoint for evaluation and monitoring

### Infrastructure
- **PostgreSQL 14+** — ACID transactions, per-user isolated databases
- **Redis** (optional) — Query caching & distributed sessions
- **Nginx** — Reverse proxy & static file serving
- **Docker** — Containerization for easy deployment

---

## 🔐 Security Architecture

### Multi-Tenant Isolation
```
Each user gets their own PostgreSQL database:
├─ User "alice" → database "db_alice" (completely isolated)
├─ User "bob"   → database "db_bob"   (completely isolated)
└─ Central DB   → "sqlanalyst"        (users table, audit logs)

✓ No way for alice to access bob's data
✓ JWT claim "db_name" scopes every database connection
✓ Database connection scoped to authenticated user on every request
```

### 4-Layer MCP Safety Pipeline
```
Layer 1: Stacked Statement Detection   → blocks "SELECT 1; DROP TABLE users;"
Layer 2: Unsafe Function Blocking      → blocks pg_sleep, exec, eval
Layer 3: Keyword Classification        → SELECT=safe | DELETE=confirmation
Layer 4: WHERE-Clause Enforcement      → warns DELETE/UPDATE without WHERE
```

### Double-Confirmation Gate
```
User asks: "DELETE FROM products"

POST /api/query/validate
  → {requires_confirmation: true, confirmation_token: "abc...", explanation: "..."}

Frontend → countdown timer + warning dialog
User clicks CONFIRM

POST /api/query/confirm + {sql, confirmation_token, user_confirms: true}
  → HMAC-SHA256 token verified (user-scoped, time-limited, single-use)
  → Re-validate query → Execute → Audit log
```

### Audit Logging
```
Every operation logged to central database:
✓ User registration/login/logout
✓ Query execution (SQL, execution time, rows affected)
✓ Destructive operations (DELETE, UPDATE, DROP) + confirmation events
✓ Failed authentication attempts
✓ Password changes
✓ Rate limit violations
```

---

## 📋 Key Features

### AI-Powered Query Generation
- Natural Language → SQL (Groq LLaMA 3.3 70B)
- Multi-turn conversation context
- Schema-aware query suggestions via TF-IDF retrieval
- Real-time SSE streaming responses

### Data Management
- CSV/Excel data ingestion with schema inference
- Interactive schema explorer
- Query history with results
- Bulk data operations

### Visualizations
- Bar, line, pie charts (Recharts)
- Real-time updates
- Export to CSV/PNG
- Theme switching (light/dark)

### Enterprise Features
- Per-user database isolation
- Audit logging & compliance trails (GDPR-ready)
- Rate limiting (token-bucket, per-user, per-endpoint)
- Query caching (optional Redis)
- Connection pooling & resource limits
- Prometheus metrics for SRE monitoring

---

## 🚀 Getting Started

### 1. Prerequisites
```bash
postgres --version    # PostgreSQL 14+
python --version      # Python 3.11+
node --version        # Node.js 18+
```

### 2. Backend Setup
```bash
cd backend

# Activate virtual environment
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/macOS

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env: set DATABASE_URL, GROQ_API_KEY, JWT_SECRET

# Initialize database
python scripts/init_db.py

# Start server
uvicorn main:app --reload --port 8000
# Open http://localhost:8000/docs
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:5173
```

### 4. Test the System
```bash
# Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"Test123!@"}'

# Validate a destructive query (should return requires_confirmation: true)
curl -X POST http://localhost:8000/api/query/validate \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{"sql":"DELETE FROM products"}'
```

---

## 🧪 Testing & Evaluation

### Unit & Integration Tests
```bash
cd backend
pytest tests/ -v
pytest tests/test_security.py -v          # Security-specific tests
pytest tests/test_auth_and_validation.py -v
pytest tests/ -v --cov=. --cov-report=html
```

### Research Benchmarks (Reproduce IEEE Paper Results)
```bash
# Safety benchmark with P/R/F1 + LaTeX table
python scripts/research_benchmark.py --skip-api --latex

# Ablation study
python scripts/ablation_study.py --latex

# Threat model defense tests
python scripts/threat_model_tests.py
```

### Test Coverage
- ✅ Authentication (register, login, password change)
- ✅ Multi-tenancy (user isolation, token scoping)
- ✅ Query validation (safe, destructive, multi-statement)
- ✅ Destructive operation confirmation (token flow)
- ✅ SQL injection corpus (20+ patterns)
- ✅ JWT attack resistance (malformed, tampered, expired tokens)
- ✅ Threat model (T1–T6 categories)

---

## 📊 Project Structure

```
sql-analyst-mcp/
├── PAPER.md                          # IEEE research paper (full text)
├── ARCHITECTURE.md                   # System design documentation
├── SETUP.md                          # Detailed installation guide
├── README.md                         # This file
├── experiments/                      # Reproducibility package
│   ├── README.md                     # How to reproduce all results
│   ├── benchmark_results.json        # Safety benchmark (52 cases, P/R/F1)
│   ├── ablation_results.json         # Ablation study results
│   └── threat_model_results.json     # Threat model scorecard
├── backend/
│   ├── main.py                       # FastAPI entrypoint + Prometheus metrics
│   ├── requirements.txt              # Python dependencies (pinned versions)
│   ├── .env.example                  # Configuration template
│   ├── scripts/
│   │   ├── init_db.py               # Database initialization
│   │   ├── seed_demo_data.py        # Synthetic dataset generator
│   │   ├── research_benchmark.py    # IEEE benchmark (52 cases, P/R/F1)
│   │   ├── ablation_study.py        # Per-layer ablation study
│   │   ├── threat_model_tests.py    # T1–T6 threat model tests
│   │   └── fixtures/                # Fixed-seed synthetic datasets
│   ├── db/
│   │   ├── database.py              # Connection pool + per-user routing
│   │   ├── auth_models.py           # User model
│   │   ├── audit_models.py          # Audit logging models
│   │   └── models.py                # Business models
│   ├── mcp_tools/                   # 14 MCP safety & execution tools
│   ├── routes/
│   │   ├── auth.py                  # /api/auth/* (JWT + bcrypt)
│   │   ├── confirm.py               # /api/query/validate + /confirm (DCG)
│   │   ├── query.py                 # /api/query/* (NL-to-SQL flow)
│   │   ├── analytics.py             # /api/analytics
│   │   ├── tables.py                # /api/tables/*
│   │   └── upload.py                # /api/upload (CSV ingest)
│   ├── services/
│   │   ├── query_validator.py       # 4-layer MCP safety pipeline
│   │   ├── groq_service.py          # Groq LLaMA 3.3 70B wrapper
│   │   ├── audit_service.py         # GDPR-compliant audit logging
│   │   ├── ingestion_service.py     # CSV schema inference
│   │   ├── schema_retrieval.py      # TF-IDF semantic schema retrieval
│   │   └── rate_limiter.py          # Token-bucket rate limiting
│   └── tests/
│       ├── test_auth_and_validation.py  # Auth + validation integration tests
│       ├── test_security.py             # Security test suite (SQL injection, JWT)
│       └── test_mcp_tools.py            # MCP tool unit tests
└── frontend/
    ├── src/
    │   ├── App.jsx                  # Main app + routing
    │   ├── pages/                   # Page components
    │   │   ├── AuthPage.jsx
    │   │   ├── ChatPage.jsx
    │   │   ├── Dashboard.jsx
    │   │   ├── LandingPage.jsx
    │   │   ├── QueryHistoryPage.jsx
    │   │   ├── UploadPage.jsx
    │   │   └── VisualizationPage.jsx
    │   ├── components/              # Reusable UI components
    │   │   ├── ConfirmModal.jsx     # DCG confirmation dialog
    │   │   ├── CommandPalette.jsx
    │   │   ├── SchemaPanel.jsx
    │   │   └── Toast.jsx
    │   └── services/api.js          # Axios API client
    ├── package.json
    └── vite.config.js
```

---

## 🌐 API Endpoints

### Authentication
```
POST   /api/auth/register           — Create account + isolated database
POST   /api/auth/login              — Get JWT token
GET    /api/auth/me                 — Current user info
POST   /api/auth/logout             — Logout (audit event)
POST   /api/auth/change-password    — Change password
```

### Query Management
```
POST   /api/query/validate          — Check if query needs confirmation (DCG)
POST   /api/query/confirm           — Execute confirmed destructive query
POST   /api/query                   — Full AI NL-to-SQL workflow
GET    /api/history                 — Query history
```

### Data Management
```
GET    /api/tables                  — List all tables in user's DB
GET    /api/tables/{name}           — Table schema & row count
POST   /api/upload                  — Import CSV/Excel
```

### System & Monitoring
```
GET    /health                      — Health check
GET    /api/system/info             — System metadata (research context)
GET    /metrics                     — Prometheus metrics endpoint
GET    /docs                        — Interactive API documentation (Swagger)
```

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Safety Validation (p99) | < 15 ms |
| Login (median) | ~420 ms |
| Registration (median) | ~1.4 s |
| Safety F1 Score | 0.9565 |
| Threat Defense Rate | 100% (22/22 cases) |
| Audit Log Overhead | ~9.6% |

---

## 🚢 Deployment

### Development
```bash
uvicorn main:app --reload --port 8000   # Backend
npm run dev                              # Frontend
```

### Production (Docker)
```bash
docker build -t querymind-ai .
docker run -e DATABASE_URL=... -e GROQ_API_KEY=... -p 8000:8000 querymind-ai
```

### Production (Systemd)
See [SETUP.md](SETUP.md) for full Nginx + Systemd configuration.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [**PAPER.md**](PAPER.md) | Full IEEE research paper |
| [**ARCHITECTURE.md**](ARCHITECTURE.md) | System design & data flow |
| [**SETUP.md**](SETUP.md) | Step-by-step installation |
| [**experiments/README.md**](experiments/README.md) | Reproduce evaluation results |
| **API Docs** | http://localhost:8000/docs |

---

## 🤝 Contributing

Contributions welcome. Priority areas aligned with the research roadmap:
- [ ] Controlled user study on DCG effectiveness
- [ ] Fine-tuned LLaMA for domain-specific SQL accuracy
- [ ] Geo-distributed multi-tenant PostgreSQL federation
- [ ] Restrict information_schema access per tenant (T5 defense)
- [ ] GraphQL API layer

---

## 📄 License

MIT License — See [LICENSE](LICENSE) file

---

## 📞 Support

- **Issues**: GitHub Issues
- **Documentation**: See SETUP.md, ARCHITECTURE.md, PAPER.md
- **API Docs**: http://localhost:8000/docs
- **Metrics**: http://localhost:8000/metrics

---

## 🎉 Acknowledgments

Built with FastAPI, React, SQLAlchemy, Groq, PostgreSQL, scikit-learn, and Prometheus.

---

**Version**: 4.0.0 | **Last Updated**: 2025-05 | **Status**: ✅ Production-Ready + IEEE Submission
**Maintainers**: QueryMind AI Research Team
