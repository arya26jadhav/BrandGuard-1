"""Brand sources for the Compose screen and source drawer (plan section 1).

Returns approved guidelines and product facts in the same shape as the frontend
BrandSource type, so every finding's source chip opens the real database record.
Any signed-in user can read sources; only the database is written by the admin screens.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.db import get_conn
from app.security import current_user

router = APIRouter(prefix="/api/sources", tags=["sources"])

GUIDELINES_SQL = """
    SELECT g.id, g.title, g.text, g.version, g.updated_at, g.required_text,
           g.is_active, g.category, u.name AS owner_name
    FROM guidelines g
    LEFT JOIN users u ON u.id = g.owner_id
    ORDER BY g.id
"""

FACTS_SQL = """
    SELECT f.id, f.title, f.statement, f.version, f.updated_at, f.valid_until,
           f.status, f.category, u.name AS owner_name
    FROM facts f
    LEFT JOIN users u ON u.id = f.owner_id
    ORDER BY f.id
"""


def _label(value) -> str:
    return value.strftime("%b %d, %Y") if value else ""


def _guideline_to_source(row: dict) -> dict:
    is_disclaimer = bool(row["required_text"])
    return {
        "id": row["id"],
        "title": row["title"],
        "category": "Disclaimer" if is_disclaimer else "Guideline",
        "version": row["version"],
        "updatedAt": _label(row["updated_at"]),
        "owner": row["owner_name"] or "Brand Team",
        "status": "Active" if row["is_active"] else "Needs review",
        "excerpt": row["text"],
        "expiryDate": None,
    }


def _fact_to_source(row: dict) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "category": "Product fact",
        "version": row["version"],
        "updatedAt": _label(row["updated_at"]),
        "owner": row["owner_name"] or "Product Team",
        "status": "Active" if row["status"] == "Active" else "Needs review",
        "excerpt": row["statement"],
        "expiryDate": row["valid_until"].isoformat() if row["valid_until"] else None,
    }


@router.get("")
def list_sources(
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(current_user),
) -> list[dict]:
    guidelines = [_guideline_to_source(r) for r in conn.execute(GUIDELINES_SQL).fetchall()]
    facts = [_fact_to_source(r) for r in conn.execute(FACTS_SQL).fetchall()]
    return guidelines + facts
