"""Comments endpoints for content items.

The workflow approval moves (submit, approve, request-changes, publish, start-fixing)
live in app/routes/approval.py. This module provides only the comments CRUD,
which is used by the ReviewQueuePage to let reviewers leave notes on a draft.
"""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.db import get_conn
from app.schemas import CommentCreate
from app.security import current_user

router = APIRouter(prefix="/api/content", tags=["workflow"])


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _ensure_can_view(row: dict, user: dict) -> None:
    if user["role"] == "creator" and row["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="You can only access your own content")


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
