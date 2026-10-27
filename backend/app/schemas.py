
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


def to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class DemoLoginRequest(APIModel):
    user_id: str = Field(min_length=1, max_length=128)


class DemoUser(APIModel):
    id: str
    name: str
    initials: str
    role: Literal["creator", "manager", "reviewer", "admin"]
    title: str
    team: str
    persona_description: str = ""
    demo_route: str = "/content"


class UserResponse(APIModel):
    id: str
    name: str
    initials: str
    role: Literal["creator", "manager", "reviewer", "admin"]
    title: str
    team: str


class LoginResponse(APIModel):
    token: str
    user: UserResponse


class HealthResponse(APIModel):
    status: Literal["ok"]
    db: bool


class OwnerResponse(APIModel):
    id: str
    name: str
    initials: str


class FindingResponse(APIModel):
    id: str
    content_id: str
    type: Literal[
        "rule", "claim", "tone", "image", "accessibility", "security"
    ]
    start: int | None = None
    end: int | None = None
    bbox: list[float] | None = None
    severity: Literal["critical", "warning", "info"]
    title: str
    reason: str
    source_id: str
    source_version: int
    original_text: str = ""
    suggested_fix: str = ""
    confidence: float
    ai_generated: bool
    needs_human_review: bool
    status: Literal["open", "accepted", "edited", "rejected", "resolved"]


class ContentListItem(APIModel):
    id: str
    title: str
    channel: str
    format: str
    status: str
    owner: OwnerResponse
    team: str
    updated_at: datetime
    thumbnail_art: str | None = None
    high: int = 0
    medium: int = 0
    low: int = 0
    reason: str | None = None


class CommentCreate(APIModel):
    body: str = Field(min_length=1, max_length=10000)
    finding_id: str | None = None


class CommentResponse(APIModel):
    id: str
    content_id: str
    author_id: str
    body: str
    finding_id: str | None = None
    comment_type: str
    created_at: datetime


class ContentCreate(APIModel):
    title: str = Field(min_length=1, max_length=300)
    channel: Literal["Website", "Instagram", "Email", "Ad"]
    body_text: str = ""
    body_html: str = ""
    format: str = ""
    image_url: str | None = None
    alt_text: str | None = None


class ContentUpdate(APIModel):
    title: str | None = Field(default=None, max_length=300)
    channel: Literal["Website", "Instagram", "Email", "Ad"] | None = None
    body_text: str | None = None
    body_html: str | None = None
    format: str | None = None
    image_url: str | None = None
    alt_text: str | None = None


class AlertStatusUpdate(APIModel):
    status: Literal["open", "updated", "dismissed"]


class AlertResponse(APIModel):
    id: str
    title: str
    priority: str
    status: str
    reason: str
    fact: str
    old_value: str | None = None
    new_value: str | None = None
    old_sentence: str | None = None
    corrected_sentence: str | None = None
    content_id: str | None = None
    sent_at: datetime
    reminder_sent: int = 0
    read: bool = False
    channel: str | None = None
    owner: OwnerResponse | None = None


class DemoResetResponse(APIModel):
    ok: bool
    ms: int


class SampleDraft(APIModel):
    id: str
    title: str
    channel: str
    body_text: str
    body_html: str = ""
    format: str = ""
    category: str = ""


class AnalyticsSummary(APIModel):
    rules: list[dict[str, Any]]
    issue_trend: list[dict[str, Any]]
    teams: list[dict[str, Any]]
    rejected_suggestions: list[dict[str, Any]]
    unresolved_count: int
    outdated_published_count: int
    avg_review_minutes: float | None = None
    unclear_rule: dict[str, Any] | None = None
