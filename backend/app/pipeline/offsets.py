"""Calculate downstream finding offset changes after an edit."""
from dataclasses import dataclass

@dataclass(frozen=True)
class OffsetUpdate:
    finding_id: str
    start: int | None
    end: int | None
    status: str

def calculate_offset_updates(findings: list[dict], edited_finding_id: str, edit_start: int | None,
                             edit_end: int | None, replacement: str) -> list[OffsetUpdate]:
    if edit_start is None or edit_end is None:
        return []
    if edit_start < 0 or edit_end < edit_start:
        raise ValueError("Invalid edited span")
    delta = len(replacement) - (edit_end - edit_start)
    updates: list[OffsetUpdate] = []
    for finding in findings:
        if str(finding.get("id")) == str(edited_finding_id):
            continue
        start, end = finding.get("start"), finding.get("end")
        status = finding.get("status", "open")
        if start is None or end is None or status != "open":
            continue
        if start < edit_end and end > edit_start:
            updates.append(OffsetUpdate(str(finding["id"]), start, end, "resolved"))
        elif start >= edit_end:
            updates.append(OffsetUpdate(str(finding["id"]), start + delta, end + delta, status))
    return updates
