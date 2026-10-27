"""Redaction of confidential terms before any model call (plan section 5, step 6).

Confidential terms come from rule_patterns where kind = 'confidential_term'. They are
masked in the post and in the evidence text before the request leaves the server.

Masking keeps the length of the text unchanged, so character offsets computed on the
masked text are still valid for the original. Matching is case-insensitive and needs a
non-word character (or the edge of the text) on both sides, so a term does not match
inside a longer word.

This module uses only the standard library, so it can be tested without a database.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable
from typing import Any

MASK_CHAR = "\u2588"  # full block: visibly redacted, one character per original character
MIN_TERM_LENGTH = 3   # shorter terms would mask ordinary words and make the check useless
MAX_TERMS = 200


def normalise_terms(terms: Iterable[Any]) -> list[str]:
    """Trim, drop short and duplicate terms, and sort longest first.

    Longest first matters: if 'Nightingale' and 'Project Nightingale' are both listed,
    the regex tries the longer phrase first, so the whole phrase is masked.
    """
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        if not isinstance(term, str):
            continue
        term = term.strip()
        if len(term) < MIN_TERM_LENGTH:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(term)
    cleaned.sort(key=len, reverse=True)
    return cleaned[:MAX_TERMS]


def terms_digest(terms: Iterable[Any]) -> str:
    """Stable fingerprint of the active term list, used in the AI cache key."""
    normalised = sorted(t.casefold() for t in normalise_terms(terms))
    return hashlib.sha256("\n".join(normalised).encode("utf-8")).hexdigest()[:16]


def _pattern(terms: list[str]) -> re.Pattern[str] | None:
    if not terms:
        return None
    alternatives = "|".join(re.escape(t) for t in terms)
    return re.compile(rf"(?<!\w)(?:{alternatives})(?!\w)", re.IGNORECASE)


def mask_text(text: str, terms: Iterable[Any]) -> tuple[str, int]:
    """Return (masked_text, number_of_matches). Same length as the input text."""
    pattern = _pattern(normalise_terms(terms))
    if pattern is None or not text:
        return text, 0

    count = 0

    def _replace(match: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return MASK_CHAR * len(match.group(0))

    return pattern.sub(_replace, text), count


def load_confidential_terms(conn: Any) -> list[str]:
    """Active confidential terms from rule_patterns. Rows are dict-like, as elsewhere in the app."""
    rows = conn.execute(
        "SELECT pattern FROM rule_patterns WHERE kind = 'confidential_term' AND is_active = TRUE"
    ).fetchall()
    return [row["pattern"] for row in rows if row["pattern"]]
