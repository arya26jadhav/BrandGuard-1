"""Accept, edit or reject a finding (plan section 2). Creator-only, owner-only.

Accept applies the suggested fix to content.body_text, shifts the offsets of
later open findings, and writes decisions, content_versions and revisions in one
transaction. Open findings that overlap the replaced span become 'resolved'.
"""
from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from pydantic import BaseModel, Field

from app.db import get_conn
from app.security import current_user
from app.services.checks import list_latest_findings
from app.services.content_text import plain_text_to_html

router = APIRouter(prefix="/api/findings", tags=["findings"])

EDITABLE_STATUSES = ("Draft", "Checked", "Fixing", "Changes requested")


class DecisionIn(BaseModel):
    action: Literal["accept", "edit", "reject"]
    editedText: str | None = Field(default=None, max_length=5000)
    rejectReason: str | None = Field(default=None, max_length=500)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _shift_other_findings(conn: Connection, content_id: str, finding_id: str,
                          start: int, end: int, delta: int) -> None:
    rows = conn.execute(
        """
        SELECT id, start, "end" FROM findings
        WHERE content_id = %s AND status = 'open' AND id <> %s AND start IS NOT NULL
        FOR UPDATE
        """,
        (content_id, finding_id),
    ).fetchall()
    for r in rows:
        if r["start"] >= end:
            conn.execute(
                'UPDATE findings SET start = %s, "end" = %s WHERE id = %s',
                (r["start"] + delta, r["end"] + delta, r["id"]),
            )
        elif r["end"] > start:
            # Overlaps the text that was just replaced; its span no longer exists.
            conn.execute("UPDATE findings SET status = 'resolved' WHERE id = %s", (r["id"],))


@router.patch("/{finding_id}")
def decide_finding(
    finding_id: str,
    payload: DecisionIn,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    if user["role"] != "creator":
        raise HTTPException(status_code=403, detail="Only the content creator can decide on findings")

    new_status = ""
    content_id = ""
    new_body = ""
    with conn.transaction():
        row = conn.execute(
            """
            SELECT f.id, f.content_id, f.status, f.start, f."end", f.original_text,
                   f.suggested_fix, f.ai_generated, f.title,
                   c.owner_id, c.status AS content_status, c.body_text
            FROM findings f
            JOIN content c ON c.id = f.content_id
            WHERE f.id = %s
            FOR UPDATE OF f, c
            """,
            (finding_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Finding not found")
        if row["owner_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="You can only decide on your own content")
        if row["content_status"] not in EDITABLE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"Content is locked in status {row['content_status']}",
            )
        if row["status"] != "open":
            raise HTTPException(status_code=409, detail="Finding is no longer open")

        content_id = row["content_id"]
        text = row["body_text"]
        start, end = row["start"], row["end"]
        action = payload.action
        content_changed = False
        version = None
        new_body = text

        if action == "reject":
            new_status = "rejected"
        else:
            new_status = "accepted" if action == "accept" else "edited"
            replacement = row["suggested_fix"] if action == "accept" else (payload.editedText or "")
            if not replacement.strip():
                detail = (
                    "This finding has no suggested fix. Use Edit or Reject."
                    if action == "accept"
                    else "Edited text cannot be empty"
                )
                raise HTTPException(status_code=422, detail=detail)

            if start is None:
                # Missing-content finding (for example a required disclaimer): append at the end.
                new_body = f"{text}\n\n{replacement}" if text else replacement
            else:
                if row["original_text"] is not None and text[start:end] != row["original_text"]:
                    raise HTTPException(
                        status_code=409,
                        detail="The text changed since the check. Run the check again.",
                    )
                new_body = text[:start] + replacement + text[end:]
                delta = len(replacement) - (end - start)
                _shift_other_findings(conn, content_id, finding_id, start, end, delta)
            content_changed = True

        conn.execute("UPDATE findings SET status = %s WHERE id = %s", (new_status, finding_id))

        conn.execute(
            """
            INSERT INTO decisions
                (id, finding_id, content_id, actor_id, action, note, reject_reason, edited_text)
            VALUES (%s, %s, %s, %s, %s, '', %s, %s)
            """,
            (
                _new_id("dec"), finding_id, content_id, user["id"], action,
                payload.rejectReason if action == "reject" else None,
                payload.editedText if action == "edit" else None,
            ),
        )

        to_status = row["content_status"]
        if content_changed:
            version = conn.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 AS v FROM content_versions WHERE content_id = %s",
                (content_id,),
            ).fetchone()["v"]
            change_type = "ai_fix" if (action == "accept" and row["ai_generated"]) else "human_edit"
            conn.execute(
                """
                INSERT INTO content_versions
                    (id, content_id, version, body_text, body_html, change_type,
                     actor_id, actor_label, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    _new_id("cv"), content_id, version, new_body, plain_text_to_html(new_body),
                    change_type, user["id"], user["name"], f"{new_status}: {row['title']}",
                ),
            )
            if to_status in ("Checked", "Changes requested"):
                to_status = "Fixing"
            conn.execute(
                "UPDATE content SET body_text = %s, body_html = %s, status = %s, updated_at = now() WHERE id = %s",
                (new_body, plain_text_to_html(new_body), to_status, content_id),
            )

        conn.execute(
            """
            INSERT INTO revisions
                (id, content_id, actor_id, actor_label, kind, action, detail,
                 from_status, to_status, version)
            VALUES (%s, %s, %s, %s, 'person', %s, %s, %s, %s, %s)
            """,
            (
                _new_id("rev"), content_id, user["id"], user["name"], new_status,
                row["title"], row["content_status"], to_status, version,
            ),
        )

    return {
        "findingId": finding_id,
        "status": new_status,
        "bodyText": new_body,
        "contentStatus": to_status,
        "findings": list_latest_findings(conn, content_id),
    }
