"""Fact change alerts routes (Member 3).

Endpoints:
- GET /api/alerts: retrieve alerts for current user only
- PATCH /api/alerts/{id}: update alert status ('updated' or 'dismissed' only; recipient only)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from psycopg import Connection

from app.db import get_conn
from app.schemas import AlertResponse, AlertStatusUpdate, OwnerResponse
from app.security import current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

VALID_PATCH_STATUSES = {"updated", "dismissed"}


def _row_to_alert_response(row: dict) -> AlertResponse:
    owner = None
    if row.get("owner_id"):
        owner = OwnerResponse(
            id=row["owner_id"],
            name=row["owner_name"],
            initials=row["owner_initials"],
        )

    return AlertResponse(
        id=row["id"],
        title=row["title"],
        priority=row["priority"],
        status=row["status"],
        reason=row["reason"],
        fact=row["source_id"],
        old_value=row["old_value"],
        new_value=row["new_value"],
        old_sentence=row["old_text"],
        corrected_sentence=row["suggested_fix"],
        content_id=row["content_id"],
        sent_at=row["created_at"],
        reminder_sent=row["reminder_count"],
        read=row["read_at"] is not None,
        channel=row["channel"],
        owner=owner,
    )


@router.get("", response_model=list[AlertResponse])
def get_alerts(
    conn: Annotated[Connection, Depends(get_conn)],
    user: Annotated[dict, Depends(current_user)],
) -> list[AlertResponse]:
    """Retrieve alerts for the current authenticated user only."""
    rows = conn.execute(
        """
        SELECT a.id, a.recipient_id, a.content_id, a.source_id, a.source_version,
               a.priority, a.status, a.title, a.reason,
               a.old_value, a.new_value, a.old_text, a.suggested_fix,
               a.reminder_count, a.last_reminder_at, a.read_at, a.created_at, a.updated_at,
               c.channel,
               u.id AS owner_id, u.name AS owner_name, u.initials AS owner_initials
        FROM alerts a
        LEFT JOIN content c ON c.id = a.content_id
        LEFT JOIN users u ON u.id = c.owner_id
        WHERE a.recipient_id = %s
        ORDER BY a.created_at DESC
        """,
        (user["id"],),
    ).fetchall()

    return [_row_to_alert_response(r) for r in rows]


@router.patch("/{alert_id}", response_model=AlertResponse)
def update_alert(
    alert_id: str,
    payload: AlertStatusUpdate,
    conn: Annotated[Connection, Depends(get_conn)],
    user: Annotated[dict, Depends(current_user)],
) -> AlertResponse:
    """Update alert status (recipient only; status must be 'updated' or 'dismissed')."""
    if payload.status not in VALID_PATCH_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status must be one of: {', '.join(sorted(VALID_PATCH_STATUSES))}",
        )

    alert = conn.execute(
        """
        SELECT a.id, a.recipient_id, a.content_id, a.source_id, a.source_version,
               a.priority, a.status, a.title, a.reason,
               a.old_value, a.new_value, a.old_text, a.suggested_fix,
               a.reminder_count, a.last_reminder_at, a.read_at, a.created_at, a.updated_at,
               c.channel,
               u.id AS owner_id, u.name AS owner_name, u.initials AS owner_initials
        FROM alerts a
        LEFT JOIN content c ON c.id = a.content_id
        LEFT JOIN users u ON u.id = c.owner_id
        WHERE a.id = %s
        """,
        (alert_id,),
    ).fetchone()

    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )

    if alert["recipient_id"] != user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this alert",
        )

    conn.execute(
        """
        UPDATE alerts
        SET status = %s, updated_at = now()
        WHERE id = %s
        """,
        (payload.status, alert_id),
    )

    alert["status"] = payload.status
    return _row_to_alert_response(alert)
