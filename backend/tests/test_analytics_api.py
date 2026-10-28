"""Tests for GET /api/analytics/summary."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.analytics import router
from app.security import current_user

USER_MANAGER = {"id": "user-manager", "role": "manager", "name": "Sarah Connor"}
USER_ADMIN = {"id": "user-admin", "role": "admin", "name": "Alex Morgan"}
USER_CREATOR = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}
USER_REVIEWER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}


class FakeResult:
    def __init__(self, row=None, rows=None):
        self._row = row
        self._rows = rows or []

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class FakeAnalyticsConn:
    def __init__(
        self,
        review_rows=None,
        unresolved_count=0,
        outdated_count=0,
        decision_rows=None,
        rejected_rows=None,
        findings_rows=None,
        trend_rows=None,
    ):
        self.review_rows = review_rows or []
        self.unresolved_count = unresolved_count
        self.outdated_count = outdated_count
        self.decision_rows = decision_rows or []
        self.rejected_rows = rejected_rows or []
        self.findings_rows = findings_rows or []
        self.trend_rows = trend_rows or []

    def execute(self, sql: str, params: tuple = ()) -> FakeResult:
        # 1. Review rows
        if "FROM content" in sql and "EXTRACT(EPOCH" in sql:
            return FakeResult(rows=self.review_rows)

        # 2. Unresolved issues
        if "FROM findings" in sql and "status = 'open'" in sql:
            return FakeResult(row={"count": self.unresolved_count})

        # 3. Outdated published posts
        if "FROM alerts" in sql and "COUNT(DISTINCT content_id)" in sql:
            return FakeResult(row={"count": self.outdated_count})

        # 4. Decisions summary
        if "FROM decisions" in sql and "GROUP BY action" in sql:
            return FakeResult(rows=self.decision_rows)

        # 5. Rejected suggestions
        if "FROM decisions d" in sql and "JOIN findings f" in sql:
            return FakeResult(rows=self.rejected_rows)

        # 6. Violated rules
        if "FROM findings f" in sql and "LEFT JOIN guidelines g" in sql:
            return FakeResult(rows=self.findings_rows)

        # 7. Trend
        if "FROM findings f" in sql and "JOIN check_runs cr" in sql:
            return FakeResult(rows=self.trend_rows)

        return FakeResult()


class FakePool:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self):
        yield self._conn


def _app(conn: FakeAnalyticsConn, auth_user: dict | None = USER_MANAGER) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.db_pool = FakePool(conn)
    if auth_user:
        app.dependency_overrides[current_user] = lambda: auth_user
    return app


def test_analytics_requires_auth():
    app = _app(FakeAnalyticsConn(), auth_user=None)
    res = TestClient(app).get("/api/analytics/summary")
    assert res.status_code == 401


def test_analytics_forbidden_for_creator_and_reviewer():
    for user in (USER_CREATOR, USER_REVIEWER):
        app = _app(FakeAnalyticsConn(), auth_user=user)
        res = TestClient(app).get("/api/analytics/summary")
        assert res.status_code == 403


def test_analytics_allowed_for_manager_and_admin():
    for user in (USER_MANAGER, USER_ADMIN):
        app = _app(FakeAnalyticsConn(), auth_user=user)
        res = TestClient(app).get("/api/analytics/summary")
        assert res.status_code == 200


def test_analytics_empty_database_shape():
    app = _app(FakeAnalyticsConn(), auth_user=USER_MANAGER)
    res = TestClient(app).get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()

    # Exact expected keys and empty values
    assert data["kpis"] == {
        "avgReviewMinutes": None,
        "avgReviewItems": 0,
        "unresolvedIssues": 0,
        "outdatedPublishedPosts": 0,
        "suggestionsAcceptedPct": None,
        "decisionCount": 0,
    }
    assert data["mostViolatedRules"] == []
    assert data["mostRejectedSuggestions"] == []
    assert data["issuesOverTime"] == []
    assert data["reviewTimeByTeam"] == []


def test_analytics_review_time_threshold_not_met():
    # Only 4 items (threshold requires >= 5 items)
    conn = FakeAnalyticsConn(
        review_rows=[
            {"team": "Marketing", "duration_minutes": 30.0},
            {"team": "Sales", "duration_minutes": 20.0},
            {"team": "Marketing", "duration_minutes": 40.0},
            {"team": "Sales", "duration_minutes": 25.0},
        ]
    )
    app = _app(conn)
    res = TestClient(app).get("/api/analytics/summary")
    data = res.json()
    assert data["kpis"]["avgReviewMinutes"] is None
    assert data["kpis"]["avgReviewItems"] == 4
    assert data["reviewTimeByTeam"] == []

    # 5 items but all from 1 single team (threshold requires >= 2 teams)
    conn_single_team = FakeAnalyticsConn(
        review_rows=[
            {"team": "Marketing", "duration_minutes": 30.0},
            {"team": "Marketing", "duration_minutes": 20.0},
            {"team": "Marketing", "duration_minutes": 40.0},
            {"team": "Marketing", "duration_minutes": 25.0},
            {"team": "Marketing", "duration_minutes": 35.0},
        ]
    )
    app2 = _app(conn_single_team)
    res2 = TestClient(app2).get("/api/analytics/summary")
    data2 = res2.json()
    assert data2["kpis"]["avgReviewMinutes"] is None
    assert data2["kpis"]["avgReviewItems"] == 5
    assert data2["reviewTimeByTeam"] == []


def test_analytics_review_time_threshold_met():
    # 5 items across 2 teams
    conn = FakeAnalyticsConn(
        review_rows=[
            {"team": "Marketing", "duration_minutes": 30.0},
            {"team": "Sales", "duration_minutes": 20.0},
            {"team": "Marketing", "duration_minutes": 40.0},
            {"team": "Sales", "duration_minutes": 20.0},
            {"team": "Marketing", "duration_minutes": 50.0},
        ]
    )
    app = _app(conn)
    res = TestClient(app).get("/api/analytics/summary")
    data = res.json()
    # (30 + 20 + 40 + 20 + 50) / 5 = 160 / 5 = 32.0
    assert data["kpis"]["avgReviewMinutes"] == 32.0
    assert data["kpis"]["avgReviewItems"] == 5
    # Marketing: (30 + 40 + 50) / 3 = 40.0; Sales: (20 + 20) / 2 = 20.0
    assert data["reviewTimeByTeam"] == [
        {"team": "Marketing", "avgMinutes": 40.0},
        {"team": "Sales", "avgMinutes": 20.0},
    ]


def test_analytics_decisions_acceptance_threshold():
    # 9 decisions: below threshold (requires >= 10)
    conn_below = FakeAnalyticsConn(
        decision_rows=[
            {"action": "accept", "count": 7},
            {"action": "reject", "count": 2},
        ]
    )
    app = _app(conn_below)
    res = TestClient(app).get("/api/analytics/summary")
    data = res.json()
    assert data["kpis"]["suggestionsAcceptedPct"] is None
    assert data["kpis"]["decisionCount"] == 9

    # 10 decisions: threshold met -> 8/10 = 80.0%
    conn_met = FakeAnalyticsConn(
        decision_rows=[
            {"action": "accept", "count": 8},
            {"action": "reject", "count": 2},
        ]
    )
    app2 = _app(conn_met)
    res2 = TestClient(app2).get("/api/analytics/summary")
    data2 = res2.json()
    assert data2["kpis"]["suggestionsAcceptedPct"] == 80.0
    assert data2["kpis"]["decisionCount"] == 10


def test_analytics_rejected_suggestions_threshold():
    # Below 5 decisions: returns []
    conn_few = FakeAnalyticsConn(
        decision_rows=[
            {"action": "accept", "count": 2},
            {"action": "reject", "count": 1},
        ],
        rejected_rows=[
            {"suggestion_kind": "Tone rewrite", "count": 1},
        ],
    )
    app = _app(conn_few)
    assert TestClient(app).get("/api/analytics/summary").json()["mostRejectedSuggestions"] == []

    # >= 5 decisions but 0 rejections: returns []
    conn_no_rej = FakeAnalyticsConn(
        decision_rows=[
            {"action": "accept", "count": 5},
        ],
    )
    app2 = _app(conn_no_rej)
    assert TestClient(app2).get("/api/analytics/summary").json()["mostRejectedSuggestions"] == []

    # >= 5 decisions with >= 1 rejection: populated
    conn_met = FakeAnalyticsConn(
        decision_rows=[
            {"action": "accept", "count": 4},
            {"action": "reject", "count": 2},
        ],
        rejected_rows=[
            {"suggestion_kind": "Tone rewrite", "count": 2},
        ],
    )
    app3 = _app(conn_met)
    assert TestClient(app3).get("/api/analytics/summary").json()["mostRejectedSuggestions"] == [
        {"type": "Tone rewrite", "label": "Tone rewrite", "count": 2}
    ]


def test_analytics_most_violated_rules_threshold():
    # Below 5 total findings: returns []
    conn_few = FakeAnalyticsConn(
        findings_rows=[
            {"source_id": "G-001", "count": 3, "label": "Absolute Claims"},
            {"source_id": "G-002", "count": 1, "label": "Pricing Rule"},
        ]
    )
    app = _app(conn_few)
    assert TestClient(app).get("/api/analytics/summary").json()["mostViolatedRules"] == []

    # >= 5 findings: returns top 5
    conn_met = FakeAnalyticsConn(
        findings_rows=[
            {"source_id": "G-001", "count": 4, "label": "Absolute Claims"},
            {"source_id": "G-002", "count": 2, "label": "Pricing Rule"},
        ]
    )
    app2 = _app(conn_met)
    assert TestClient(app2).get("/api/analytics/summary").json()["mostViolatedRules"] == [
        {"ruleId": "G-001", "label": "Absolute Claims", "count": 4},
        {"ruleId": "G-002", "label": "Pricing Rule", "count": 2},
    ]


def test_analytics_issues_over_time():
    conn = FakeAnalyticsConn(
        trend_rows=[
            {"date": "2026-10-20", "critical": 2, "warning": 3, "info": 1},
            {"date": "2026-10-21", "critical": 0, "warning": 4, "info": 2},
        ]
    )
    app = _app(conn)
    res = TestClient(app).get("/api/analytics/summary")
    assert res.json()["issuesOverTime"] == [
        {"date": "2026-10-20", "critical": 2, "warning": 3, "info": 1},
        {"date": "2026-10-21", "critical": 0, "warning": 4, "info": 2},
    ]
