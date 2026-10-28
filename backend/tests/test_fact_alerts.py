"""Tests for fact change alerts endpoints (/api/alerts).

Covers:
- A user cannot read another user's alerts
- PATCH by a non-recipient returns 403
- Invalid status returns 422
- Valid PATCH to 'dismissed' (and 'updated') succeeds
- Request without Authorization header returns 401 (real current_user)
- Integration test against DATABASE_URL (skipped if unset)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import get_conn
from app.routes.fact_alerts import router
from app.security import current_user

USER_ALICE = {"id": "user-alice", "role": "creator", "name": "Alice Chen"}
USER_BOB = {"id": "user-bob", "role": "reviewer", "name": "Bob Smith"}

NOW = datetime(2026, 10, 28, 10, 0, 0, tzinfo=timezone.utc)

SAMPLE_ALERTS = [
    {
        "id": "AL-001",
        "recipient_id": "user-alice",
        "content_id": "LIV-01",
        "source_id": "F-004",
        "source_version": 2,
        "priority": "High",
        "status": "open",
        "title": "Fact F-004 changed: Face wash launch",
        "reason": "A fact used in your published post has changed.",
        "old_value": "Rs 349",
        "new_value": "Rs 399",
        "old_text": "Meet GreenGlow Tea Tree Face Wash, now Rs 349 for 100 ml.",
        "suggested_fix": "Update price to Rs 399",
        "reminder_count": 0,
        "last_reminder_at": None,
        "read_at": None,
        "created_at": NOW,
        "updated_at": NOW,
        "channel": "Instagram",
        "owner_id": "user-alice",
        "owner_name": "Alice Chen",
        "owner_initials": "AC",
    },
    {
        "id": "AL-002",
        "recipient_id": "user-bob",
        "content_id": "LIV-02",
        "source_id": "F-004",
        "source_version": 2,
        "priority": "High",
        "status": "open",
        "title": "Fact F-004 changed: Face wash price",
        "reason": "A fact used in your published post has changed.",
        "old_value": "Rs 349",
        "new_value": "Rs 399",
        "old_text": "Your favourite face wash is Rs 349 for 100 ml.",
        "suggested_fix": "Update price to Rs 399",
        "reminder_count": 1,
        "last_reminder_at": NOW,
        "read_at": NOW,
        "created_at": NOW,
        "updated_at": NOW,
        "channel": "Email",
        "owner_id": "user-bob",
        "owner_name": "Bob Smith",
        "owner_initials": "BS",
    },
]


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeAlertsConn:
    def __init__(self, alerts: list[dict]):
        self.alerts = {a["id"]: dict(a) for a in alerts}
        self.executed_queries: list[tuple[str, tuple]] = []

    def execute(self, sql: str, params: tuple = ()):
        self.executed_queries.append((sql, tuple(params)))
        sql_stripped = sql.strip().upper()

        if sql_stripped.startswith("SELECT") and "WHERE A.RECIPIENT_ID = %S" in sql_stripped:
            recipient_id = params[0]
            matching = [a for a in self.alerts.values() if a["recipient_id"] == recipient_id]
            return FakeResult(rows=matching)

        if sql_stripped.startswith("SELECT") and "WHERE A.ID = %S" in sql_stripped:
            alert_id = params[0]
            row = self.alerts.get(alert_id)
            return FakeResult(row=row)

        if sql_stripped.startswith("UPDATE ALERTS"):
            new_status, alert_id = params[0], params[1]
            if alert_id in self.alerts:
                self.alerts[alert_id]["status"] = new_status
            return FakeResult()

        return FakeResult()


def make_client(user: dict, conn: FakeAlertsConn) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[current_user] = lambda: user
    app.dependency_overrides[get_conn] = lambda: conn
    return TestClient(app)


def test_user_cannot_read_another_users_alerts():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    client_alice = make_client(USER_ALICE, conn)
    client_bob = make_client(USER_BOB, conn)

    # Alice fetches her alerts
    res_alice = client_alice.get("/api/alerts")
    assert res_alice.status_code == 200
    data_alice = res_alice.json()
    assert len(data_alice) == 1
    assert data_alice[0]["id"] == "AL-001"
    # Ensure Bob's alert is not included
    assert all(a["id"] != "AL-002" for a in data_alice)

    # Bob fetches his alerts
    res_bob = client_bob.get("/api/alerts")
    assert res_bob.status_code == 200
    data_bob = res_bob.json()
    assert len(data_bob) == 1
    assert data_bob[0]["id"] == "AL-002"
    # Ensure Alice's alert is not included
    assert all(a["id"] != "AL-001" for a in data_bob)

    # Verify SQL query filtered by recipient_id
    recipient_queries = [
        p for sql, p in conn.executed_queries
        if "WHERE a.recipient_id = %s" in sql
    ]
    assert len(recipient_queries) == 2
    assert recipient_queries[0] == ("user-alice",)
    assert recipient_queries[1] == ("user-bob",)


def test_patch_by_non_recipient_returns_403():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    # AL-001 belongs to Alice; Bob attempts to patch it
    client_bob = make_client(USER_BOB, conn)

    res = client_bob.patch("/api/alerts/AL-001", json={"status": "dismissed"})
    assert res.status_code == 403
    assert "permission" in res.json()["detail"].lower()
    # Confirm DB status did not change
    assert conn.alerts["AL-001"]["status"] == "open"


def test_patch_invalid_status_returns_422():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    client_alice = make_client(USER_ALICE, conn)

    # Status 'open' is valid in schema but rejected by PATCH /api/alerts/{alert_id}
    res_open = client_alice.patch("/api/alerts/AL-001", json={"status": "open"})
    assert res_open.status_code == 422

    # Completely invalid status
    res_invalid = client_alice.patch("/api/alerts/AL-001", json={"status": "resolved"})
    assert res_invalid.status_code == 422

    # Another disallowed status
    res_other = client_alice.patch("/api/alerts/AL-001", json={"status": "closed"})
    assert res_other.status_code == 422


def test_patch_valid_dismissed_succeeds():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    client_alice = make_client(USER_ALICE, conn)

    res = client_alice.patch("/api/alerts/AL-001", json={"status": "dismissed"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "AL-001"
    assert data["status"] == "dismissed"
    # Verify underlying DB status was updated
    assert conn.alerts["AL-001"]["status"] == "dismissed"


def test_patch_valid_updated_succeeds():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    client_alice = make_client(USER_ALICE, conn)

    res = client_alice.patch("/api/alerts/AL-001", json={"status": "updated"})
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "AL-001"
    assert data["status"] == "updated"
    assert conn.alerts["AL-001"]["status"] == "updated"


def test_patch_nonexistent_alert_returns_404():
    conn = FakeAlertsConn(SAMPLE_ALERTS)
    client_alice = make_client(USER_ALICE, conn)

    res = client_alice.patch("/api/alerts/AL-NONEXISTENT", json={"status": "dismissed"})
    assert res.status_code == 404


def test_request_without_auth_header_returns_401():
    """Verify that omitting the Authorization header triggers 401 via real current_user."""
    app = FastAPI()
    app.include_router(router)
    # Real current_user is used (no dependency override)
    app.dependency_overrides[get_conn] = lambda: FakeAlertsConn([])
    client = TestClient(app)

    res = client.get("/api/alerts")
    assert res.status_code == 401
    assert "authentication required" in res.json()["detail"].lower()


@pytest.mark.integration
def test_integration_alerts_against_db():
    """Runs against DATABASE_URL from app.config. Skips if DATABASE_URL is unset."""
    try:
        settings = get_settings()
        db_url = settings.database_url
    except Exception:
        db_url = os.getenv("DATABASE_URL")

    if not db_url:
        pytest.skip("DATABASE_URL is unset")

    import psycopg
    from psycopg.rows import dict_row

    test_alert_id = f"AL-test-{uuid.uuid4()}"
    init_conn = None

    try:
        init_conn = psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10)
    except Exception as exc:
        pytest.skip(f"Could not connect to DATABASE_URL: {exc}")

    try:
        # 1. Insert seed data with fresh connection and commit
        with init_conn.transaction():
            init_conn.execute(
                """
                INSERT INTO users (id, name, email, role, team)
                VALUES ('user-alice', 'Alice Chen', 'alice@example.com', 'creator', 'Marketing'),
                       ('user-bob', 'Bob Smith', 'bob@example.com', 'reviewer', 'Sales')
                ON CONFLICT (id) DO NOTHING
                """
            )
            init_conn.execute(
                """
                INSERT INTO alerts
                    (id, recipient_id, source_id, source_version, priority,
                     status, title, reason, old_value, new_value, old_text, suggested_fix)
                VALUES (%s, 'user-alice', 'F-001', 1, 'High',
                        'open', 'Integration Test Alert', 'Testing DB integration',
                        'old', 'new', 'old text', 'new fix')
                """,
                (test_alert_id,),
            )
        init_conn.close()
        init_conn = None

        # 2. Override get_conn so each request opens its own connection and closes it
        def _override_get_conn():
            req_conn = psycopg.connect(db_url, row_factory=dict_row, connect_timeout=10)
            try:
                yield req_conn
            finally:
                req_conn.close()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_conn] = _override_get_conn

        # Alice can GET the alert
        app.dependency_overrides[current_user] = lambda: USER_ALICE
        client_alice = TestClient(app)
        res_alice = client_alice.get("/api/alerts", timeout=10.0)
        assert res_alice.status_code == 200
        alerts = res_alice.json()
        assert any(a["id"] == test_alert_id for a in alerts)

        # Bob tries to PATCH Alice's alert -> 403 Forbidden
        app.dependency_overrides[current_user] = lambda: USER_BOB
        client_bob = TestClient(app)
        res_bob_patch = client_bob.patch(
            f"/api/alerts/{test_alert_id}", json={"status": "dismissed"}, timeout=10.0
        )
        assert res_bob_patch.status_code == 403

        # Alice can PATCH the alert to dismissed -> 200 OK
        app.dependency_overrides[current_user] = lambda: USER_ALICE
        res_alice_patch = client_alice.patch(
            f"/api/alerts/{test_alert_id}", json={"status": "dismissed"}, timeout=10.0
        )
        assert res_alice_patch.status_code == 200
        assert res_alice_patch.json()["status"] == "dismissed"

    finally:
        # 4. Clean up test rows and close connection
        if init_conn is not None and not init_conn.closed:
            init_conn.close()
        try:
            with psycopg.connect(db_url, connect_timeout=10) as cleanup_conn:
                cleanup_conn.execute("DELETE FROM alerts WHERE id = %s", (test_alert_id,))
                cleanup_conn.commit()
        except Exception as exc:
            print(f"Failed to cleanup test alert {test_alert_id}: {exc}")
