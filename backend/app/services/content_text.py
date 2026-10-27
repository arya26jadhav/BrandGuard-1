"""Helpers for turning plain post text into the body_html stored alongside it."""
from __future__ import annotations

import html


def plain_text_to_html(text: str) -> str:
    """One paragraph per line, escaped. Replace with editor HTML if the editor needs it."""
    return "".join(f"<p>{html.escape(line)}</p>" for line in text.split("\n"))
