"""Routing for a submission held because it may contain a confidential term (plan section 9).

Called by the reading pipeline when the pre-scan finds a term. Runs before any model call, and
inside the caller's transaction. It writes:

- the held attachments (read_status held, the warning text, extracted text cleared),
- the content moved to "In Review", assigned to a manager (or an admin if no manager exists),
- one check run and one security finding, with no term text,
- one manager alert (alerts.kind = 'confidential_review'),
- one audit row in revisions.

Nothing here stores or returns the term. The creator only ever sees HOLD_MESSAGE.
"""
from __future__ import annotations

from uuid import uuid4

from psycopg import Connection
from psycopg.types.json import Jsonb

HOLD_MESSAGE = (
    "This file was held for manager review because it may contain internal information. "
    "A manager will contact you."
)
SECURITY_SOURCE = "confidential-terms"
FINDING_TITLE = "Confidential term detected"
FINDING_REASON = (
    "A confidential term was found in this submission before any AI check. "
    "No AI check was run. A manager should review the submission."
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def pick_reviewer(conn: Connection) -> str | None:
    """A manager if one exists, otherwise an admin, otherwise None."""
    for role in ("manager", "admin"):
        row = conn.execute(
            "SELECT id FROM users WHERE role = %s ORDER BY id LIMIT 1", (role,)
        ).fetchone()
        if row is not None:
            return row["id"]
    return None


def hold_submission(
    conn: Connection,
    *,
    content_id: str,
    attachment_ids: list[str],
) -> dict:
    """Apply the hold. Call inside a transaction. Returns the routing summary for the response."""
    reviewer_id = pick_reviewer(conn)

    if attachment_ids:
        conn.execute(
            """
            UPDATE content_attachments
               SET read_status = 'held', read_message = %s,
                   extracted_text = '', visual_facts = '[]'::jsonb
             WHERE content_id = %s AND id = ANY(%s)
            """,
            (HOLD_MESSAGE, content_id, attachment_ids),
        )

    conn.execute(
        """
        UPDATE content
           SET status = 'In Review', assigned_reviewer_id = %s, updated_at = now()
         WHERE id = %s
        """,
        (reviewer_id, content_id),
    )

    check_run_id = _new_id("chk")
    conn.execute(
        """
        INSERT INTO check_runs
            (id, content_id, started_at, finished_at, rules_count, ai_count,
             rules_only_fallback, metadata)
        VALUES (%s, %s, now(), now(), 0, 0, FALSE, %s)
        """,
        (check_run_id, content_id, Jsonb({"aiStatus": "held", "reason": "confidential_term"})),
    )

    finding_id = _new_id("fnd")
    conn.execute(
        """
        INSERT INTO findings (
            id, content_id, check_run_id, type, start, "end", bbox,
            severity, title, reason, source_id, source_version, guideline_id,
            suggested_fix, original_text, confidence, ai_generated,
            needs_human_review, status, suggestion_kind
        ) VALUES (
            %s, %s, %s, 'security', NULL, NULL, NULL,
            'critical', %s, %s, %s, 1, NULL,
            '', NULL, 1.0, FALSE,
            TRUE, 'open', 'Terminology change'
        )
        """,
        (finding_id, content_id, check_run_id, FINDING_TITLE, FINDING_REASON, SECURITY_SOURCE),
    )
    for attachment_id in attachment_ids:
        conn.execute(
            "INSERT INTO finding_attachments (finding_id, attachment_id) VALUES (%s, %s)",
            (finding_id, attachment_id),
        )

    alert_id = None
    if reviewer_id is not None:
        alert_id = _new_id("alt")
        conn.execute(
            """
            INSERT INTO alerts
                (id, recipient_id, content_id, source_id, source_version, priority, status,
                 title, reason, kind)
            VALUES (%s, %s, %s, %s, 1, 'High', 'open', %s, %s, 'confidential_review')
            """,
            (
                alert_id, reviewer_id, content_id, SECURITY_SOURCE,
                "Submission held for review",
                "A file was held before any AI check. Review it in the queue.",
            ),
        )

    conn.execute(
        """
        INSERT INTO revisions (id, content_id, actor_id, actor_label, kind, action, detail)
        VALUES (%s, %s, NULL, 'BrandGuard', 'ai', 'Held for manager review',
                'Confidential term detected before any AI check')
        """,
        (_new_id("rev"), content_id),
    )

    return {
        "reason": "confidential_term",
        "routedTo": "manager",
        "message": HOLD_MESSAGE,
        "reviewerId": reviewer_id,
        "alertId": alert_id,
        "checkRunId": check_run_id,
    }
