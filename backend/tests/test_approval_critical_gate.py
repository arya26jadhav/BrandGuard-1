"""Approval is blocked while the content has open critical findings."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.routes.approval import approve_content, submit_for_review

CREATOR = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}
REVIEWER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}


class FakeResult:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConn:
    def __init__(self, status, open_critical=0, owner_id="user-creator"):
        self.row = {"status": status, "owner_id": owner_id}
        self.open_critical = open_critical
        self.calls = []

    def transaction(self):
        return FakeTransaction()

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FOR UPDATE" in sql:
            return FakeResult(self.row)
        if "FROM findings" in sql:
            return FakeResult({"n": self.open_critical})
        if "COALESCE(MAX(version)" in sql:
            return FakeResult({"v": 1})
        return FakeResult()

    def writes(self):
        return [s for s, _ in self.calls if s.lstrip().startswith(("UPDATE", "INSERT"))]


def test_approve_is_blocked_while_critical_findings_are_open():
    conn = FakeConn("In Review", open_critical=2)
    with pytest.raises(HTTPException) as exc:
        approve_content("cnt_1", None, conn, REVIEWER)
    assert exc.value.status_code == 409
    assert "2 open critical" in exc.value.detail
    assert conn.writes() == []


def test_approve_is_allowed_when_no_critical_findings_are_open():
    conn = FakeConn("In Review", open_critical=0)
    assert approve_content("cnt_1", None, conn, REVIEWER) == {"id": "cnt_1", "status": "Approved"}


def test_role_check_runs_before_the_critical_gate():
    conn = FakeConn("In Review", open_critical=2)
    with pytest.raises(HTTPException) as exc:
        approve_content("cnt_1", None, conn, CREATOR)
    assert exc.value.status_code == 403


def test_submit_is_not_blocked_by_open_critical_findings():
    conn = FakeConn("Checked", open_critical=3)
    assert submit_for_review("cnt_1", conn, CREATOR)["status"] == "In Review"