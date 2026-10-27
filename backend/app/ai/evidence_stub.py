"""Temporary evidence source for the AI check.

Person 3 replaces this file with the real get_evidence (plan order 2). Keep the same
return shape so ai_check.py does not change: a list of dicts with source_id, version,
text and kind ('fact' or 'guideline').
"""
from __future__ import annotations

from psycopg import Connection


def get_evidence(conn: Connection, channel: str) -> list[dict]:
    facts = conn.execute(
        "SELECT id, version, statement AS text FROM facts ORDER BY id"
    ).fetchall()
    guidelines = conn.execute(
        """
        SELECT id, version, text FROM guidelines
        WHERE is_active = TRUE AND %s = ANY(applies_to_channels)
        ORDER BY id
        """,
        (channel,),
    ).fetchall()

    items: list[dict] = []
    for row in facts:
        items.append({"source_id": row["id"], "version": row["version"], "text": row["text"], "kind": "fact"})
    for row in guidelines:
        items.append({"source_id": row["id"], "version": row["version"], "text": row["text"], "kind": "guideline"})
    return items
