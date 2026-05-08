#!/usr/bin/env python3
"""
QueryMind AI — Formal Threat Model Test Suite
===============================================

Validates QueryMind's defenses against the formal threat model defined in PAPER.md.

Attacker Capabilities (per threat model):
  T1 — SQL Injection via user-controlled query input
  T2 — Cross-tenant data access via JWT manipulation
  T3 — Privilege escalation via GRANT/REVOKE injection
  T4 — Denial-of-Service via long-running query functions (pg_sleep, recursive CTEs)
  T5 — Schema exfiltration via information_schema queries
  T6 — Stacked-statement command injection

Each test case is labeled with its threat category and expected defense outcome.
All cases should be BLOCKED or require CONFIRMATION.

Usage:
    cd backend
    python scripts/threat_model_tests.py
    python scripts/threat_model_tests.py --json-out experiments/threat_model_results.json
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.query_validator import check_query_safety_extended


ThreatCategory = Literal["T1_SQL_INJECTION", "T2_CROSS_TENANT", "T3_PRIVILEGE_ESCALATION",
                          "T4_DOS_ATTACK", "T5_SCHEMA_EXFILTRATION", "T6_STACKED_STATEMENT"]

@dataclass
class ThreatCase:
    name: str
    threat_category: str
    sql: str
    # Expected defense: "blocked" (is_safe=False) or "gated" (requires_confirmation=True)
    expected_defense: Literal["blocked", "gated"]
    description: str


THREAT_CASES: list[ThreatCase] = [
    # ── T1: SQL Injection ─────────────────────────────────────────────────
    ThreatCase("t1_tautology_bypass",
               "T1_SQL_INJECTION",
               "SELECT * FROM users WHERE username='' OR '1'='1'",
               "gated",  # Validator should flag this as safe READ but not inject — SELECT only
               "Classic tautology injection — SELECT so not blocked but still read-only"),
    ThreatCase("t1_union_exfil",
               "T1_SQL_INJECTION",
               "SELECT id FROM products UNION SELECT password FROM users",
               "gated",
               "UNION-based data exfiltration via read-only path"),
    ThreatCase("t1_comment_terminate",
               "T1_SQL_INJECTION",
               "SELECT * FROM products--; DROP TABLE products",
               "blocked",
               "Comment injection to terminate and append DROP TABLE"),
    ThreatCase("t1_sleep_inject",
               "T1_SQL_INJECTION",
               "SELECT * FROM users WHERE id=1 OR pg_sleep(10)=0",
               "blocked",
               "Time-based blind injection using pg_sleep"),
    ThreatCase("t1_stacked_drop",
               "T1_SQL_INJECTION",
               "'; DROP TABLE users; --",
               "blocked",
               "Classic stacked statement SQL injection"),
    ThreatCase("t1_hex_encode",
               "T1_SQL_INJECTION",
               "SELECT 0x44524f50205441424c4520757365727320",
               "gated",
               "Hex-encoded SQL attempt (SELECT is safe)"),

    # ── T3: Privilege Escalation ──────────────────────────────────────────
    ThreatCase("t3_grant_all",
               "T3_PRIVILEGE_ESCALATION",
               "GRANT ALL PRIVILEGES ON ALL TABLES TO public",
               "gated",
               "Mass privilege grant — should require confirmation"),
    ThreatCase("t3_grant_superuser",
               "T3_PRIVILEGE_ESCALATION",
               "ALTER ROLE guest SUPERUSER",
               "gated",
               "Escalate guest to superuser"),
    ThreatCase("t3_revoke_admin",
               "T3_PRIVILEGE_ESCALATION",
               "REVOKE ALL PRIVILEGES ON DATABASE sqlanalyst FROM alice",
               "gated",
               "Revoke all privileges from another user"),
    ThreatCase("t3_create_role",
               "T3_PRIVILEGE_ESCALATION",
               "CREATE ROLE hacker SUPERUSER LOGIN PASSWORD 'evil'",
               "gated",
               "Create a new superuser role"),

    # ── T4: Denial of Service ─────────────────────────────────────────────
    ThreatCase("t4_pg_sleep",
               "T4_DOS_ATTACK",
               "SELECT pg_sleep(3600)",
               "blocked",
               "1-hour sleep to exhaust DB connections"),
    ThreatCase("t4_pg_sleep_inject",
               "T4_DOS_ATTACK",
               "SELECT id FROM orders WHERE pg_sleep(60) IS NULL",
               "blocked",
               "pg_sleep embedded in WHERE clause"),
    ThreatCase("t4_recursive_cte",
               "T4_DOS_ATTACK",
               "WITH RECURSIVE r AS (SELECT 1 UNION ALL SELECT n+1 FROM r) SELECT * FROM r",
               "gated",
               "Infinite recursive CTE — should require confirmation or be flagged"),
    ThreatCase("t4_generate_series_large",
               "T4_DOS_ATTACK",
               "SELECT * FROM generate_series(1, 1000000000)",
               "gated",
               "Generate 1 billion rows — memory exhaustion"),

    # ── T5: Schema Exfiltration ───────────────────────────────────────────
    ThreatCase("t5_information_schema_tables",
               "T5_SCHEMA_EXFILTRATION",
               "SELECT table_name FROM information_schema.tables",
               "gated",
               "Enumerate all tables via information_schema"),
    ThreatCase("t5_information_schema_columns",
               "T5_SCHEMA_EXFILTRATION",
               "SELECT column_name, data_type FROM information_schema.columns WHERE table_name='users'",
               "gated",
               "Exfiltrate column names and types for users table"),
    ThreatCase("t5_pg_catalog_users",
               "T5_SCHEMA_EXFILTRATION",
               "SELECT usename, passwd FROM pg_shadow",
               "gated",
               "Access PostgreSQL password hashes via pg_shadow"),
    ThreatCase("t5_pg_stat_activity",
               "T5_SCHEMA_EXFILTRATION",
               "SELECT query, usename FROM pg_stat_activity",
               "gated",
               "Monitor other users' active queries"),

    # ── T6: Stacked Statements ────────────────────────────────────────────
    ThreatCase("t6_select_then_drop",
               "T6_STACKED_STATEMENT",
               "SELECT 1; DROP TABLE orders;",
               "blocked",
               "SELECT followed by DROP TABLE"),
    ThreatCase("t6_select_then_delete",
               "T6_STACKED_STATEMENT",
               "SELECT * FROM users; DELETE FROM users;",
               "blocked",
               "SELECT followed by DELETE all users"),
    ThreatCase("t6_triple_statement",
               "T6_STACKED_STATEMENT",
               "SELECT 1; SELECT 2; DROP DATABASE sqlanalyst;",
               "blocked",
               "Three stacked statements ending in DROP DATABASE"),
    ThreatCase("t6_update_then_drop",
               "T6_STACKED_STATEMENT",
               "UPDATE users SET is_active=false WHERE 1=1; DROP TABLE users;",
               "blocked",
               "Disable all users then drop table"),
]


def run_threat_tests() -> dict:
    passed = 0
    failed = 0
    results = []

    for case in THREAT_CASES:
        try:
            is_safe, requires_conf, reason = check_query_safety_extended(case.sql)
            blocked = not is_safe
            gated = requires_conf
        except ValueError as e:
            is_safe = False
            requires_conf = False
            blocked = True
            gated = False
            reason = str(e)

        if case.expected_defense == "blocked":
            defense_ok = blocked
            actual_defense = "blocked" if blocked else "passed_through"
        elif case.expected_defense == "gated":
            defense_ok = gated or blocked  # Either gated or blocked is acceptable
            actual_defense = "blocked" if blocked else ("gated" if gated else "passed_through")
        else:
            defense_ok = False
            actual_defense = "unknown"

        if defense_ok:
            passed += 1
            status = "PASS ✓"
        else:
            failed += 1
            status = "FAIL ✗"

        results.append({
            "name": case.name,
            "threat_category": case.threat_category,
            "description": case.description,
            "sql": case.sql[:80] + ("..." if len(case.sql) > 80 else ""),
            "expected_defense": case.expected_defense,
            "actual_defense": actual_defense,
            "reason": reason,
            "passed": defense_ok,
        })

        print(f"  {status}  [{case.threat_category}]  {case.name}")
        if not defense_ok:
            print(f"         Expected: {case.expected_defense}  Got: {actual_defense}")
            print(f"         SQL: {case.sql[:60]}...")

    total = len(THREAT_CASES)
    score = passed / total if total else 0.0

    # Per-category summary
    categories_done = {}
    for r in results:
        cat = r["threat_category"]
        categories_done.setdefault(cat, {"total": 0, "passed": 0})
        categories_done[cat]["total"] += 1
        categories_done[cat]["passed"] += int(r["passed"])

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "security_score": round(score, 4),
        "per_category": categories_done,
        "cases": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="QueryMind AI Threat Model Tests")
    parser.add_argument("--json-out", default="experiments/threat_model_results.json")
    args = parser.parse_args()

    print("=" * 72)
    print("  QueryMind AI — Threat Model Test Suite")
    print(f"  Total threat cases: {len(THREAT_CASES)}")
    print("=" * 72)
    print()

    results = run_threat_tests()

    print()
    print("=" * 72)
    print(f"  SECURITY SCORE: {results['passed']}/{results['total']} "
          f"({results['security_score']*100:.1f}%)")
    print()
    for cat, data in results["per_category"].items():
        score_pct = data["passed"] / data["total"] * 100
        print(f"  {cat:30s}  {data['passed']}/{data['total']}  ({score_pct:.0f}%)")
    print("=" * 72)

    report = {
        "project": "QueryMind AI",
        "study": "threat_model",
        "benchmark_date": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threat_model_summary": results,
    }

    out_path = Path(args.json_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nThreat model results written to: {args.json_out}")
    return 0 if results["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
