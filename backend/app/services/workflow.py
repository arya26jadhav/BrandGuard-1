from enum import Enum


class Status(str, Enum):
    DRAFT = "Draft"
    CHECKED = "Checked"
    FIXING = "Fixing"
    IN_REVIEW = "In Review"
    CHANGES_REQUESTED = "Changes requested"
    APPROVED = "Approved"
    PUBLISHED = "Published"
    NEEDS_REVALIDATION = "Needs revalidation"


class Role(str, Enum):
    CREATOR = "creator"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    ADMIN = "admin"
    AI_CHECK = "ai_check"  # the system actor, shown as "AI Check" in history


class InvalidTransition(Exception):
    """Move is not in the state machine. API should return 409."""


class Forbidden(Exception):
    """Actor's role may not make this move. API should return 403."""


# (from, to) -> roles allowed to make the move
TRANSITIONS: dict[tuple[Status, Status], set[Role]] = {
    (Status.DRAFT, Status.CHECKED): {Role.AI_CHECK},
    (Status.FIXING, Status.CHECKED): {Role.AI_CHECK},
    (Status.CHECKED, Status.FIXING): {Role.CREATOR},
    (Status.CHECKED, Status.IN_REVIEW): {Role.CREATOR},
    (Status.FIXING, Status.IN_REVIEW): {Role.CREATOR},
    (Status.IN_REVIEW, Status.APPROVED): {Role.REVIEWER, Role.MANAGER},
    (Status.IN_REVIEW, Status.CHANGES_REQUESTED): {Role.REVIEWER, Role.MANAGER},
    (Status.CHANGES_REQUESTED, Status.FIXING): {Role.CREATOR},
    # Assumption: the plan does not say who publishes. Change this if the team decides otherwise.
    (Status.APPROVED, Status.PUBLISHED): {Role.CREATOR, Role.MANAGER, Role.ADMIN},
    (Status.PUBLISHED, Status.NEEDS_REVALIDATION): {Role.AI_CHECK},
    (Status.NEEDS_REVALIDATION, Status.FIXING): {Role.CREATOR},
}


def check_transition(
    current: Status,
    to: Status,
    actor: Role,
    comment: str | None = None,
) -> None:
    """Raise if the move is illegal. Returns None when the move is allowed."""
    allowed = TRANSITIONS.get((current, to))
    if allowed is None:
        raise InvalidTransition(f"{current.value} -> {to.value} is not allowed")
    if actor not in allowed:
        raise Forbidden(f"role '{actor.value}' cannot move {current.value} -> {to.value}")
    if to is Status.CHANGES_REQUESTED and not (comment and comment.strip()):
        raise ValueError("send back requires a comment")
