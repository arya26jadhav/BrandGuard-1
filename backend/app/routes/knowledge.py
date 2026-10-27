from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from app.db import get_conn
from app.security import require_role

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

EDITOR_ROLES = ("manager", "admin")

FactStatus = Literal["Active", "Expiring soon", "Expired"]
FactSeverity = Literal["High", "Medium"]
GuidelineSeverity = Literal["critical", "warning", "info"]


class FactUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    statement: str | None = Field(default=None, min_length=1)
    status: FactStatus | None = None
    valid_until: date | None = None
    severity_on_change: FactSeverity | None = None
    note: str | None = Field(default=None, max_length=500)


class GuidelineUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    severity: GuidelineSeverity | None = None
    is_active: bool | None = None


FACT_COLUMNS = """
    id, product_id, title, statement, fact_type, structured_value,
    match_keywords, severity_on_change, owner_id, version,
    valid_from, valid_until, status, category, updated_at
"""

GUIDELINE_COLUMNS = """
    id, short_name, title, text, category, rule_type, severity,
    applies_to_channels, required_text, version, owner_id, is_active, updated_at
"""


def to_fact(row: dict) -> dict:
    return {
        "id": row["id"],
        "productId": row["product_id"],
        "title": row["title"],
        "statement": row["statement"],
        "factType": row["fact_type"],
        "structuredValue": row["structured_value"],
        "matchKeywords": row["match_keywords"],
        "severityOnChange": row["severity_on_change"],
        "ownerId": row["owner_id"],
        "version": row["version"],
        "validFrom": row["valid_from"],
        "validUntil": row["valid_until"],
        "status": row["status"],
        "category": row["category"],
        "updatedAt": row["updated_at"],
    }


def to_guideline(row: dict) -> dict:
    return {
        "id": row["id"],
        "shortName": row["short_name"],
        "title": row["title"],
        "text": row["text"],
        "category": row["category"],
        "ruleType": row["rule_type"],
        "severity": row["severity"],
        "appliesToChannels": row["applies_to_channels"],
        "requiredText": row["required_text"],
        "version": row["version"],
        "ownerId": row["owner_id"],
        "isActive": row["is_active"],
        "updatedAt": row["updated_at"],
    }


@router.get("/facts")
def list_facts(
    status: FactStatus | None = Query(default=None),
    conn: Connection = Depends(get_conn),
) -> list[dict]:
    if status is None:
        rows = conn.execute(f"SELECT {FACT_COLUMNS} FROM facts ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            f"SELECT {FACT_COLUMNS} FROM facts WHERE status = %s ORDER BY id",
            (status,),
        ).fetchall()
    return [to_fact(r) for r in rows]


@router.get("/facts/{fact_id}")
def get_fact(fact_id: str, conn: Connection = Depends(get_conn)) -> dict:
    row = conn.execute(
        f"SELECT {FACT_COLUMNS} FROM facts WHERE id = %s", (fact_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return to_fact(row)


@router.patch("/facts/{fact_id}")
def update_fact(
    fact_id: str,
    body: FactUpdate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    """Update the fields sent, bump the version, and write a fact_versions row.

    Column names come only from the FactUpdate model, never from user input.
    """
    changes = body.model_dump(exclude_unset=True)
    note = changes.pop("note", None) or ""
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{column} = %s" for column in changes)
    params = [*changes.values(), fact_id]
    row = conn.execute(
        f"""
        UPDATE facts
        SET {set_clause}, version = version + 1, updated_at = now()
        WHERE id = %s
        RETURNING {FACT_COLUMNS}
        """,
        params,
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")

    conn.execute(
        """
        INSERT INTO fact_versions
            (fact_id, version, statement, structured_value, note, owner,
             changed_by, valid_from, valid_until)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row["id"],
            row["version"],
            row["statement"],
            Jsonb(row["structured_value"] or {}),
            note,
            row["owner_id"] or "",
            user["id"],
            row["valid_from"],
            row["valid_until"],
        ),
    )
    return to_fact(row)


@router.get("/facts/{fact_id}/history")
def fact_history(fact_id: str, conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        """
        SELECT version, statement, note, owner, changed_by, changed_at, valid_from, valid_until
        FROM fact_versions WHERE fact_id = %s ORDER BY version DESC
        """,
        (fact_id,),
    ).fetchall()
    return [
        {
            "version": r["version"],
            "statement": r["statement"],
            "note": r["note"],
            "owner": r["owner"],
            "changedBy": r["changed_by"],
            "changedAt": r["changed_at"],
            "validFrom": r["valid_from"],
            "validUntil": r["valid_until"],
        }
        for r in rows
    ]


@router.get("/guidelines")
def list_guidelines(conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        f"SELECT {GUIDELINE_COLUMNS} FROM guidelines ORDER BY id"
    ).fetchall()
    return [to_guideline(r) for r in rows]


@router.get("/guidelines/{guideline_id}")
def get_guideline(guideline_id: str, conn: Connection = Depends(get_conn)) -> dict:
    row = conn.execute(
        f"SELECT {GUIDELINE_COLUMNS} FROM guidelines WHERE id = %s", (guideline_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Guideline not found")
    return to_guideline(row)


@router.patch("/guidelines/{guideline_id}")
def update_guideline(
    guideline_id: str,
    body: GuidelineUpdate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{column} = %s" for column in changes)
    params = [*changes.values(), guideline_id]
    row = conn.execute(
        f"""
        UPDATE guidelines
        SET {set_clause}, version = version + 1, updated_at = now()
        WHERE id = %s
        RETURNING {GUIDELINE_COLUMNS}
        """,
        params,
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Guideline not found")
    return to_guideline(row)


@router.get("/glossary")
def list_glossary(conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        "SELECT id, approved_term, avoid_terms, kind, explanation, is_active "
        "FROM glossary ORDER BY id"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "approvedTerm": r["approved_term"],
            "avoidTerms": r["avoid_terms"],
            "kind": r["kind"],
            "explanation": r["explanation"],
            "isActive": r["is_active"],
        }
        for r in rows
    ]


@router.get("/assets")
def list_assets(
    asset_type: str | None = Query(default=None),
    conn: Connection = Depends(get_conn),
) -> list[dict]:
    base = "SELECT id, label, asset_type, version, status, hex, usage_note, metadata FROM assets"
    if asset_type is None:
        rows = conn.execute(f"{base} ORDER BY id").fetchall()
    else:
        rows = conn.execute(f"{base} WHERE asset_type = %s ORDER BY id", (asset_type,)).fetchall()
    return [
        {
            "id": r["id"],
            "label": r["label"],
            "assetType": r["asset_type"],
            "version": r["version"],
            "status": r["status"],
            "hex": r["hex"],
            "usageNote": r["usage_note"],
            "metadata": r["metadata"],
        }
        for r in rows
    ]
