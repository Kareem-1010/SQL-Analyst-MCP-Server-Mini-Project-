"""
Schema retrieval service.

Ranks tables and their column metadata against a user's natural-language query
to provide a smaller, more relevant schema context for NL-to-SQL generation.

This is useful for research because it adds a measurable retrieval layer on top
of the base SQL generation workflow.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from mcp_tools.describe_table import describe_table
from mcp_tools.list_tables import list_tables

logger = logging.getLogger(__name__)


@dataclass
class SchemaMatch:
    table_name: str
    score: float
    summary: str


def _table_document(table_name: str, description: dict[str, Any]) -> str:
    columns = description.get("columns", [])
    column_text = " ".join(
        f"{col.get('column_name', '')} {col.get('data_type', '')} {col.get('nullable', '')}"
        for col in columns
    )
    summary = description.get("summary", "") or description.get("table_name", "")
    return f"{table_name} {summary} {column_text}".strip()


def rank_relevant_tables(question: str, db_engine, top_k: int = 5) -> dict[str, Any]:
    """Return the most relevant tables and schema text for a question."""
    tables_result = list_tables(db_engine=db_engine)
    if not tables_result.get("success"):
        return {
            "success": False,
            "error": tables_result.get("error", "Unable to list tables"),
            "matches": [],
            "schema_context": "No tables available.",
        }

    table_names = tables_result.get("data", {}).get("tables", [])
    if not table_names:
        return {
            "success": True,
            "matches": [],
            "schema_context": "No tables available.",
        }

    documents: list[str] = []
    metadata: list[dict[str, Any]] = []
    for table_name in table_names:
        desc = describe_table(table_name, db_engine=db_engine)
        if not desc.get("success"):
            continue
        table_data = desc.get("data", {})
        documents.append(_table_document(table_name, table_data))
        metadata.append({
            "table_name": table_name,
            "description": table_data,
        })

    if not documents:
        return {
            "success": True,
            "matches": [],
            "schema_context": "No describable tables found.",
        }

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(documents + [question])
    query_vector = matrix[-1]
    schema_vectors = matrix[:-1]
    scores = cosine_similarity(schema_vectors, query_vector).ravel()

    ranked = sorted(
        (
            SchemaMatch(
                table_name=item["table_name"],
                score=float(score),
                summary=item["description"].get("table_name", item["table_name"]),
            )
            for item, score in zip(metadata, scores)
        ),
        key=lambda entry: entry.score,
        reverse=True,
    )[:top_k]

    context_parts = []
    for match in ranked:
        desc = next(item["description"] for item in metadata if item["table_name"] == match.table_name)
        columns = desc.get("columns", [])
        column_str = ", ".join(
            f"{col.get('column_name')} ({col.get('data_type')})" for col in columns
        )
        context_parts.append(
            f"Table: {match.table_name}\nScore: {match.score:.3f}\nColumns: {column_str}"
        )

    return {
        "success": True,
        "matches": [match.__dict__ for match in ranked],
        "schema_context": "\n\n".join(context_parts) if context_parts else "No relevant tables found.",
        "table_count": len(table_names),
    }