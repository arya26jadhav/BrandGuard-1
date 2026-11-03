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
    status: AlertUpdateStatus | None = None
    read: bool | None = None


def _to_alert(row: dict) -> dict:
    created = row["created_at"]
    read_at = row.get("read_at")
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
        "read": read_at is not None,
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
               created_at, read_at
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
                   created_at, read_at
            FROM alerts
            WHERE id = %s
            FOR UPDATE
            """,
            (alert_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Alert not found")

        # Authorization: recipient, reviewer, or admin may update
        if user["role"] not in ("admin", "reviewer") and row["recipient_id"] != user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the recipient or an admin may update this alert",
            )

        # Build dynamic SET clause
        set_parts = ["updated_at = now()"]
        set_vals: list = []
        if payload.status is not None:
            set_parts.append("status = %s")
            set_vals.append(payload.status)
        if payload.read is True:
            set_parts.append("read_at = now()")
        elif payload.read is False:
            set_parts.append("read_at = NULL")
        if len(set_parts) == 1:
            raise HTTPException(status_code=400, detail="Nothing to update")
        set_vals.append(alert_id)
        conn.execute(
            f"UPDATE alerts SET {', '.join(set_parts)} WHERE id = %s",
            set_vals,
        )

        if payload.status is not None:
            row["status"] = payload.status
        if payload.read is True:
            from datetime import datetime, timezone
            row["read_at"] = datetime.now(timezone.utc)
        elif payload.read is False:
            row["read_at"] = None
        return _to_alert(row)



@router.post("/mark-all-read")
def mark_all_read(
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    """Mark all open alerts for the current user as read."""
    conn.execute(
        """
        UPDATE alerts
        SET read_at = now(), updated_at = now()
        WHERE recipient_id = %s AND read_at IS NULL
        """,
        (user["id"],),
    )
    return {"status": "ok"}
