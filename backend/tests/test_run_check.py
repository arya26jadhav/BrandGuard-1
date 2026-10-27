"""run_check: system-run checks write an 'ai' revision with no user, and reject blocked statuses.

The database is replaced by a fake connection that records each SQL call. These tests check
the parameters passed to the revisions insert, and the 409 guard. They do not check that the
schema accepts the values; that was confirmed by reading data/schema.sql.
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services import checks


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
    """Returns canned rows for SELECTs on content and records every execute call."""

    def __init__(self, status: str, body_text: str = "Plain text.", channel: str = "Website"):
        self.status = status
        self.body_text = body_text
        self.channel = channel
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FROM content WHERE id" in sql and "FOR UPDATE" not in sql:
            return FakeResult(row={"id": "cnt_1", "channel": self.channel,
                                   "body_text": self.body_text, "status": self.status})
        if "FOR UPDATE" in sql:
            return FakeResult(row={"status": self.status, "body_text": self.body_text})
        if sql.lstrip().startswith("SELECT id, content_id, type"):
            return FakeResult(rows=[])
        return FakeResult()

    def transaction(self):
        return FakeTransaction()


@pytest.fixture
def stubbed(monkeypatch):
    """Stub everything that run_rule_check calls outside the connection."""
    monkeypatch.setattr(checks, "load_active_rules", lambda conn, channel: [])
    monkeypatch.setattr(checks, "run_rules", lambda text, content_id, rules: [])
    monkeypatch.setattr(checks, "load_confidential_terms", lambda conn: [])

    class EmptyAI:
        status = "success"
        error = None
        findings = []
        dropped = 0
        redacted = 0
        model = "test-model"
        latency_ms = 0
        input_tokens = 0
        output_tokens = 0
        input_hash = None

    monkeypatch.setattr(checks, "run_ai_stage", lambda *args, **kwargs: EmptyAI())
    monkeypatch.setattr(checks, "get_settings", lambda: type("S", (), {"brandguard_model": "test-model"})())
    return checks


def _revision_params(conn: FakeConn) -> tuple:
    matches = [params for sql, params in conn.calls if "INSERT INTO revisions" in sql]
    # run_rule_check writes exactly one 'checked' revision row, and no AI row (input_hash is None).
    assert len(matches) == 1, f"expected one revisions insert, got {len(matches)}"
    return matches[0]


def test_system_check_writes_ai_revision_with_no_user(stubbed):
    conn = FakeConn(status="Needs revalidation")

    checks.run_check(conn, "cnt_1")

    # Parameter order in the insert: id, content_id, actor_id, actor_label, kind, detail, from, to
    _, content_id, actor_id, actor_label, kind, detail, from_status, to_status = _revision_params(conn)
    assert content_id == "cnt_1"
    assert actor_id is None
    assert actor_label == "AI Check"
    assert kind == "ai"
    assert from_status == "Needs revalidation"


def test_human_check_still_writes_person_revision_with_user(stubbed):
    conn = FakeConn(status="Draft")
    actor = {"id": "user-creator", "name": "Maya Chen"}

    checks.run_rule_check(conn, "cnt_1", actor=actor)

    _, content_id, actor_id, actor_label, kind, detail, from_status, to_status = _revision_params(conn)
    assert actor_id == "user-creator"
    assert actor_label == "Maya Chen"
    assert kind == "person"


@pytest.mark.parametrize("blocked", ["Published", "In Review", "Approved"])
def test_run_check_rejects_blocked_statuses_with_409(stubbed, blocked):
    conn = FakeConn(status=blocked)

    with pytest.raises(HTTPException) as err:
        checks.run_check(conn, "cnt_1")

    assert err.value.status_code == 409
    assert not any("INSERT INTO revisions" in sql for sql, _ in conn.calls)


def test_run_check_allows_needs_revalidation(stubbed):
    conn = FakeConn(status="Needs revalidation")

    result = checks.run_check(conn, "cnt_1")

    assert result["checkRunId"].startswith("chk_")