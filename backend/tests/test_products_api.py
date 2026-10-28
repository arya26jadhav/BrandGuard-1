"""Tests for GET /api/knowledge/products."""
from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.knowledge import router
from app.security import current_user

USER_CREATOR = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}


class FakeResult:
    def __init__(self, rows=None):
        self._rows = rows or []

    def fetchall(self):
        return self._rows


class FakeConn:
    def __init__(self, products=None):
        self.products = products or [
            {
                "id": "P-001",
                "name": "GreenGlow Tea Tree Face Wash",
                "approved_name": "GreenGlow Tea Tree Face Wash",
                "category": "skincare",
                "is_released": True,
            },
            {
                "id": "P-002",
                "name": "Unreleased Serum",
                "approved_name": "GreenGlow Serum",
                "category": "treatments",
                "is_released": False,
            },
        ]

    def execute(self, sql, params=()):
        return FakeResult(rows=self.products)


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


def test_products_requires_auth():
    app = _app(FakeConn(), auth_user=None)
    res = TestClient(app).get("/api/knowledge/products")
    assert res.status_code == 401


def test_products_returns_shape_for_logged_in_user():
    app = _app(FakeConn())
    res = TestClient(app).get("/api/knowledge/products")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2

    p1 = data[0]
    assert p1 == {
        "id": "P-001",
        "name": "GreenGlow Tea Tree Face Wash",
        "line": "skincare",
        "status": "Active",
    }

    p2 = data[1]
    assert p2 == {
        "id": "P-002",
        "name": "GreenGlow Serum",
        "line": "treatments",
        "status": "Inactive",
    }


def test_products_accessible_by_reviewer_and_admin():
    for role in ("reviewer", "manager", "admin"):
        user = {"id": f"user-{role}", "role": role, "name": f"Test {role}"}
        app = _app(FakeConn(), auth_user=user)
        res = TestClient(app).get("/api/knowledge/products")
        assert res.status_code == 200
        assert len(res.json()) == 2
