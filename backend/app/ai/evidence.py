"""Evidence retrieval v1 (Person 3).

Returns every active fact and every active guideline for a channel, with source IDs and
versions. Same return shape as evidence_stub.py, so ai_check.py needs only an import change.
"""
from __future__ import annotations

from psycopg import Connection

# Facts with these statuses are sent to the AI. "Expired" facts are not.
ACTIVE_FACT_STATUSES = ["Active", "Expiring soon"]


def get_evidence(conn: Connection, channel: str) -> list[dict]:
    facts = conn.execute(
        """
        SELECT id, version, statement AS text FROM facts
        WHERE status = ANY(%s)
        ORDER BY id
        """,
        (ACTIVE_FACT_STATUSES,),
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
        items.append({"source_id": row["id"], "version": row["version"],
                      "text": row["text"], "kind": "fact"})
    for row in guidelines:
        items.append({"source_id": row["id"], "version": row["version"],
                      "text": row["text"], "kind": "guideline"})
    return items
