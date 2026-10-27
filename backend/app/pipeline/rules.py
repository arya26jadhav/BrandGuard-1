"""Rule matching for phrase, regex, glossary and required-text rules.

Accepted JSON root formats: a list of rule objects, or {"rules": [...]}.
Rule fields: id, pattern/phrase/regex, type (phrase|regex|confidential|avoid_term|required_text),
severity_default/severity, title, reason, suggested_fix, source_id, source_version,
required_channels, approved_name, avoid_terms, replacement.
"""
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any
from .normalise import normalise_with_offsets, original_span

_CACHE: dict[str, tuple[tuple[int, int], list[dict[str, Any]]]] = {}

def invalidate_rule_cache(path: str | Path | None = None) -> None:
    if path is None:
        _CACHE.clear()
    else:
        _CACHE.pop(str(Path(path).resolve()), None)

def load_rules(path: str | Path) -> list[dict[str, Any]]:
    resolved = Path(path).resolve()
    stat = resolved.stat()
    stamp = (stat.st_mtime_ns, stat.st_size)
    key = str(resolved)
    if key not in _CACHE or _CACHE[key][0] != stamp:
        data = json.loads(resolved.read_text(encoding="utf-8"))
        rules = data if isinstance(data, list) else data.get("rules", [])
        if not isinstance(rules, list):
            raise ValueError("Rule file must contain a list or a 'rules' list")
        _CACHE[key] = (stamp, rules)
    return _CACHE[key][1]

def _finding(rule: dict, content_id: str, start: int | None, end: int | None,
             original: str, suggested: str = "") -> dict:
    return {
        "id": None, "contentId": content_id, "type": rule.get("finding_type", rule.get("type", "rule")),
        "start": start, "end": end, "bbox": None,
        "severity": str(rule.get("severity_default", rule.get("severity", "warning"))).lower(),
        "title": rule.get("title", rule.get("name", "Brand rule match")),
        "reason": rule.get("reason", rule.get("description", "Matched a configured brand rule.")),
        "sourceId": str(rule.get("source_id", rule.get("id", ""))),
        "sourceVersion": int(rule.get("source_version", rule.get("version", 1))),
        "originalText": original, "suggestedFix": suggested or rule.get("suggested_fix", ""),
        "confidence": float(rule.get("confidence", 1.0)),
        "aiGenerated": False, "needsHumanReview": bool(rule.get("needs_human_review", False)),
        "status": "open", "suggestionKind": rule.get("suggestion_kind", "Terminology change"),
    }

def run_rules(text: str, content_id: str, rules: list[dict[str, Any]]) -> list[dict]:
    normalized = normalise_with_offsets(text)
    findings: list[dict] = []
    for rule in rules:
        kind = str(rule.get("type", "phrase")).lower()
        patterns: list[str] = []
        if kind in {"phrase", "confidential", "avoid_term", "glossary", "name_variant"}:
            raw = rule.get("patterns", rule.get("avoid_terms", rule.get("pattern", rule.get("phrase", []))))
            patterns = [raw] if isinstance(raw, str) else list(raw or [])
            approved = rule.get("approved_name")
            for pattern in patterns:
                if not pattern:
                    continue
                needle = normalise_with_offsets(str(pattern)).text
                if not needle:
                    continue
                start_at = 0
                while True:
                    pos = normalized.text.find(needle, start_at)
                    if pos < 0:
                        break
                    end_pos = pos + len(needle)
                    before = normalized.text[pos - 1] if pos else " "
                    after = normalized.text[end_pos] if end_pos < len(normalized.text) else " "
                    whole_word = not before.isalnum() and before != "_" and not after.isalnum() and after != "_"
                    if kind in {"avoid_term", "glossary", "name_variant"} and not whole_word:
                        start_at = pos + 1
                        continue
                    start, end = original_span(normalized, pos, end_pos)
                    original = text[start:end]
                    # A variant is ignored when it occurs inside the approved full product name.
                    if approved and kind == "name_variant":
                        approved_norm = normalise_with_offsets(str(approved)).text
                        if approved_norm in normalized.text[max(0, pos-len(approved_norm)):min(len(normalized.text), end_pos+len(approved_norm))]:
                            start_at = pos + 1
                            continue
                    replacement = rule.get("replacement", rule.get("suggested_fix", ""))
                    if replacement and original.isupper(): replacement = str(replacement).upper()
                    elif replacement and original[:1].isupper(): replacement = str(replacement)[:1].upper() + str(replacement)[1:]
                    finding_type = "security" if kind == "confidential" else rule.get("finding_type", "rule")
                    adapted = {**rule, "type": finding_type}
                    if kind == "confidential": adapted["severity_default"] = "critical"
                    findings.append(_finding(adapted, content_id, start, end, original, str(replacement or "")))
                    start_at = pos + max(1, len(needle))
        elif kind == "regex":
            expression = rule.get("regex", rule.get("pattern", ""))
            try:
                matches = re.finditer(str(expression), text, re.IGNORECASE)
                for match in matches:
                    findings.append(_finding(rule, content_id, match.start(), match.end(), match.group(0), str(rule.get("replacement", rule.get("suggested_fix", "")))))
            except re.error as exc:
                raise ValueError(f"Invalid regex in rule {rule.get('id', '<unknown>')}: {exc}") from exc
        elif kind in {"required_text", "disclaimer"}:
            channels = rule.get("required_channels", rule.get("channels", []))
            channel = rule.get("_channel")
            if channels and channel and channel not in channels:
                continue
            required = str(rule.get("required_text", rule.get("pattern", "")))
            if required and normalise_with_offsets(required).text not in normalized.text:
                findings.append(_finding(rule, content_id, None, None, "", required))
    # Exact duplicate and overlapping matches from the same source are collapsed.
    findings.sort(key=lambda f: (f["start"] is None, f["start"] or -1, -(f["end"] or 0), f["sourceId"]))
    deduped: list[dict] = []
    seen = set()
    for item in findings:
        key = (item["sourceId"], item["start"], item["end"], item["title"])
        if key in seen: continue
        seen.add(key)
        if item["start"] is not None and any(old["start"] is not None and old["start"] < item["end"] and old["end"] > item["start"] and old["sourceId"] == item["sourceId"] for old in deduped):
            continue
        deduped.append(item)
    return deduped

def run_rule_file(text: str, content_id: str, path: str | Path, channel: str | None = None) -> list[dict]:
    rules = [dict(rule, _channel=channel) for rule in load_rules(path)]
    return run_rules(text, content_id, rules)
