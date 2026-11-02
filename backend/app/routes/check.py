"""Check endpoints (plan section 1): run the check and list the latest findings.

Running a check is limited to the owning creator. Anyone who may view the content
(its owner, or a reviewer or manager) can read its latest findings.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.db import get_conn
from app.security import current_user
from app.services.checks import list_latest_findings, run_rule_check

router = APIRouter(prefix="/api/content", tags=["checks"])


def _content_owner(conn: Connection, content_id: str) -> str:
    row = conn.execute(
        "SELECT owner_id FROM content WHERE id = %s", (content_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return row["owner_id"]


def _ensure_owner_creator(conn: Connection, content_id: str, user: dict) -> None:
    owner_id = _content_owner(conn, content_id)
    if user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only the content creator can run a check")
    if owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only check your own content")


def _ensure_can_view(conn: Connection, content_id: str, user: dict) -> None:
    owner_id = _content_owner(conn, content_id)
    if user["role"] == "creator" and owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only access your own content")


@router.post("/{content_id}/check")
def check_content(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    _ensure_owner_creator(conn, content_id, user)
    return run_rule_check(conn, content_id, user)


@router.get("/{content_id}/findings")
def get_findings(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> list[dict]:
    _ensure_can_view(conn, content_id, user)
    findings = list_latest_findings(conn, content_id)
    # Which attachment(s) each finding came from, for the visual overlay. Additive: the
    # existing fields are unchanged.
    links = conn.execute(
        """SELECT fa.finding_id, fa.attachment_id FROM finding_attachments fa
           JOIN findings f ON f.id = fa.finding_id WHERE f.content_id = %s""",
        (content_id,),
    ).fetchall()
    by_finding: dict[str, list[str]] = {}
    for link in links:
        by_finding.setdefault(link["finding_id"], []).append(link["attachment_id"])
    for finding in findings:
        finding["attachmentIds"] = by_finding.get(finding["id"], [])
    if user["role"] == "creator":
        # Phase 2: a creator never sees the confidential-term finding, nor the findings of a
        # held submission (plan section 10).
        findings = [f for f in findings if f["type"] != "security"]
        held = conn.execute(
            "SELECT 1 FROM content_attachments WHERE content_id = %s AND read_status = 'held' LIMIT 1",
            (content_id,),
        ).fetchone()
        if held is not None:
            findings = []
    return findings
