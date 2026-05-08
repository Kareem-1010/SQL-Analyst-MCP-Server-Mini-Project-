# Experiments — Reproducibility Package

This directory contains all experiment outputs and scripts needed to reproduce
the evaluation results in the QueryMind AI IEEE paper.

## Directory Structure

```
experiments/
├── benchmark_results.json       # Full safety benchmark (52 cases) with P/R/F1
├── ablation_results.json        # Ablation study: per-layer contribution
├── threat_model_results.json    # Threat model security scorecard
└── README.md                    # This file
```

## Reproducing All Results

### Prerequisites

```bash
cd backend
pip install -r requirements.txt
```

> The backend server does **not** need to be running for the offline safety tests.
> Start `uvicorn main:app --port 8000` before running API latency tests.

---

### 1. Safety Benchmark (Table III in paper)

Runs the 52-case labeled SQL benchmark with Precision/Recall/F1 and baseline comparison.

```bash
python scripts/research_benchmark.py \
  --json-out experiments/benchmark_results.json \
  --skip-api \
  --latex
```

To also run the live API latency benchmark (requires running backend):
```bash
python scripts/research_benchmark.py \
  --base-url http://127.0.0.1:8000 \
  --json-out experiments/benchmark_results.json \
  --n-repeat 20 \
  --latex
```

---

### 2. Ablation Study (Table IV in paper)

Measures F1 contribution of each safety layer independently.

```bash
python scripts/ablation_study.py \
  --json-out experiments/ablation_results.json \
  --latex
```

---

### 3. Threat Model Tests (Table V in paper)

Validates defense against T1–T6 attacker capabilities.

```bash
python scripts/threat_model_tests.py \
  --json-out experiments/threat_model_results.json
```

---

### 4. Unit & Integration Tests

```bash
pytest tests/ -v --tb=short
pytest tests/test_security.py -v         # Security-specific
pytest tests/test_auth_and_validation.py -v
```

---

## Expected Results (from paper submission)

| Metric | QueryMind | Baseline |
|--------|-----------|----------|
| Accuracy | ≥ 0.90 | ~0.75 |
| Precision | ≥ 0.95 | ~0.80 |
| Recall | ≥ 0.90 | ~0.70 |
| F1 Score | ≥ 0.92 | ~0.74 |

| Threat Category | Defense Rate |
|-----------------|-------------|
| T1 SQL Injection | 100% |
| T3 Privilege Escalation | 100% (gated) |
| T4 DoS Attacks | 100% |
| T6 Stacked Statements | 100% |

---

## Environment

All results generated with:
- Python 3.11
- FastAPI 0.111
- PostgreSQL 14
- scikit-learn 1.4
- Groq API (llama-3.3-70b-versatile)

Random seed: `42` (where applicable)

See `backend/.env.example` for full environment variable specification.
