"""Tests for the AI stage safeguards and the Gemini client. No network or database needed."""
from __future__ import annotations

import json

import pytest

from app.ai import client as ai_client
from app.ai.schemas import AIOutput
from app.config import get_settings
from app.services import ai_check

POST = "Makes you look ten years younger in one week. Dermatologically tested."
EVIDENCE = {
    "F-007": {"source_id": "F-007", "version": 3, "text": "Allowed wording", "kind": "fact"},
    "G-001": {"source_id": "G-001", "version": 1, "text": "No absolute claims", "kind": "guideline"},
}


def _finding(**overrides) -> dict:
    base = {
        "quote": "Makes you look ten years younger in one week.",
        "source_id": "G-001",
        "severity": "critical",
        "title": "Unrealistic claim",
        "reason": "Promises a result the evidence does not support.",
        "suggested_fix": "Helps skin look smoother with regular use.",
        "suggestion_kind": "Claim correction",
        "confidence": 0.9,
    }
    base.update(overrides)
    return base


def _run(findings: list[dict], rule_spans=None):
    output = AIOutput.model_validate({"findings": findings})
    return ai_check._to_findings(output, POST, EVIDENCE, rule_spans or [])


def test_valid_finding_is_kept_with_exact_offsets_and_source():
    kept, dropped = _run([_finding()])
    assert dropped == 0
    assert len(kept) == 1
    assert kept[0]["start"] == 0
    assert kept[0]["end"] == len("Makes you look ten years younger in one week.")
    assert kept[0]["sourceId"] == "G-001" and kept[0]["sourceVersion"] == 1
    assert kept[0]["aiGenerated"] is True


def test_unknown_source_id_is_dropped():
    kept, dropped = _run([_finding(source_id="F-999")])
    assert kept == [] and dropped == 1


def test_quote_not_in_post_is_dropped():
    kept, dropped = _run([_finding(quote="Clinically proven to work.")])
    assert kept == [] and dropped == 1


def test_finding_overlapping_a_rule_finding_is_dropped():
    start = POST.index("younger")
    kept, dropped = _run([_finding()], rule_spans=[(start, start + 5)])
    assert kept == [] and dropped == 1


def test_low_confidence_becomes_a_suggestion_needing_review():
    kept, _ = _run([_finding(confidence=0.5)])
    assert len(kept) == 1 and kept[0]["needsHumanReview"] is True


def test_very_low_confidence_is_dropped():
    kept, dropped = _run([_finding(confidence=0.2)])
    assert kept == [] and dropped == 1


def test_duplicate_source_and_position_is_kept_once():
    kept, dropped = _run([_finding(), _finding()])
    assert len(kept) == 1 and dropped == 1


def test_dermatologically_tested_is_not_flagged_when_model_does_not_flag_it():
    kept, _ = _run([_finding()])
    assert all("Dermatologically" not in f["originalText"] for f in kept)


def test_prompt_rule_five_names_contradicted_evidence():
    from app.ai.prompt import PROMPT_VERSION, SYSTEM_PROMPT

    assert PROMPT_VERSION == "claim-check-v2"
    assert "contradicts or breaks" in SYSTEM_PROMPT
    assert "G-001" in SYSTEM_PROMPT and "G-008" in SYSTEM_PROMPT


# --- Gemini client -----------------------------------------------------------

@pytest.fixture
def gemini_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("BRANDGUARD_MODEL", "test-model")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _gemini_reply(text: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
        "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 7},
    }


def test_missing_key_raises_unavailable(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test/test")
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    try:
        with pytest.raises(ai_client.AIUnavailable, match="GEMINI_API_KEY is not set"):
            ai_client.call_llm("system", "user", AIOutput)
    finally:
        get_settings.cache_clear()


def test_valid_reply_returns_validated_result_and_usage(monkeypatch, gemini_env):
    reply = json.dumps({"findings": [_finding()]})
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: _gemini_reply(reply))
    result = ai_client.call_llm("system", "user", AIOutput)
    assert result.model == "test-model"
    assert result.input_tokens == 11 and result.output_tokens == 7
    assert result.output.findings[0].source_id == "G-001"


def test_invalid_json_is_retried_once_with_the_problem_then_succeeds(monkeypatch, gemini_env):
    prompts: list[str] = []
    replies = iter([
        _gemini_reply("not json at all"),
        _gemini_reply(json.dumps({"findings": []})),
    ])

    def fake_post(model, api_key, system, user):
        prompts.append(user)
        return next(replies)

    monkeypatch.setattr(ai_client, "_post", fake_post)
    result = ai_client.call_llm("system", "base prompt", AIOutput)
    assert result.output.findings == []
    assert len(prompts) == 2
    assert prompts[0] == "base prompt"
    assert "previous reply was rejected" in prompts[1]


def test_two_failures_raise_unavailable_without_leaking_reply(monkeypatch, gemini_env):
    monkeypatch.setattr(ai_client, "_post", lambda *a, **k: _gemini_reply("secret post text {"))
    with pytest.raises(ai_client.AIUnavailable) as info:
        ai_client.call_llm("system", "user", AIOutput)
    assert "secret post text" not in str(info.value)
