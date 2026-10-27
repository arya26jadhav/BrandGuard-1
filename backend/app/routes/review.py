"""Review summary counts and the reviewer queue (plan section 6)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.db import get_conn
from app.security import current_user, require_role

router = APIRouter(prefix="/api/review", tags=["review"])

QUEUE_STATUSES = ["In Review", "Changes requested", "Approved"]


@router.get("/summary")
def review_summary(
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict[str, int]:
    """Counts for the sidebar. Creators see counts for their own content only."""
    if user["role"] == "creator":
        row = conn.execute(
            """
            SELECT COUNT(*) FILTER (WHERE status = 'In Review') AS pending_review,
                   COUNT(*) FILTER (WHERE status = 'Changes requested') AS changes_requested
            FROM content WHERE owner_id = %s
            """,
            (user["id"],),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT COUNT(*) FILTER (WHERE status = 'In Review') AS pending_review,
                   COUNT(*) FILTER (WHERE status = 'Changes requested') AS changes_requested
            FROM content
            """
        ).fetchone()
    return {
        "pendingReview": row["pending_review"],
        "changesRequested": row["changes_requested"],
    }


@router.get("/queue")
def review_queue(
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(require_role("reviewer", "manager", "admin")),
) -> list[dict]:
    """Content waiting for a reviewer, with the owner name and open-finding count."""
    rows = conn.execute(
        """
        SELECT c.id, c.title, c.channel, c.status, c.updated_at, c.submitted_at,
               u.name AS owner_name,
               (SELECT COUNT(*) FROM findings f
                 WHERE f.content_id = c.id AND f.status = 'open'
                   AND f.check_run_id = (
                       SELECT r.id FROM check_runs r WHERE r.content_id = c.id
                       ORDER BY r.started_at DESC LIMIT 1
                   )) AS open_findings
        FROM content c
        JOIN users u ON u.id = c.owner_id
        WHERE c.status = ANY(%s)
        ORDER BY c.updated_at DESC
        """,
        (QUEUE_STATUSES,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "title": r["title"],
            "channel": r["channel"],
            "status": r["status"],
            "ownerName": r["owner_name"],
            "updatedAt": r["updated_at"],
            "submittedAt": r["submitted_at"],
            "openFindings": r["open_findings"],
        }
        for r in rows
    ]
