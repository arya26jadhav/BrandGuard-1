"""The only place the model is called (plan section 3). Gemini only.

call_llm returns a CallResult whose .output is the Pydantic-validated object.
If the reply is not valid JSON or fails the schema, the call is retried once with
the validation problem appended (field names and messages only, never the post text).
If both attempts fail, AIUnavailable is raised and the caller falls back to rules only.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError

from app.config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT_SECONDS = 20
MAX_ATTEMPTS = 2  # one call plus one retry


class AIUnavailable(Exception):
    """The model could not give a valid answer. The message holds no request content."""


@dataclass(frozen=True)
class CallResult:
    output: Any
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int


def _post(model: str, api_key: str, system: str, user: str) -> dict:
    resp = httpx.post(
        GEMINI_URL.format(model=model),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0,
            },
        },
        timeout=TIMEOUT_SECONDS,
    )
    resp.raise_for_status()
    return resp.json()


def _problem_summary(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:5]:
        location = ".".join(str(p) for p in err.get("loc", ())) or "reply"
        parts.append(f"{location}: {err.get('msg', 'invalid')}")
    return "; ".join(parts)


def call_llm(system: str, user: str, schema: type[BaseModel]) -> CallResult:
    settings = get_settings()
    if not settings.gemini_api_key:
        raise AIUnavailable("GEMINI_API_KEY is not set")

    model = settings.brandguard_model
    prompt = user
    last_error = "unknown"

    for _attempt in range(MAX_ATTEMPTS):
        started = time.monotonic()
        try:
            data = _post(model, settings.gemini_api_key, system, prompt)
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            output = schema.model_validate_json(text)
            usage = data.get("usageMetadata", {})
            return CallResult(
                output=output,
                model=model,
                latency_ms=int((time.monotonic() - started) * 1000),
                input_tokens=int(usage.get("promptTokenCount", 0)),
                output_tokens=int(usage.get("candidatesTokenCount", 0)),
            )
        except ValidationError as exc:
            # ValidationError is a ValueError, so it must be handled before the generic clause.
            last_error = "ValidationError"
            prompt = (
                f"{user}\n\nYour previous reply was rejected ({_problem_summary(exc)}). "
                "Reply again with one JSON object that matches the schema exactly."
            )
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            last_error = exc.__class__.__name__

    raise AIUnavailable(f"Gemini call failed: {last_error}")
