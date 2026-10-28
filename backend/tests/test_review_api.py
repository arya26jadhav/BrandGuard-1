"""Integration-style tests for /api/review/summary and /api/review/queue.

Both endpoints require a valid Bearer token; the tests override the
current_user dependency so no real database or JWT is needed.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.review import QUEUE_STATUSES, router
from app.security import current_user

REVIEWER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}


def _app(fake_pool) -> FastAPI:
    """Build a minimal FastAPI app with the review router and a stubbed auth."""
    application = FastAPI()
    application.include_router(router)
    application.state.db_pool = fake_pool
    # Override auth so tests do not need a real JWT
    application.dependency_overrides[current_user] = lambda: REVIEWER
    return application


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class SummaryFakeConn:
    def execute(self, sql, params=()):
        return FakeResult(row={"pending_review": 4, "changes_requested": 2})


class QueueFakeConn:
    """Returns two queue items and records the status list passed to the query."""

    NOW = datetime(2026, 10, 27, 12, 0, 0, tzinfo=timezone.utc)

    def __init__(self):
        self.last_params = None

    def execute(self, sql, params=()):
        self.last_params = params
        rows = [
            {
                "id": "cnt_aaa",
                "title": "Face wash launch",
                "channel": "Instagram",
                "status": "In Review",
                "updated_at": self.NOW,
                "submitted_at": self.NOW,
                "owner_name": "Maya Chen",
                "open_findings": 2,
            },
            {
                "id": "cnt_bbb",
                "title": "Sunscreen ad copy",
                "channel": "Ad",
                "status": "Changes requested",
                "updated_at": self.NOW,
                "submitted_at": None,
                "owner_name": "Jordan Lee",
                "open_findings": 0,
            },
        ]
        return FakeResult(rows=rows)


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self):
        yield self._conn


# ---------------------------------------------------------------------------
# /summary tests
# ---------------------------------------------------------------------------

def test_summary_shape():
    app = _app(FakePool(SummaryFakeConn()))
    res = TestClient(app).get("/api/review/summary")
    assert res.status_code == 200
    assert res.json() == {"pendingReview": 4, "changesRequested": 2}


def test_summary_requires_auth():
    """Without the override the endpoint must reject an unauthenticated request."""
    application = FastAPI()
    application.include_router(router)
    application.state.db_pool = FakePool(SummaryFakeConn())
    # No dependency override – no token sent
    res = TestClient(application).get("/api/review/summary")
    assert res.status_code == 401


# ---------------------------------------------------------------------------
# /queue tests
# ---------------------------------------------------------------------------

def test_queue_returns_list():
    conn = QueueFakeConn()
    app = _app(FakePool(conn))
    res = TestClient(app).get("/api/review/queue")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_queue_item_shape():
    app = _app(FakePool(QueueFakeConn()))
    data = TestClient(app).get("/api/review/queue").json()
    item = data[0]
    for key in ("id", "title", "channel", "status", "ownerName", "updatedAt", "submittedAt", "openFindings"):
        assert key in item, f"missing key: {key}"
    assert item["id"] == "cnt_aaa"
    assert item["ownerName"] == "Maya Chen"
    assert item["openFindings"] == 2


def test_queue_submitted_at_null_is_none():
    app = _app(FakePool(QueueFakeConn()))
    data = TestClient(app).get("/api/review/queue").json()
    item_no_submit = next(d for d in data if d["id"] == "cnt_bbb")
    assert item_no_submit["submittedAt"] is None


def test_queue_passes_all_queue_statuses():
    """The SQL query must filter by all four QUEUE_STATUSES."""
    conn = QueueFakeConn()
    app = _app(FakePool(conn))
    TestClient(app).get("/api/review/queue")
    # params[0] is the list passed to ANY(%s)
    assert conn.last_params is not None
    statuses_sent = list(conn.last_params[0])
    for status in QUEUE_STATUSES:
        assert status in statuses_sent, f"status '{status}' not passed to query"


def test_queue_requires_auth():
    """Without the override the endpoint must reject an unauthenticated request."""
    application = FastAPI()
    application.include_router(router)
    application.state.db_pool = FakePool(QueueFakeConn())
    res = TestClient(application).get("/api/review/queue")
    assert res.status_code == 401
