from fastapi import APIRouter, Depends
from psycopg import Connection

from app.db import get_conn
from app.security import current_user

router = APIRouter(prefix="/api/review", tags=["review"])

# Values must match the content.status CHECK constraint in data/schema.sql.
PENDING_REVIEW_STATUS = "In Review"
CHANGES_REQUESTED_STATUS = "Changes requested"

# Statuses visible in the review queue (reviewer/manager facing).
QUEUE_STATUSES = ("In Review", "Changes requested", "Approved", "Published")


@router.get("/summary")
def review_summary(
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(current_user),
) -> dict[str, int]:
    """Counts of content waiting for a reviewer, and content sent back for changes."""
    row = conn.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = %s) AS pending_review,
            COUNT(*) FILTER (WHERE status = %s) AS changes_requested
        FROM content
        """,
        (PENDING_REVIEW_STATUS, CHANGES_REQUESTED_STATUS),
    ).fetchone()
    return {
        "pendingReview": int(row["pending_review"]),
        "changesRequested": int(row["changes_requested"]),
    }


@router.get("/queue")
def review_queue(
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(current_user),
) -> list[dict]:
    """All content items visible in the review queue (In Review, Changes requested, Approved, Published).

    Returns the open-findings count from the most recent check run so the reviewer
    can see at a glance how many issues are still outstanding.
    """
    rows = conn.execute(
        """
        SELECT
            c.id,
            c.title,
            c.channel,
            c.status,
            c.updated_at,
            c.submitted_at,
            u.name AS owner_name,
            COALESCE(
                (
                    SELECT COUNT(*)
                    FROM findings f
                    WHERE f.content_id = c.id
                      AND f.status = 'open'
                      AND f.check_run_id = (
                          SELECT cr.id
                          FROM check_runs cr
                          WHERE cr.content_id = c.id
                          ORDER BY cr.started_at DESC
                          LIMIT 1
                      )
                ),
                0
            ) AS open_findings
        FROM content c
        LEFT JOIN users u ON u.id = c.owner_id
        WHERE c.status = ANY(%s)
        ORDER BY c.updated_at DESC, c.id
        """,
        (list(QUEUE_STATUSES),),
    ).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "channel": row["channel"],
            "status": row["status"],
            "ownerName": row["owner_name"] or "Unknown",
            "updatedAt": row["updated_at"].isoformat() if row["updated_at"] else None,
            "submittedAt": row["submitted_at"].isoformat() if row["submitted_at"] else None,
            "openFindings": int(row["open_findings"]),
        }
        for row in rows
    ]
