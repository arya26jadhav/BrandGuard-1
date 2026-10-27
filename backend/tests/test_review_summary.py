"""review_summary: counts come from content statuses, not hard-coded zeros.

The database is replaced by a fake connection that records the SQL and parameters.
The test checks the statuses passed to the query and the response keys. It does not
run the SQL; the status names were checked against the content.status CHECK in data/schema.sql.
"""
from __future__ import annotations

from app.routes.review import (
    CHANGES_REQUESTED_STATUS,
    PENDING_REVIEW_STATUS,
    review_summary,
)


class FakeResult:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class FakeConn:
    def __init__(self, row):
        self.row = row
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        return FakeResult(self.row)


FAKE_USER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}


def test_summary_returns_counts_from_the_row():
    conn = FakeConn({"pending_review": 3, "changes_requested": 1})
    assert review_summary(conn, _user=FAKE_USER) == {"pendingReview": 3, "changesRequested": 1}


def test_summary_queries_the_real_status_values():
    conn = FakeConn({"pending_review": 0, "changes_requested": 0})
    review_summary(conn, _user=FAKE_USER)
    sql, params = conn.calls[0]
    assert "FROM content" in sql
    assert params == (PENDING_REVIEW_STATUS, CHANGES_REQUESTED_STATUS)
    assert params == ("In Review", "Changes requested")


def test_summary_is_not_hard_coded_zeros():
    conn = FakeConn({"pending_review": 5, "changes_requested": 2})
    assert review_summary(conn, _user=FAKE_USER) != {"pendingReview": 0, "changesRequested": 0}
