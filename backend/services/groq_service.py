"""
Groq API service.
Primary model: llama-3.3-70b-versatile  |  Fallback: llama3-70b-8192

Features:
  - groq_complete()       — single-turn completion
  - groq_complete_multi() — multi-turn conversation completion
  - groq_stream()         — single-turn streaming
  - groq_insights()       — generate 3 AI bullet-point insights from query result
"""
import os
import json
import logging
from typing import Optional
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PRIMARY_MODEL = "llama-3.3-70b-versatile"
FALLBACK_MODEL = "llama3-70b-8192"

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        _client = Groq(api_key=api_key)
    return _client


def groq_complete(
    prompt: str,
    system_prompt: str = "You are a helpful AI data analyst assistant.",
    model: str = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> str:
    """
    Send a prompt to Groq and return the response text.
    Automatically falls back to FALLBACK_MODEL on failure.
    """
    client = _get_client()
    models_to_try = [model or PRIMARY_MODEL, FALLBACK_MODEL]

    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            content = response.choices[0].message.content
            logger.info(f"[groq_service] Response from model={m}, tokens={response.usage.total_tokens}")
            return content
        except Exception as e:
            logger.warning(f"[groq_service] Model {m} failed: {e}")
            if m == FALLBACK_MODEL:
                raise
    return ""


def groq_complete_multi(
    messages: list[dict],
    system_prompt: str = "You are a helpful AI data analyst assistant.",
    model: str = None,
    max_tokens: int = 1024,
    temperature: float = 0.1,
) -> str:
    """
    Multi-turn chat completion. `messages` is a list of
    {"role": "user"|"assistant", "content": "..."} dicts.
    """
    client = _get_client()
    m = model or PRIMARY_MODEL
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    try:
        response = client.chat.completions.create(
            model=m,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        content = response.choices[0].message.content
        logger.info(f"[groq_service] Multi-turn response from model={m}")
        return content
    except Exception as e:
        logger.warning(f"[groq_service] Multi-turn model {m} failed: {e}, trying fallback")
        response = client.chat.completions.create(
            model=FALLBACK_MODEL,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content


def groq_stream(
    prompt: str,
    system_prompt: str = "You are a helpful AI data analyst assistant.",
    model: str = None,
):
    """Generator that streams token chunks from Groq."""
    client = _get_client()
    m = model or PRIMARY_MODEL
    try:
        stream = client.chat.completions.create(
            model=m,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1024,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as e:
        logger.error(f"[groq_service] Streaming error: {e}")
        yield f"Error: {str(e)}"


def groq_insights(
    sql: str,
    rows: list[dict],
    columns: list[str],
    row_count: int,
) -> list[str]:
    """
    Generate 3 concise bullet-point insights about a query result.
    Returns a list of strings (one per insight).
    """
    if not rows:
        return []

    # Build a compact result preview (max 20 rows)
    preview_rows = rows[:20]
    preview_text = "\n".join(
        "  " + ", ".join(f"{c}: {str(r.get(c, ''))[:40]}" for c in columns)
        for r in preview_rows
    )

    prompt = f"""You are a data analyst. Analyze this SQL query result and provide exactly 3 short, 
insightful observations. Each insight should be on its own line starting with "- ". 
Be specific, quantitative where possible, and actionable.

SQL: {sql}

Columns: {', '.join(columns)}
Total rows: {row_count}
Sample data:
{preview_text}

Provide exactly 3 bullet-point insights about patterns, anomalies, or key findings:"""

    try:
        result = groq_complete(
            prompt,
            system_prompt="You are a senior data analyst. Provide concise, specific, data-driven insights.",
            max_tokens=400,
            temperature=0.3,
        )
        # Parse bullet points
        insights = [
            line.lstrip("- •*").strip()
            for line in result.strip().split("\n")
            if line.strip().startswith(("-", "•", "*")) and len(line.strip()) > 3
        ]
        return insights[:3]
    except Exception as e:
        logger.error(f"[groq_service] Insights error: {e}")
        return []


def groq_suggest_queries(schema_context: str, table_name: str) -> list[str]:
    """
    Generate 5 relevant natural-language questions for a newly uploaded table.
    Returns a list of question strings.
    """
    prompt = f"""A user just uploaded a table called '{table_name}' with the following schema:

{schema_context}

Generate exactly 5 useful, diverse natural-language questions a business analyst might ask about this data.
Format: one question per line, no numbering or bullets.
Keep questions concise and directly answerable with SQL."""

    try:
        result = groq_complete(
            prompt,
            system_prompt="You are a business intelligence expert helping users explore their data.",
            max_tokens=300,
            temperature=0.5,
        )
        lines = [l.strip() for l in result.strip().split("\n") if l.strip()]
        return lines[:5]
    except Exception as e:
        logger.error(f"[groq_service] Suggest queries error: {e}")
        return []
