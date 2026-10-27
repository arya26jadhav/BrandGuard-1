"""Tests verifying the switch to the real evidence source (app.ai.evidence).

These tests run without a live database using a fake connection.
"""
from __future__ import annotations

from typing import Any

import app.ai.evidence as real_evidence
import app.services.ai_check as ai_check


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]] | None = None):
        self._rows = rows or []

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class FakeConn:
    def __init__(
        self,
        fact_rows: list[dict[str, Any]] | None = None,
        guideline_rows: list[dict[str, Any]] | None = None,
    ):
        self.calls: list[tuple[str, tuple]] = []
        self.fact_rows = fact_rows or []
        self.guideline_rows = guideline_rows or []

    def execute(self, sql: str, params: tuple = ()) -> FakeResult:
        self.calls.append((sql, tuple(params) if params else ()))
        normalized = " ".join(sql.strip().split())
        if "FROM facts" in normalized:
            return FakeResult(self.fact_rows)
        if "FROM guidelines" in normalized:
            return FakeResult(self.guideline_rows)
        return FakeResult([])


def test_ai_check_imports_real_evidence_module():
    """ai_check.get_evidence must be the function from app.ai.evidence."""
    assert ai_check.get_evidence is real_evidence.get_evidence
    assert ai_check.get_evidence.__module__ == "app.ai.evidence"


def test_active_fact_statuses_constant():
    """ACTIVE_FACT_STATUSES in app.ai.evidence must equal ['Active', 'Expiring soon']."""
    assert real_evidence.ACTIVE_FACT_STATUSES == ["Active", "Expiring soon"]


def test_get_evidence_filters_by_active_statuses_and_returns_expected_shape():
    """get_evidence passes ['Active', 'Expiring soon'] to SQL and returns facts followed by guidelines."""
    canned_facts = [
        {"id": "F-001", "version": 1, "text": "Face wash is natural."},
        {"id": "F-006", "version": 1, "text": "Cruelty-free certification valid until 2026-12-31."},
    ]
    canned_guidelines = [
        {"id": "G-001", "version": 1, "text": "Avoid absolute skincare claims."},
    ]
    conn = FakeConn(fact_rows=canned_facts, guideline_rows=canned_guidelines)

    evidence_items = real_evidence.get_evidence(conn, "Website")

    # Confirm recorded calls
    assert len(conn.calls) == 2

    fact_sql, fact_params = conn.calls[0]
    assert "WHERE status = ANY(%s)" in fact_sql
    assert fact_params == (["Active", "Expiring soon"],)

    guide_sql, guide_params = conn.calls[1]
    assert "%s = ANY(applies_to_channels)" in guide_sql
    assert guide_params == ("Website",)

    # Confirm items: facts followed by guidelines, each with source_id, version, text, kind
    assert evidence_items == [
        {
            "source_id": "F-001",
            "version": 1,
            "text": "Face wash is natural.",
            "kind": "fact",
        },
        {
            "source_id": "F-006",
            "version": 1,
            "text": "Cruelty-free certification valid until 2026-12-31.",
            "kind": "fact",
        },
        {
            "source_id": "G-001",
            "version": 1,
            "text": "Avoid absolute skincare claims.",
            "kind": "guideline",
        },
    ]

