"""Tests for GET /api/alerts and PATCH /api/alerts/{id}."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.alerts import router
from app.security import current_user

USER_RECIPIENT = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}
USER_OTHER = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}
USER_ADMIN = {"id": "user-admin", "role": "admin", "name": "Alex Morgan"}


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeAlertsConn:
    NOW = datetime(2026, 10, 28, 14, 0, 0, tzinfo=timezone.utc)

    def __init__(self, alerts=None):
        self.alerts = alerts or [
            {
                "id": "AL-001",
                "recipient_id": "user-reviewer",
                "content_id": "LIV-02",
                "source_id": "F-004",
                "source_version": 2,
                "priority": "High",
                "status": "open",
                "title": "Face wash price changed",
                "reason": "Price changed from Rs 349 to Rs 399",
                "old_value": "Rs 349",
                "new_value": "Rs 399",
                "created_at": self.NOW,
            },
            {
                "id": "AL-002",
                "recipient_id": "user-creator",
                "content_id": "LIV-01",
                "source_id": "F-004",
                "source_version": 2,
                "priority": "High",
                "status": "updated",
                "title": "Face wash price changed",
                "reason": "Price changed from Rs 349 to Rs 399",
                "old_value": "Rs 349",
                "new_value": "Rs 399",
                "created_at": self.NOW,
            },
        ]
        self.last_sql = ""
        self.last_params = ()

    def transaction(self):
        return FakeTransaction()

    def execute(self, sql, params=()):
        self.last_sql = sql
        self.last_params = params

        if "SELECT" in sql and "WHERE status = %s" in sql:
            filtered = [a for a in self.alerts if a["status"] == params[0]]
            return FakeResult(rows=filtered)
        if "SELECT" in sql and "WHERE id = %s" in sql:
            match = next((a for a in self.alerts if a["id"] == params[0]), None)
            return FakeResult(row=dict(match) if match else None)
        if "SELECT" in sql:
            return FakeResult(rows=self.alerts)
        if "UPDATE alerts" in sql:
            for a in self.alerts:
                if a["id"] == params[1]:
                    a["status"] = params[0]
            return FakeResult()
        return FakeResult()


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self):
        yield self._conn


def _app(conn, auth_user=USER_RECIPIENT) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.db_pool = FakePool(conn)
    if auth_user:
        app.dependency_overrides[current_user] = lambda: auth_user
    return app


def test_alerts_list_requires_auth():
    app = _app(FakeAlertsConn(), auth_user=None)
    res = TestClient(app).get("/api/alerts")
    assert res.status_code == 401


def test_alerts_list_returns_camel_case_shape():
    app = _app(FakeAlertsConn())
    res = TestClient(app).get("/api/alerts")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    item = data[0]
    expected_keys = {
        "id", "contentId", "title", "reason", "priority",
        "status", "oldValue", "newValue", "createdAt",
    }
    assert expected_keys.issubset(item.keys())
    assert item["id"] == "AL-001"
    assert item["contentId"] == "LIV-02"
    assert item["status"] == "open"


def test_alerts_list_filters_by_status():
    conn = FakeAlertsConn()
    app = _app(conn)
    res = TestClient(app).get("/api/alerts?status=open")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "open"


def test_alerts_patch_requires_auth():
    app = _app(FakeAlertsConn(), auth_user=None)
    res = TestClient(app).patch("/api/alerts/AL-001", json={"status": "updated"})
    assert res.status_code == 401


def test_alerts_patch_unknown_id_is_404():
    app = _app(FakeAlertsConn())
    res = TestClient(app).patch("/api/alerts/AL-UNKNOWN", json={"status": "updated"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Alert not found"


def test_alerts_patch_invalid_status_is_422():
    app = _app(FakeAlertsConn())
    # "open" is not allowed in PATCH; only "updated" or "dismissed"
    res = TestClient(app).patch("/api/alerts/AL-001", json={"status": "open"})
    assert res.status_code == 422

    res_invalid = TestClient(app).patch("/api/alerts/AL-001", json={"status": "random"})
    assert res_invalid.status_code == 422


def test_alerts_patch_by_non_recipient_non_admin_is_403():
    conn = FakeAlertsConn()
    # AL-001 recipient is user-reviewer; USER_OTHER is user-creator
    app = _app(conn, auth_user=USER_OTHER)
    res = TestClient(app).patch("/api/alerts/AL-001", json={"status": "updated"})
    assert res.status_code == 403
    assert "Only the recipient or an admin" in res.json()["detail"]


def test_alerts_patch_by_recipient_succeeds():
    conn = FakeAlertsConn()
    app = _app(conn, auth_user=USER_RECIPIENT)
    res = TestClient(app).patch("/api/alerts/AL-001", json={"status": "updated"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "AL-001"
    assert data["status"] == "updated"


def test_alerts_patch_by_admin_succeeds_even_if_not_recipient():
    conn = FakeAlertsConn()
    app = _app(conn, auth_user=USER_ADMIN)
    res = TestClient(app).patch("/api/alerts/AL-001", json={"status": "dismissed"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "AL-001"
    assert data["status"] == "dismissed"

