"""Each approval move writes one revisions row with the right action, statuses and detail.

A refused move writes nothing. Uses the same fake connection style as test_approval_routes.py.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

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
REVIEWER = {"id": "user-reviewer", "role": "reviewer", "name": "Priya Shah"}
MANAGER = {"id": "user-manager", "role": "manager", "name": "Jordan Lee"}

# Positions in the revisions INSERT parameters (see _move in approval.py)
REV_CONTENT_ID, REV_ACTOR_ID, REV_ACTOR_LABEL = 1, 2, 3
REV_ACTION, REV_DETAIL, REV_FROM, REV_TO, REV_VERSION = 4, 5, 6, 7, 8


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
    def __init__(self, status, owner_id="user-creator", version=2):
        self.row = {"status": status, "owner_id": owner_id}
        self.version = version
        self.calls: list[tuple[str, tuple]] = []

    def transaction(self):
        return FakeTransaction()

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FOR UPDATE" in sql:
            return FakeResult(self.row)
        if "COALESCE(MAX(version)" in sql:
            return FakeResult({"v": self.version})
        return FakeResult()

    def writes(self):
        return [(sql, p) for sql, p in self.calls if sql.lstrip().startswith(("UPDATE", "INSERT"))]

    def revision_rows(self):
        return [p for sql, p in self.calls if "INSERT INTO revisions" in sql]


def db(status: Status) -> str:
    return DB_STATUS[status]


def test_start_fixing_revision_row():
    conn = FakeConn("Changes requested", version=3)
    start_fixing("cnt_1", conn, CREATOR)
    (rev,) = conn.revision_rows()
    assert rev[REV_CONTENT_ID] == "cnt_1"
    assert rev[REV_ACTOR_ID] == "user-creator"
    assert rev[REV_ACTOR_LABEL] == "Maya Chen"
    assert rev[REV_ACTION] == "fixing_started"
    assert rev[REV_DETAIL] == "fixing started"       # underscores become spaces
    assert rev[REV_FROM] == "Changes requested"
    assert rev[REV_TO] == db(Status.FIXING)
    assert rev[REV_VERSION] == 3


def test_approve_without_comment_uses_action_as_detail():
    conn = FakeConn("In Review")
    approve_content("cnt_1", None, conn, REVIEWER)
    (rev,) = conn.revision_rows()
    assert rev[REV_ACTION] == "approved"
    assert rev[REV_DETAIL] == "approved"
    assert rev[REV_FROM] == "In Review"
    assert rev[REV_TO] == db(Status.APPROVED)
    assert rev[REV_ACTOR_ID] == "user-reviewer"


def test_approve_with_blank_comment_uses_action_as_detail():
    conn = FakeConn("In Review")
    approve_content("cnt_1", CommentBody(comment="   "), conn, REVIEWER)
    (rev,) = conn.revision_rows()
    assert rev[REV_DETAIL] == "approved"


def test_approve_with_comment_stores_trimmed_comment_as_detail():
    conn = FakeConn("In Review")
    approve_content("cnt_1", CommentBody(comment="  Looks good  "), conn, REVIEWER)
    (rev,) = conn.revision_rows()
    assert rev[REV_DETAIL] == "Looks good"


def test_request_changes_revision_row_holds_the_comment():
    conn = FakeConn("In Review")
    request_changes("cnt_1", CommentBody(comment="Fix the price"), conn, REVIEWER)
    (rev,) = conn.revision_rows()
    assert rev[REV_ACTION] == "changes_requested"
    assert rev[REV_DETAIL] == "Fix the price"
    assert rev[REV_FROM] == "In Review"
    assert rev[REV_TO] == db(Status.CHANGES_REQUESTED)


def test_manager_can_publish_approved_content_and_revision_records_it():
    conn = FakeConn("Approved", version=4)
    publish_content("cnt_1", conn, MANAGER)
    (rev,) = conn.revision_rows()
    assert rev[REV_ACTION] == "published"
    assert rev[REV_FROM] == "Approved"
    assert rev[REV_TO] == db(Status.PUBLISHED)
    assert rev[REV_ACTOR_ID] == "user-manager"
    assert rev[REV_VERSION] == 4


def test_each_successful_move_writes_exactly_one_revision_row():
    cases = [
        (lambda c: submit_for_review("cnt_1", c, CREATOR), "Checked"),
        (lambda c: start_fixing("cnt_1", c, CREATOR), "Changes requested"),
        (lambda c: approve_content("cnt_1", None, c, REVIEWER), "In Review"),
        (lambda c: request_changes("cnt_1", CommentBody(comment="x"), c, REVIEWER), "In Review"),
        (lambda c: publish_content("cnt_1", c, CREATOR), "Approved"),
    ]
    for call, status in cases:
        conn = FakeConn(status)
        call(conn)
        assert len(conn.revision_rows()) == 1, f"{status} did not write exactly one revision"


REFUSALS = [
    pytest.param(lambda c: submit_for_review("cnt_1", c, REVIEWER), "Checked", 403, id="reviewer-cannot-submit"),
    pytest.param(lambda c: publish_content("cnt_1", c, CREATOR), "In Review", 409, id="publish-before-approval"),
    pytest.param(lambda c: publish_content("cnt_1", c, REVIEWER), "Approved", 403, id="reviewer-cannot-publish"),
    pytest.param(lambda c: approve_content("cnt_1", None, c, CREATOR), "In Review", 403, id="creator-cannot-approve"),
    pytest.param(
        lambda c: request_changes("cnt_1", CommentBody(comment="   "), c, REVIEWER),
        "In Review", 422, id="send-back-blank-comment",
    ),
    pytest.param(lambda c: submit_for_review("cnt_1", c, CREATOR), "Draft", 409, id="submit-from-draft"),
]


@pytest.mark.parametrize("call,status,code", REFUSALS)
def test_refused_move_writes_nothing(call, status, code):
    conn = FakeConn(status)
    with pytest.raises(HTTPException) as exc:
        call(conn)
    assert exc.value.status_code == code
    assert conn.writes() == []


def test_missing_content_writes_nothing():
    conn = FakeConn("Checked")
    conn.row = None
    with pytest.raises(HTTPException) as exc:
        submit_for_review("cnt_404", conn, CREATOR)
    assert exc.value.status_code == 404
    assert conn.writes() == []
