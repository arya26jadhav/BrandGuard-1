from unittest.mock import MagicMock

import pytest

from app.services import impact


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


def make_conn(rows):
    conn = MagicMock()
    conn.calls = []

    def execute(sql, params=None):
        conn.calls.append((sql, params))
        if "SELECT DISTINCT" in sql:
            return FakeResult(rows)
        return FakeResult([])

    conn.execute.side_effect = execute
    return conn


LIVE_ROWS = [{"content_id": "LIV-01", "title": "Post", "owner_id": "user-creator"}]


def run(conn, severity="High"):
    return impact.apply_fact_change(conn, "F-004", "old", "new", 2, severity, "fix")


@pytest.mark.parametrize("severity", ["High", "Medium"])
def test_valid_severity_is_used_as_priority(severity):
    conn = make_conn(LIVE_ROWS)
    run(conn, severity)
    inserts = [p for sql, p in conn.calls if "INSERT INTO alerts" in sql]
    assert len(inserts) == 1
    assert inserts[0][5] == severity


@pytest.mark.parametrize("bad", ["critical", "warning", "info", "", None])
def test_unknown_severity_raises_before_any_sql(bad):
    conn = make_conn(LIVE_ROWS)
    with pytest.raises(ValueError):
        run(conn, bad)
    assert conn.calls == []


def test_status_update_runs_before_alert_inserts():
    conn = make_conn(LIVE_ROWS)
    run(conn, "High")
    sqls = [sql for sql, _ in conn.calls]
    update_at = next(i for i, s in enumerate(sqls) if "UPDATE content" in s)
    insert_at = next(i for i, s in enumerate(sqls) if "INSERT INTO alerts" in s)
    assert update_at < insert_at


def test_no_published_posts_means_no_writes():
    conn = make_conn([])
    result = run(conn, "High")
    assert result["affectedItems"] == []
    sqls = [sql for sql, _ in conn.calls]
    assert not any("UPDATE content" in s for s in sqls)
    assert not any("INSERT INTO alerts" in s for s in sqls)
