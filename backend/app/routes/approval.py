"""Approval workflow routes (plan hours 12-16).

Endpoints: submit for review, start fixing, approve, request changes, publish.

Transition rules live in app/services/workflow.py and are not repeated here. This module maps
the database status text (Title Case, from the content.status CHECK in data/schema.sql) to the
workflow enum, checks ownership for creator moves, and writes the status change and a
revisions row in one transaction.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from pydantic import BaseModel, Field

from app.db import get_conn
from app.security import current_user
from app.services.workflow import Forbidden, InvalidTransition, Role, Status, check_transition

router = APIRouter(prefix="/api/content", tags=["approval"])

# Must match the content.status CHECK constraint in data/schema.sql (a test checks this).
DB_STATUS: dict[Status, str] = {
    Status.DRAFT: "Draft",
    Status.CHECKED: "Checked",
    Status.FIXING: "Fixing",
    Status.IN_REVIEW: "In Review",
    Status.CHANGES_REQUESTED: "Changes requested",
    Status.APPROVED: "Approved",
    Status.PUBLISHED: "Published",
    Status.NEEDS_REVALIDATION: "Needs revalidation",
}
STATUS_FROM_DB: dict[str, Status] = {value: key for key, value in DB_STATUS.items()}

ROLE_FROM_APP: dict[str, Role] = {
    "creator": Role.CREATOR,
    "manager": Role.MANAGER,
    "reviewer": Role.REVIEWER,
    "admin": Role.ADMIN,
}

# Timestamp column set by each move. Fixed names only, never user input.
STAMP_COLUMN: dict[Status, str | None] = {
    Status.IN_REVIEW: "submitted_at",
    Status.APPROVED: "approved_at",
    Status.PUBLISHED: "published_at",
}


class CommentBody(BaseModel):
    comment: str | None = Field(default=None, max_length=2000)


def _move(
    conn: Connection,
    content_id: str,
    user: dict,
    to: Status,
    action: str,
    comment: str | None = None,
) -> dict:
    actor = ROLE_FROM_APP.get(user["role"])
    if actor is None:
        raise HTTPException(status_code=403, detail="Your role cannot change content status")

    with conn.transaction():
        row = conn.execute(
            "SELECT status, owner_id FROM content WHERE id = %s FOR UPDATE",
            (content_id,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Content not found")

        current = STATUS_FROM_DB.get(row["status"])
        if current is None:
            raise HTTPException(status_code=409, detail=f"Unknown status '{row['status']}'")

        if actor is Role.CREATOR and row["owner_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Only the content owner can do this")

        try:
            check_transition(current, to, actor, comment=comment)
        except InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except Forbidden as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        if to is Status.APPROVED:
            count_row = conn.execute(
                "SELECT COUNT(*) AS n FROM findings "
                "WHERE content_id = %s AND status = 'open' AND severity = 'critical'",
                (content_id,),
            ).fetchone()
            open_critical = int(count_row["n"]) if count_row else 0
            if open_critical:
                raise HTTPException(
                    status_code=409,
                    detail=f"{open_critical} open critical finding(s) must be resolved before approval",
                )

        stamp = STAMP_COLUMN.get(to)
        stamp_sql = f", {stamp} = now()" if stamp else ""
        conn.execute(
            f"UPDATE content SET status = %s, updated_at = now(){stamp_sql} WHERE id = %s",
            (DB_STATUS[to], content_id),
        )

        version_row = conn.execute(
            "SELECT COALESCE(MAX(version), 1) AS v FROM content_versions WHERE content_id = %s",
            (content_id,),
        ).fetchone()
        detail = comment.strip() if comment and comment.strip() else action.replace("_", " ")
        conn.execute(
            """
            INSERT INTO revisions (
                id, content_id, actor_id, actor_label, kind, action, detail,
                from_status, to_status, version, created_at
            ) VALUES (%s, %s, %s, %s, 'person', %s, %s, %s, %s, %s, now())
            """,
            (
                "rev_" + uuid4().hex[:12], content_id, user["id"], user["name"],
                action, detail, DB_STATUS[current], DB_STATUS[to],
                int(version_row["v"]),
            ),
        )

    return {"id": content_id, "status": DB_STATUS[to]}


@router.post("/{content_id}/submit")
def submit_for_review(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Creator sends checked or fixed content to review."""
    return _move(conn, content_id, user, Status.IN_REVIEW, "submitted")


@router.post("/{content_id}/start-fixing")
def start_fixing(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Creator starts working on changes requested by a reviewer, or on revalidation items."""
    return _move(conn, content_id, user, Status.FIXING, "fixing_started")


@router.post("/{content_id}/approve")
def approve_content(
    content_id: str,
    body: CommentBody | None = None,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Reviewer or manager approves content that is In Review."""
    comment = body.comment if body else None
    return _move(conn, content_id, user, Status.APPROVED, "approved", comment)


@router.post("/{content_id}/request-changes")
def request_changes(
    content_id: str,
    body: CommentBody,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Reviewer or manager sends content back. A comment is required."""
    return _move(conn, content_id, user, Status.CHANGES_REQUESTED, "changes_requested", body.comment)


@router.post("/{content_id}/publish")
def publish_content(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Publish approved content. Not allowed before approval."""
    return _move(conn, content_id, user, Status.PUBLISHED, "published")
