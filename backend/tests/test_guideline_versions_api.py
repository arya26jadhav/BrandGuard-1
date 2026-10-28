"""Tests for GET /api/knowledge/guidelines/{guideline_id}/versions."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.knowledge import router
from app.security import current_user

USER_CREATOR = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, exists=True, versions=None):
        self.exists = exists
        self.versions = versions or []

    def execute(self, sql, params=()):
        if "FROM guidelines WHERE id" in sql:
            if not self.exists:
                return FakeResult(row=None)
            return FakeResult(row={"id": params[0]})
        if "FROM guideline_versions" in sql:
            return FakeResult(rows=self.versions)
        return FakeResult()


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self):
        yield self._conn


def _app(conn, auth_user=USER_CREATOR) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.db_pool = FakePool(conn)
    if auth_user:
        app.dependency_overrides[current_user] = lambda: auth_user
    return app


def test_guideline_versions_requires_auth():
    app = _app(FakeConn(exists=True), auth_user=None)
    res = TestClient(app).get("/api/knowledge/guidelines/G-001/versions")
    assert res.status_code == 401


def test_guideline_versions_unknown_guideline_returns_404():
    app = _app(FakeConn(exists=False))
    res = TestClient(app).get("/api/knowledge/guidelines/G-UNKNOWN/versions")
    assert res.status_code == 404
    assert res.json()["detail"] == "Guideline not found"


def test_guideline_versions_empty_list_when_none():
    app = _app(FakeConn(exists=True, versions=[]))
    res = TestClient(app).get("/api/knowledge/guidelines/G-001/versions")
    assert res.status_code == 200
    assert res.json() == []


def test_guideline_versions_returns_versions_newest_first():
    now = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
    versions = [
        {
            "guideline_id": "G-001",
            "version": 2,
            "text": "Updated policy text",
            "changed_by": "user-manager",
            "changed_by_name": "Jordan Lee",
            "change_note": "Tightened wording",
            "changed_at": now,
        },
        {
            "guideline_id": "G-001",
            "version": 1,
            "text": "Original policy text",
            "changed_by": "user-admin",
            "changed_by_name": "Alex Morgan",
            "change_note": "Initial baseline",
            "changed_at": now,
        },
    ]
    app = _app(FakeConn(exists=True, versions=versions))
    res = TestClient(app).get("/api/knowledge/guidelines/G-001/versions")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["version"] == 2
    assert data[0]["text"] == "Updated policy text"
    assert data[0]["changedBy"] == "user-manager"
    assert data[0]["changedByName"] == "Jordan Lee"
    assert data[0]["changeNote"] == "Tightened wording"
    assert data[1]["version"] == 1
