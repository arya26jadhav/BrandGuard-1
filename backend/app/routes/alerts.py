"""Alerts endpoints for BrandGuard.

Alerts notify content owners when approved facts or guidelines change,
linking to the published content that needs revalidation.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from psycopg import Connection
from pydantic import BaseModel

from app.db import get_conn
from app.security import current_user

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

AlertStatus = Literal["open", "updated", "dismissed"]
AlertUpdateStatus = Literal["updated", "dismissed"]


class AlertPatch(BaseModel):
    status: AlertUpdateStatus


def _to_alert(row: dict) -> dict:
    created = row["created_at"]
    return {
        "id": row["id"],
        "contentId": row["content_id"],
        "title": row["title"],
        "reason": row["reason"] or "",
        "priority": row["priority"],
        "status": row["status"],
        "oldValue": row["old_value"],
        "newValue": row["new_value"],
        "createdAt": created.isoformat() if hasattr(created, "isoformat") else str(created),
    }


@router.get("")
def list_alerts(
    status: AlertStatus | None = Query(default=None),
    conn: Connection = Depends(get_conn),
    _user: dict = Depends(current_user),
) -> list[dict]:
    """List alerts, optionally filtered by status (open, updated, dismissed)."""
    sql = """
        SELECT id, recipient_id, content_id, source_id, source_version,
               priority, status, title, reason, old_value, new_value,
               created_at
        FROM alerts
    """
    params: tuple = ()
    if status is not None:
        sql += " WHERE status = %s"
        params = (status,)
    sql += " ORDER BY created_at DESC, id"

    rows = conn.execute(sql, params).fetchall()
    return [_to_alert(row) for row in rows]


@router.patch("/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertPatch,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Update alert status to 'updated' or 'dismissed'.

    Only the alert recipient or an admin may perform this action.
    """
    with conn.transaction():
        row = conn.execute(
            """
            SELECT id, recipient_id, content_id, source_id, source_version,
                   priority, status, title, reason, old_value, new_value,
                   created_at
            FROM alerts
            WHERE id = %s
            FOR UPDATE
            """,
            (alert_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Authorization: only the recipient or an admin may update
        if user["role"] != "admin" and row["recipient_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient or an admin may update this alert",
            )

        conn.execute(
            """
            UPDATE alerts
            SET status = %s, updated_at = now()
            WHERE id = %s
            """,
            (payload.status, alert_id),
        )

        row["status"] = payload.status
        return _to_alert(row)

