"""Pydantic models for the model's JSON reply (plan section 3)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AIFinding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quote: str = Field(min_length=1, max_length=500)
    source_id: str = Field(min_length=1, max_length=20)
    severity: Literal["critical", "warning", "info"]
    title: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)
    suggested_fix: str = Field(default="", max_length=500)
    suggestion_kind: Literal[
        "Tone rewrite", "Claim correction", "Suggested disclaimer", "Terminology change"
    ] = "Claim correction"
    confidence: float = Field(ge=0.0, le=1.0)


class AIOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    findings: list[AIFinding] = Field(default_factory=list, max_length=20)
