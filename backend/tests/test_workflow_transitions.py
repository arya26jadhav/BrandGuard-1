"""State machine rules: each move is either allowed for the right role, or rejected.

These tests call check_transition directly, so they need no database.
"""
from __future__ import annotations

from itertools import product

import pytest

from app.services.workflow import (
    TRANSITIONS,
    Forbidden,
    InvalidTransition,
    Role,
    Status,
    check_transition,
)

ALLOWED_PAIRS = sorted(TRANSITIONS, key=lambda p: (p[0].value, p[1].value))
FORBIDDEN_PAIRS = [pair for pair in product(Status, Status) if pair not in TRANSITIONS]


def test_transition_table_has_the_agreed_moves():
    # Guard: if someone adds or removes a move, this test should be updated on purpose.
    assert set(TRANSITIONS) == {
        (Status.DRAFT, Status.CHECKED),
        (Status.FIXING, Status.CHECKED),
        (Status.CHECKED, Status.FIXING),
        (Status.CHECKED, Status.IN_REVIEW),
        (Status.FIXING, Status.IN_REVIEW),
        (Status.IN_REVIEW, Status.APPROVED),
        (Status.IN_REVIEW, Status.CHANGES_REQUESTED),
        (Status.CHANGES_REQUESTED, Status.FIXING),
        (Status.APPROVED, Status.PUBLISHED),
        (Status.PUBLISHED, Status.NEEDS_REVALIDATION),
        (Status.NEEDS_REVALIDATION, Status.FIXING),
    }


@pytest.mark.parametrize("frm,to", FORBIDDEN_PAIRS)
def test_move_not_in_the_table_is_rejected_for_every_role(frm, to):
    for role in Role:
        with pytest.raises(InvalidTransition):
            check_transition(frm, to, role, comment="reason")


@pytest.mark.parametrize("frm,to", ALLOWED_PAIRS)
def test_allowed_move_is_rejected_for_roles_not_in_the_table(frm, to):
    allowed = TRANSITIONS[(frm, to)]
    for role in Role:
        if role in allowed:
            continue
        with pytest.raises(Forbidden):
            check_transition(frm, to, role, comment="reason")


@pytest.mark.parametrize("frm,to", ALLOWED_PAIRS)
def test_allowed_move_succeeds_for_each_permitted_role(frm, to):
    for role in TRANSITIONS[(frm, to)]:
        assert check_transition(frm, to, role, comment="Fix the price") is None


@pytest.mark.parametrize("comment", [None, "", "   "])
def test_send_back_needs_a_non_blank_comment(comment):
    with pytest.raises(ValueError):
        check_transition(Status.IN_REVIEW, Status.CHANGES_REQUESTED, Role.REVIEWER, comment=comment)


def test_send_back_with_a_comment_is_allowed():
    assert check_transition(
        Status.IN_REVIEW, Status.CHANGES_REQUESTED, Role.REVIEWER, comment="Fix the price"
    ) is None