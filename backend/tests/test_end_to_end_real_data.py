from contextlib import contextmanager
from unittest.mock import MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.knowledge import router as knowledge_router
from app.routes.alerts import router as alerts_router
from app.security import current_user


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self):
        yield self._conn


def test_fact_impact_preview_route():
    app = FastAPI()
    app.include_router(knowledge_router)
    app.dependency_overrides[current_user] = lambda: {"id": "user-manager", "role": "manager"}

    conn = MagicMock()
    app.state.db_pool = FakePool(conn)

    # First call: SELECT statement FROM facts WHERE id = %s
    # Second call: SELECT c.id, c.title, c.channel, c.owner_id, u.name ...
    def fake_execute(sql, params=()):
        if "SELECT statement FROM facts" in sql:
            return FakeResult(row={"statement": "Old 50 SPF sunscreen"})
        if "FROM fact_content_links" in sql:
            return FakeResult(rows=[
                {
                    "id": "LIV-01",
                    "title": "Sunscreen Post",
                    "channel": "Instagram",
                    "owner_id": "user-creator",
                    "owner_name": "Maya Chen",
                }
            ])
        return FakeResult()

    conn.execute.side_effect = fake_execute

    client = TestClient(app)
    resp = client.post(
        "/api/knowledge/facts/F-005/impact-preview",
        json={"statement": "New 45 SPF sunscreen"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["factId"] == "F-005"
    assert data["oldStatement"] == "Old 50 SPF sunscreen"
    assert data["newStatement"] == "New 45 SPF sunscreen"
    assert len(data["affectedItems"]) == 1
    assert data["affectedItems"][0]["contentId"] == "LIV-01"
    assert data["affectedOwnerCount"] == 1


def test_fact_linked_content_route():
    app = FastAPI()
    app.include_router(knowledge_router)
    app.dependency_overrides[current_user] = lambda: {"id": "user-manager", "role": "manager"}

    conn = MagicMock()
    app.state.db_pool = FakePool(conn)

    conn.execute.return_value = FakeResult(rows=[
        {
            "id": "LIV-01",
            "title": "Launch Post",
            "status": "Published",
            "channel": "Instagram",
            "owner_id": "user-creator",
            "owner_name": "Maya Chen",
        }
    ])

    client = TestClient(app)
    resp = client.get("/api/knowledge/facts/F-001/linked-content")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["contentId"] == "LIV-01"
    assert data[0]["ownerName"] == "Maya Chen"


def test_alerts_read_and_mark_all_read():
    app = FastAPI()
    app.include_router(alerts_router)
    app.dependency_overrides[current_user] = lambda: {"id": "user-reviewer", "role": "reviewer"}

    conn = MagicMock()
    app.state.db_pool = FakePool(conn)

    @contextmanager
    def fake_tx():
        yield conn

    conn.transaction.side_effect = fake_tx

    # Test patch with read: True
    conn.execute.return_value = FakeResult(row={
        "id": "AL-001",
        "recipient_id": "user-reviewer",
        "content_id": "LIV-02",
        "source_id": "F-004",
        "source_version": 2,
        "priority": "High",
        "status": "open",
        "title": "Price change",
        "reason": "Price updated",
        "old_value": "349",
        "new_value": "399",
        "created_at": "2026-10-28T10:00:00Z",
        "read_at": "2026-10-28T11:00:00Z",
    })

    client = TestClient(app)
    resp = client.patch("/api/alerts/AL-001", json={"read": True})
    assert resp.status_code == 200
    data = resp.json()
    assert data["read"] is True

    # Test mark-all-read
    resp2 = client.post("/api/alerts/mark-all-read")
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"

