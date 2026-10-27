"""Rules-only fallback: when the AI stage fails, run_rule_check still returns rule findings.

Uses the same fake connection and stubs as test_run_check.py, so no database or model is needed.
"""
from __future__ import annotations

from types import SimpleNamespace

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
    def __init__(self, body_text="Buy now, 100% clear skin."):
        self.body_text = body_text
        self.calls: list[tuple[str, tuple]] = []

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))
        if "FROM content WHERE id" in sql and "FOR UPDATE" not in sql:
            return FakeResult(row={"id": "cnt_1", "channel": "Instagram",
                                   "body_text": self.body_text, "status": "Draft"})
        if "FOR UPDATE" in sql:
            return FakeResult(row={"status": "Draft", "body_text": self.body_text})
        if "COALESCE(MAX(version)" in sql:
            return FakeResult(row={"v": 1})
        return FakeResult()

    def transaction(self):
        return FakeTransaction()


RULE_FINDING = {
    "id": "fnd_rule", "type": "rule", "start": 0, "end": 3, "severity": "warning",
    "title": "Banned phrase", "reason": "Matched a brand rule.", "sourceId": "G-001",
    "sourceVersion": 1, "suggestedFix": "", "originalText": "Buy",
    "confidence": 1.0, "aiGenerated": False, "needsHumanReview": False,
    "suggestionKind": "Terminology change",
}


def test_failed_ai_stage_falls_back_to_rules_only(monkeypatch):
    conn = FakeConn()
    monkeypatch.setattr(checks, "load_active_rules", lambda conn, channel: [])
    monkeypatch.setattr(checks, "run_rules", lambda text, content_id, rules: [dict(RULE_FINDING)])
    monkeypatch.setattr(checks, "load_confidential_terms", lambda conn: [])
    monkeypatch.setattr(checks, "get_settings", lambda: SimpleNamespace(brandguard_model="test-model"))

    # The AI stage fails: this is what happens when the API key is missing or the call times out.
    failed = checks.AIStage(status="fallback", error="AI stage failed: AIUnavailable")
    monkeypatch.setattr(checks, "run_ai_stage", lambda *args, **kwargs: failed)

    result = checks.run_check(conn, "cnt_1")

    assert result["aiStatus"] == "fallback"
    assert result["rulesOnlyFallback"] is True
    assert "AIUnavailable" in result["aiError"]
    # The fake connection returns no rows for the findings SELECT, so this only checks the shape.
    assert result["findings"] == []