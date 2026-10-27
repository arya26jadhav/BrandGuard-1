"""Review and approval moves (plan section 6, stages 6 and 7).

Every move goes through services/workflow.py, which holds the allowed
(from, to, role) table. Each move writes a revision row, so the history shows
who did what and when. Comments on a draft are stored in the comments table.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from pydantic import BaseModel, Field

from app.db import get_conn
from app.schemas import CommentCreate
from app.security import current_user, require_role
from app.services.workflow import Forbidden, InvalidTransition, Role, Status, check_transition

router = APIRouter(prefix="/api/content", tags=["workflow"])

# Column set when a move reaches a given status. Values are fixed here, never from user input.
TIMESTAMP_COLUMN = {
    Status.IN_REVIEW: "submitted_at",
    Status.APPROVED: "approved_at",
    Status.PUBLISHED: "published_at",
}


class ChangesRequest(BaseModel):
    comment: str = Field(min_length=1, max_length=5000)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _load_for_update(conn: Connection, content_id: str) -> dict:
    row = conn.execute(
        "SELECT id, title, owner_id, status FROM content WHERE id = %s FOR UPDATE",
        (content_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    return row


def _ensure_can_view(row: dict, user: dict) -> None:
    if user["role"] == "creator" and row["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only access your own content")


def _ensure_owner(row: dict, user: dict) -> None:
    if row["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only change your own content")


def _move(
    conn: Connection,
    row: dict,
    to_status: Status,
    user: dict,
    action: str,
    detail: str,
    comment: str | None = None,
) -> None:
    """Check the move against the state machine, then update content and write a revision."""
    current = Status(row["status"])
    try:
        check_transition(current, to_status, Role(user["role"]), comment)
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Forbidden as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    timestamp = TIMESTAMP_COLUMN.get(to_status)
    extra = f", {timestamp} = now()" if timestamp else ""
    conn.execute(
        f"UPDATE content SET status = %s, updated_at = now(){extra} WHERE id = %s",
        (to_status.value, row["id"]),
    )
    conn.execute(
        """
        INSERT INTO revisions
            (id, content_id, actor_id, actor_label, kind, action, detail,
             from_status, to_status, version)
        VALUES (%s, %s, %s, %s, 'person', %s, %s, %s, %s, NULL)
        """,
        (
            _new_id("rev"), row["id"], user["id"], user["name"], action, detail,
            current.value, to_status.value,
        ),
    )
    row["status"] = to_status.value


def _add_comment(
    conn: Connection,
    content_id: str,
    author_id: str,
    body: str,
    comment_type: str,
    finding_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO comments (id, content_id, author_id, finding_id, body, comment_type)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (_new_id("cmt"), content_id, author_id, finding_id, body, comment_type),
    )


def _result(row: dict) -> dict:
    return {"id": row["id"], "status": row["status"]}


@router.post("/{content_id}/submit")
def submit_for_review(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(require_role("creator")),
) -> dict:
    with conn.transaction():
        row = _load_for_update(conn, content_id)
        _ensure_owner(row, user)

        if row["status"] == Status.DRAFT.value:
            raise HTTPException(status_code=409, detail="Run the brand check before submitting.")

        open_critical = conn.execute(
            """
            SELECT COUNT(*) AS n FROM findings
            WHERE content_id = %s AND status = 'open' AND severity = 'critical'
              AND check_run_id = (
                  SELECT id FROM check_runs WHERE content_id = %s
                  ORDER BY started_at DESC LIMIT 1
              )
            """,
            (content_id, content_id),
        ).fetchone()["n"]
        if open_critical:
            raise HTTPException(
                status_code=409,
                detail=f"Resolve {open_critical} critical finding{'s' if open_critical != 1 else ''} before submitting.",
            )

        if row["status"] == Status.CHANGES_REQUESTED.value:
            _move(conn, row, Status.FIXING, user, "fixing",
                  "Creator started fixes after changes were requested")
        _move(conn, row, Status.IN_REVIEW, user, "submitted", "Submitted for review")
    return _result(row)


@router.post("/{content_id}/approve")
def approve_content(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(require_role("reviewer", "manager")),
) -> dict:
    with conn.transaction():
        row = _load_for_update(conn, content_id)
        if row["owner_id"] == user["id"]:
            raise HTTPException(status_code=403, detail="You cannot approve your own content")
        _move(conn, row, Status.APPROVED, user, "approved", "Approved for publication")
    return _result(row)


@router.post("/{content_id}/request-changes")
def request_changes(
    content_id: str,
    payload: ChangesRequest,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(require_role("reviewer", "manager")),
) -> dict:
    comment = payload.comment.strip()
    with conn.transaction():
        row = _load_for_update(conn, content_id)
        if row["owner_id"] == user["id"]:
            raise HTTPException(status_code=403, detail="You cannot send back your own content")
        _move(conn, row, Status.CHANGES_REQUESTED, user, "changes requested",
              comment[:200], comment=comment)
        _add_comment(conn, content_id, user["id"], comment, "decision")
    return _result(row)


@router.post("/{content_id}/publish")
def publish_content(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    with conn.transaction():
        row = _load_for_update(conn, content_id)
        _ensure_can_view(row, user)
        _move(conn, row, Status.PUBLISHED, user, "published", "Published")
    return _result(row)


@router.get("/{content_id}/comments")
def list_comments(
    content_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> list[dict]:
    row = conn.execute(
        "SELECT id, owner_id FROM content WHERE id = %s", (content_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    _ensure_can_view(row, user)
    rows = conn.execute(
        """
        SELECT c.id, c.body, c.author_id, u.name AS author_name,
               c.comment_type, c.finding_id, c.created_at
        FROM comments c
        JOIN users u ON u.id = c.author_id
        WHERE c.content_id = %s
        ORDER BY c.created_at
        """,
        (content_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "body": r["body"],
            "authorId": r["author_id"],
            "authorName": r["author_name"],
            "commentType": r["comment_type"],
            "findingId": r["finding_id"],
            "createdAt": r["created_at"],
        }
        for r in rows
    ]


@router.post("/{content_id}/comments", status_code=201)
def add_comment(
    content_id: str,
    payload: CommentCreate,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    row = conn.execute(
        "SELECT id, owner_id FROM content WHERE id = %s", (content_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Content not found")
    _ensure_can_view(row, user)

    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="Comment cannot be empty")
    if payload.finding_id:
        exists = conn.execute(
            "SELECT 1 FROM findings WHERE id = %s AND content_id = %s",
            (payload.finding_id, content_id),
        ).fetchone()
        if exists is None:
            raise HTTPException(status_code=422, detail="Finding does not belong to this content")

    with conn.transaction():
        _add_comment(conn, content_id, user["id"], body, "review", payload.finding_id)
    return {"ok": True}
