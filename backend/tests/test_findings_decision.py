"""PATCH /api/findings/{id}: accept, edit and reject (plan section 2).

Calls decide_finding directly with a scripted fake connection, so no database is needed.
The HTTP layer (login and dependency injection) is not exercised here.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.routes.findings import DecisionIn, decide_finding

BODY = "Buy now and get the quickest results."
START = BODY.index("quickest")
END = START + len("quickest")
CREATOR = {"id": "user-creator", "name": "Maya Chen", "role": "creator"}


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

    def __exit__(self, *exc):
        return False


class FakeConn:
    """Returns canned rows for each SQL shape the route runs, and records every call."""

    def __init__(self, *, status="Draft", owner="user-creator", body=BODY,
                 original="quickest", fix="fastest", finding_status="open"):
        self.row = {
            "id": "fnd_1", "content_id": "cnt_1", "status": finding_status,
            "start": START, "end": END, "original_text": original,
            "suggested_fix": fix, "ai_generated": True, "title": "Absolute claim",
            "owner_id": owner, "content_status": status, "body_text": body,
        }
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FOR UPDATE OF f, c" in sql:
            return FakeResult(row=self.row)
        if "AND start IS NOT NULL" in sql:          # other open findings, for offset shifts
            return FakeResult(rows=[])
        if "COALESCE(MAX(version)" in sql:
            return FakeResult(row={"v": 1})
        if "check_run_id = (" in sql:              # list_latest_findings at the end
            return FakeResult(rows=[])
        return FakeResult()

    def transaction(self):
        return FakeTransaction()

    def sql_containing(self, text):
        return [(sql, params) for sql, params in self.calls if text in sql]


def _decide(conn, action, **fields):
    return decide_finding("fnd_1", DecisionIn(action=action, **fields), conn=conn, user=CREATOR)


def test_accept_applies_fix_and_records_decision():
    conn = FakeConn()
    result = _decide(conn, "accept")
    assert result["status"] == "accepted"
    assert result["bodyText"] == BODY.replace("quickest", "fastest")
    params = conn.sql_containing("INSERT INTO decisions")[0][1]
    assert params[4] == "accept"
    assert conn.sql_containing("INSERT INTO content_versions")


def test_edit_uses_the_edited_text():
    conn = FakeConn()
    result = _decide(conn, "edit", editedText="rapid")
    assert result["status"] == "edited"
    assert result["bodyText"] == BODY.replace("quickest", "rapid")
    params = conn.sql_containing("INSERT INTO decisions")[0][1]
    assert params[4] == "edit" and params[6] == "rapid"


def test_blank_edit_is_rejected_before_any_write():
    conn = FakeConn()
    with pytest.raises(HTTPException) as err:
        _decide(conn, "edit", editedText="   ")
    assert err.value.status_code == 422
    assert not conn.sql_containing("UPDATE content")


def test_reject_records_decision_and_leaves_text_alone():
    conn = FakeConn()
    result = _decide(conn, "reject", rejectReason="Not our claim")
    assert result["status"] == "rejected"
    assert result["bodyText"] == BODY
    assert not conn.sql_containing("UPDATE content")
    params = conn.sql_containing("INSERT INTO decisions")[0][1]
    assert params[4] == "reject" and params[5] == "Not our claim"


def test_only_the_creator_role_can_decide():
    conn = FakeConn()
    reviewer = dict(CREATOR, role="reviewer")
    with pytest.raises(HTTPException) as err:
        decide_finding("fnd_1", DecisionIn(action="reject"), conn=conn, user=reviewer)
    assert err.value.status_code == 403
    assert conn.calls == []


def test_creator_cannot_decide_on_someone_elses_content():
    conn = FakeConn(owner="user-creator-test")
    with pytest.raises(HTTPException) as err:
        _decide(conn, "reject")
    assert err.value.status_code == 403


def test_published_content_is_locked():
    conn = FakeConn(status="Published")
    with pytest.raises(HTTPException) as err:
        _decide(conn, "accept")
    assert err.value.status_code == 409


def test_stale_text_is_rejected_with_409():
    conn = FakeConn(original="slowest")
    with pytest.raises(HTTPException) as err:
        _decide(conn, "accept")
    assert err.value.status_code == 409
    assert not conn.sql_containing("UPDATE content")