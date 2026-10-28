"""Approval routes: each move goes through the workflow rules and writes a revisions row.

The database is replaced by a fake connection. The tests check the status values passed to
UPDATE and INSERT, and the HTTP errors. The DB status names are checked against data/schema.sql.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import HTTPException

from app.routes import approval
from app.routes.approval import (
    DB_STATUS,
    CommentBody,
    approve_content,
    publish_content,
    request_changes,
    start_fixing,
    submit_for_review,
)
from app.services.workflow import Status

CREATOR = {"id": "user-creator", "role": "creator", "name": "Maya Chen"}
OTHER_CREATOR = {"id": "user-creator-test", "role": "creator", "name": "Test Creator"}
REVIEWER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}
MANAGER = {"id": "user-manager", "role": "manager", "name": "Jordan Lee"}


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
    def __init__(self, status: str, owner_id: str = "user-creator"):
        self.row = {"status": status, "owner_id": owner_id}
        self.calls: list[tuple[str, tuple]] = []

    def transaction(self):
        return FakeTransaction()

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FOR UPDATE" in sql:
            return FakeResult(self.row)
        if "COALESCE(MAX(version)" in sql:
            return FakeResult({"v": 2})
        return FakeResult()

    def update_params(self):
        return [p for sql, p in self.calls if sql.lstrip().startswith("UPDATE content")][0]

    def revision_params(self):
        return [p for sql, p in self.calls if "INSERT INTO revisions" in sql][0]


def test_owner_submits_checked_content_for_review():
    conn = FakeConn("Checked")
    result = submit_for_review("cnt_1", conn, CREATOR)
    assert result == {"id": "cnt_1", "status": "In Review"}
    assert conn.update_params()[0] == "In Review"
    assert "submitted_at = now()" in [sql for sql, _ in conn.calls if sql.startswith("UPDATE")][0]
    revision = conn.revision_params()
    assert revision[4] == "submitted"            # action
    assert revision[6] == "Checked"              # from_status
    assert revision[7] == "In Review"            # to_status
    assert revision[8] == 2                      # version from content_versions


def test_other_creator_cannot_submit():
    with pytest.raises(HTTPException) as exc:
        submit_for_review("cnt_1", FakeConn("Checked"), OTHER_CREATOR)
    assert exc.value.status_code == 403


def test_submit_from_draft_is_rejected_as_conflict():
    with pytest.raises(HTTPException) as exc:
        submit_for_review("cnt_1", FakeConn("Draft"), CREATOR)
    assert exc.value.status_code == 409


def test_reviewer_approves_content_in_review():
    conn = FakeConn("In Review")
    assert approve_content("cnt_1", None, conn, REVIEWER) == {"id": "cnt_1", "status": "Approved"}
    assert "approved_at = now()" in [sql for sql, _ in conn.calls if sql.startswith("UPDATE")][0]


def test_creator_cannot_approve():
    with pytest.raises(HTTPException) as exc:
        approve_content("cnt_1", None, FakeConn("In Review"), CREATOR)
    assert exc.value.status_code == 403


def test_request_changes_needs_a_comment():
    with pytest.raises(HTTPException) as exc:
        request_changes("cnt_1", CommentBody(comment="   "), FakeConn("In Review"), REVIEWER)
    assert exc.value.status_code == 422


def test_request_changes_with_comment_writes_comment_to_revision():
    conn = FakeConn("In Review")
    result = request_changes("cnt_1", CommentBody(comment="Fix the price"), conn, MANAGER)
    assert result == {"id": "cnt_1", "status": "Changes requested"}
    assert conn.revision_params()[5] == "Fix the price"


def test_owner_starts_fixing_after_changes_requested():
    conn = FakeConn("Changes requested")
    assert start_fixing("cnt_1", conn, CREATOR) == {"id": "cnt_1", "status": "Fixing"}


def test_publish_before_approval_is_rejected():
    with pytest.raises(HTTPException) as exc:
        publish_content("cnt_1", FakeConn("In Review"), CREATOR)
    assert exc.value.status_code == 409


def test_owner_publishes_approved_content_and_stamps_published_at():
    conn = FakeConn("Approved")
    assert publish_content("cnt_1", conn, CREATOR) == {"id": "cnt_1", "status": "Published"}
    assert "published_at = now()" in [sql for sql, _ in conn.calls if sql.startswith("UPDATE")][0]


def test_reviewer_cannot_publish():
    with pytest.raises(HTTPException) as exc:
        publish_content("cnt_1", FakeConn("Approved"), REVIEWER)
    assert exc.value.status_code == 403


def test_missing_content_is_404():
    class Empty(FakeConn):
        def execute(self, sql, params=()):
            if "FOR UPDATE" in sql:
                return FakeResult(None)
            return FakeResult()

    with pytest.raises(HTTPException) as exc:
        submit_for_review("cnt_missing", Empty("Checked"), CREATOR)
    assert exc.value.status_code == 404


def test_db_status_names_match_schema_check():
    schema = (Path(__file__).resolve().parents[2] / "data" / "schema.sql").read_text(encoding="utf-8")
    check_line = next(line for line in schema.splitlines() if "status TEXT NOT NULL CHECK (status IN (" in line)
    for status in Status:
        assert f"'{DB_STATUS[status]}'" in check_line
    assert set(DB_STATUS) == set(Status)
