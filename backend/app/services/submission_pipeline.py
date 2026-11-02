"""Background reading of a submission (phase 2, plan section 5.3).

Order of work:
1. Read the submission and its attachments from the database (short connection).
2. Extract text locally, with no database connection open: DOCX and text files, text PDFs,
   images (RapidOCR), and scanned PDF pages (rendered, then RapidOCR).
3. Confidentiality pre-scan over the title, body, file names and all extracted text, including
   watermarks. A match holds the whole submission: no model call is made, and the routing
   records are written (confidential_routing.py).
4. Text stage: the existing rule and AI text check on the body, then the AI text check on any
   text attachment. Both use the same call budget.
5. Visual stage: images and scanned pages, in batches of up to 4 per call, against the active
   guidelines. Findings are mapped with findings_mapper and saved with their bounding boxes.
6. Save attachment statuses, extracted text and visual facts.

The budget (plan D4) covers every model call for the submission. Calls that do not fit are
reported as not read, and the attachment becomes "partial".

Model calls are made through functions that tests can replace, so CI never calls Gemini.
"""
from __future__ import annotations

import io
import logging
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from psycopg import Connection

from app.ai.vision_client import call_vision
from app.db import connection_context
from app.pipeline.redact import load_confidential_terms
from app.services.ai_check import run_ai_stage
from app.services.checks import run_rule_check
from app.services.confidential_routing import hold_submission
from app.services.document_text import extract_text
from app.services.findings_mapper import to_finding_rows
from app.services.ocr import all_text, read_image_lines, visible_text
from app.services.pdf_render import render_pages
from app.services.pdf_text import extract_page_texts, text_layer_usable
from app.services.prescan import scan_for_confidential
from app.services.vision_check import ImageInput, run_visual_read
from app.services.vision_safeguards import CallBudget

log = logging.getLogger(__name__)

MSG_EXTRACT_FAILED = "The file could not be read."
MSG_VISION_FAILED = "The image could not be checked. Submit again to retry."
MSG_BUDGET = "Not checked: the check limit for this submission was reached."
MSG_NO_GUIDELINES = "No active guidelines apply to this channel, so images were not checked."
MSG_TEXT_FAILED = "The text could not be checked. Submit again to retry."

IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}


@dataclass
class Extracted:
    attachment_id: str
    filename: str
    kind: str
    scan_texts: list[str] = field(default_factory=list)
    visible: list[str] = field(default_factory=list)
    images: list[ImageInput] = field(default_factory=list)
    text_stage: bool = False  # True when the text AI check should read this file's text

    @property
    def text(self) -> str:
        return "\n".join(t for t in self.visible if t)


def _png_bytes(image: Any) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def extract_attachment(att: dict, *, max_pages: int) -> Extracted:
    """Extract text (and images for the model) for one attachment. No database access here."""
    path = Path(att["storage_path"])
    kind = att["kind"]
    ex = Extracted(attachment_id=att["id"], filename=att["filename"], kind=kind)

    if kind in ("docx", "text"):
        extension = ".docx" if kind == "docx" else ".txt"
        text = extract_text(extension, path.read_bytes())
        ex.scan_texts = [text]
        ex.visible = [text] if text.strip() else []
        ex.text_stage = bool(text.strip())
        return ex

    if kind == "image":
        extension = path.suffix.lower()
        lines = read_image_lines(str(path))
        ex.scan_texts = [all_text(lines)]
        ex.visible = visible_text(lines)
        ex.images = [ImageInput(att["id"], IMAGE_MIME.get(extension, "image/png"), path.read_bytes())]
        return ex

    if kind == "pdf":
        page_texts = extract_page_texts(str(path))
        if text_layer_usable(page_texts):
            text = "\n".join(page_texts)
            ex.scan_texts = [text]
            ex.visible = [text]
            ex.text_stage = True
            return ex

        # Scanned PDF: render each page, OCR it, and send the page image to the vision model.
        pages = render_pages(str(path), max_pages)
        with tempfile.TemporaryDirectory() as tmp:
            for index, page in enumerate(pages):
                page_path = Path(tmp) / f"page_{index}.png"
                png = _png_bytes(page)
                page_path.write_bytes(png)
                lines = read_image_lines(str(page_path))
                ex.scan_texts.append(all_text(lines))
                ex.visible.extend(visible_text(lines))
                ex.images.append(ImageInput(att["id"], "image/png", png))
        return ex

    raise ValueError("unknown attachment kind")


# ---------------------------------------------------------------- database helpers

def _load_submission(conn: Connection, content_id: str) -> dict | None:
    return conn.execute(
        "SELECT id, title, kind, channel, body_text, status FROM content WHERE id = %s",
        (content_id,),
    ).fetchone()


def _load_attachments(conn: Connection, content_id: str) -> list[dict]:
    return conn.execute(
        """
        SELECT id, filename, kind, storage_path
        FROM content_attachments
        WHERE content_id = %s AND deleted_at IS NULL AND read_status = 'reading'
        ORDER BY id
        """,
        (content_id,),
    ).fetchall()


def _load_guidelines(conn: Connection, channel: str) -> list[dict]:
    rows = conn.execute(
        """
        SELECT id, title, text, version FROM guidelines
        WHERE is_active AND %s = ANY(applies_to_channels)
        ORDER BY id
        """,
        (channel,),
    ).fetchall()
    return list(rows)


def _insert_text_findings(
    conn: Connection, content_id: str, check_run_id: str, findings: list[dict],
    attachment_id: str,
) -> None:
    """Save text findings from the AI stage that ran on an attachment's text."""
    from uuid import uuid4

    for f in findings:
        finding_id = f"fnd_{uuid4().hex[:12]}"
        source_id = f["sourceId"]
        guideline_id = source_id if source_id.startswith("G-") else None
        conn.execute(
            """
            INSERT INTO findings (
                id, content_id, check_run_id, type, start, "end", bbox,
                severity, title, reason, source_id, source_version, guideline_id,
                suggested_fix, original_text, confidence, ai_generated,
                needs_human_review, status, suggestion_kind
            ) VALUES (%s, %s, %s, %s, NULL, NULL, NULL, %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, 'open', %s)
            """,
            (
                finding_id, content_id, check_run_id, f["type"],
                f["severity"], f["title"], f["reason"], source_id, f["sourceVersion"], guideline_id,
                f["suggestedFix"], f["originalText"] or None,
                max(0.0, min(1.0, float(f["confidence"]))), bool(f.get("aiGenerated", True)),
                bool(f.get("needsHumanReview", False)), f["suggestionKind"],
            ),
        )
        conn.execute(
            "INSERT INTO finding_attachments (finding_id, attachment_id) VALUES (%s, %s)",
            (finding_id, attachment_id),
        )


def _insert_visual_findings(
    conn: Connection, content_id: str, check_run_id: str,
    mapped: list[tuple[dict, list[str]]],
) -> int:
    from uuid import uuid4

    for row, attachment_ids in mapped:
        finding_id = f"fnd_{uuid4().hex[:12]}"
        conn.execute(
            """
            INSERT INTO findings (
                id, content_id, check_run_id, type, start, "end", bbox,
                severity, title, reason, source_id, source_version, guideline_id,
                suggested_fix, original_text, confidence, ai_generated,
                needs_human_review, status, suggestion_kind
            ) VALUES (%s, %s, %s, %s, %s, %s, %s::numeric[],
                      %s, %s, %s, %s, %s, %s,
                      %s, %s, %s, %s,
                      %s, 'open', %s)
            """,
            (
                finding_id, content_id, check_run_id, row["type"],
                row["start"], row["end"], row["bbox"],
                row["severity"], row["title"], row["reason"], row["source_id"],
                row["source_version"], row["guideline_id"],
                row["suggested_fix"], row["original_text"], row["confidence"], row["ai_generated"],
                row["needs_human_review"], row["suggestion_kind"],
            ),
        )
        for attachment_id in attachment_ids:
            conn.execute(
                "INSERT INTO finding_attachments (finding_id, attachment_id) VALUES (%s, %s)",
                (finding_id, attachment_id),
            )
    return len(mapped)


# ---------------------------------------------------------------- the pipeline

def run_submission_pipeline(
    pool: Any,
    content_id: str,
    settings: Any,
    *,
    vision_call: Callable[..., dict] = call_vision,
) -> dict:
    """Read one submission. Safe to run in the background. Returns a short summary."""
    try:
        return _run(pool, content_id, settings, vision_call)
    except Exception:
        # Never log content. Mark every attachment that was being read as failed, so the creator
        # is not left waiting forever.
        log.exception("submission reading failed for %s", content_id)
        with connection_context(pool) as conn, conn.transaction():
            conn.execute(
                """
                UPDATE content_attachments
                   SET read_status = 'failed', read_message = %s
                 WHERE content_id = %s AND read_status = 'reading'
                """,
                (MSG_TEXT_FAILED, content_id),
            )
        return {"contentId": content_id, "status": "failed"}


def _run(pool: Any, content_id: str, settings: Any, vision_call: Callable[..., dict]) -> dict:
    # 1. Read (short connection, closed before any extraction).
    with connection_context(pool) as conn:
        content = _load_submission(conn, content_id)
        if content is None:
            return {"contentId": content_id, "status": "failed"}
        attachments = _load_attachments(conn, content_id)
        terms = load_confidential_terms(conn)
        guidelines = _load_guidelines(conn, content["channel"])

    # 2. Extract locally, no connection open.
    extracted: dict[str, Extracted] = {}
    failed_ids: list[str] = []
    for att in attachments:
        try:
            extracted[att["id"]] = extract_attachment(att, max_pages=settings.submission_max_pdf_pages)
        except Exception:
            log.warning("attachment could not be read for %s", content_id)
            failed_ids.append(att["id"])

    # 3. Pre-scan everything before any model call. A match holds the whole submission.
    file_names = [att["filename"] for att in attachments]
    scan_inputs = [content["title"], content["body_text"], *file_names]
    for ex in extracted.values():
        scan_inputs.extend(ex.scan_texts)
    if scan_for_confidential(scan_inputs, terms)["decision"] == "hold":
        all_ids = [att["id"] for att in attachments]
        with connection_context(pool) as conn, conn.transaction():
            hold_submission(conn, content_id=content_id, attachment_ids=all_ids)
        return {"contentId": content_id, "status": "held"}

    # 4 and 5. Model calls, with one shared budget. The text checks use one connection for their
    # model calls, because the existing rule check (run_rule_check) writes its results on that
    # same connection. This is a known deviation from plan section 5.3, which says no connection
    # is held during a model call. The visual call holds no connection.
    budget = CallBudget(settings.vision_max_calls_per_submission)
    unread_ids: list[str] = []
    text_failed_ids: list[str] = []
    readings_by_attachment: dict[str, list[dict]] = {}
    check_run_id: str | None = None

    with connection_context(pool) as conn:
        body_has_text = bool((content["body_text"] or "").strip())
        if body_has_text:
            budget.consume()
        try:
            result = run_rule_check(conn, content_id, actor=None)
            check_run_id = result["checkRunId"]
        except Exception:
            log.warning("text check failed for %s", content_id)
            check_run_id = None

        if check_run_id is None:
            # Findings need a check run to belong to. Without one, nothing is saved; the
            # creator is told to submit again.
            with conn.transaction():
                conn.execute(
                    """
                    UPDATE content_attachments
                       SET read_status = 'failed', read_message = %s
                     WHERE content_id = %s AND read_status = 'reading'
                    """,
                    (MSG_TEXT_FAILED, content_id),
                )
            return {"contentId": content_id, "status": "failed"}

        for ex in extracted.values():
            if not ex.text_stage:
                continue
            if budget.remaining < 1:
                unread_ids.append(ex.attachment_id)
                continue
            budget.consume()
            try:
                ai = run_ai_stage(conn, ex.text, content["channel"], [], terms)
            except Exception:
                text_failed_ids.append(ex.attachment_id)
                continue
            _insert_text_findings(conn, content_id, check_run_id, ai.findings, ex.attachment_id)

    image_inputs = [img for ex in extracted.values() for img in ex.images]
    vision_failed_ids: list[str] = []
    no_guideline_ids: list[str] = []
    vision_findings = 0
    if image_inputs:
        if not guidelines:
            no_guideline_ids.extend(img.attachment_id for img in image_inputs)
        else:
            guideline_list = [
                {"id": g["id"], "title": g["title"], "text": g["text"]} for g in guidelines
            ]
            visible_texts = [t for ex in extracted.values() for t in ex.visible]
            scan_texts = [t for ex in extracted.values() for t in ex.scan_texts]
            vr = run_visual_read(
                scan_texts=scan_texts,
                visible_texts=visible_texts,
                guidelines=guideline_list,
                images=image_inputs,
                terms=terms,
                model=settings.vision_model,
                api_key=settings.gemini_api_key,
                title=content["title"],
                budget=budget,
                call=vision_call,
            )
            if vr.status == "held":
                # Cannot happen after the pre-scan above, but never save findings for held input.
                with connection_context(pool) as conn, conn.transaction():
                    hold_submission(conn, content_id=content_id,
                                    attachment_ids=[att["id"] for att in attachments])
                return {"contentId": content_id, "status": "held"}

            unread_ids.extend(vr.unread_attachment_ids)
            vision_failed_ids.extend(vr.failed_attachment_ids)
            for fact in vr.facts:
                for att_id in fact.get("attachmentIds", []):
                    readings_by_attachment.setdefault(att_id, []).append(
                        {k: v for k, v in fact.items() if k != "attachmentIds"}
                    )
            if vr.findings:
                versions = {g["id"]: g["version"] for g in guidelines}
                mapped = to_finding_rows(
                    vr.findings,
                    content_id=content_id,
                    check_run_id=check_run_id,
                    visible_text="\n".join(t for t in visible_texts if t),
                    known_guideline_versions=versions,
                )
                with connection_context(pool) as conn, conn.transaction():
                    vision_findings = _insert_visual_findings(conn, content_id, check_run_id, mapped)

    # 6. Save attachment statuses. Text findings were saved above; the visual findings too.
    with connection_context(pool) as conn, conn.transaction():
        for att in attachments:
            att_id = att["id"]
            ex = extracted.get(att_id)
            if att_id in failed_ids:
                status, message = "failed", MSG_EXTRACT_FAILED
            elif att_id in vision_failed_ids:
                status, message = "failed", MSG_VISION_FAILED
            elif att_id in text_failed_ids:
                status, message = "failed", MSG_TEXT_FAILED
            elif att_id in unread_ids:
                status, message = "partial", MSG_BUDGET
            elif att_id in no_guideline_ids:
                status, message = "partial", MSG_NO_GUIDELINES
            else:
                status, message = "ready", ""
            conn.execute(
                """
                UPDATE content_attachments
                   SET read_status = %s, read_message = %s,
                       extracted_text = %s, visual_facts = %s
                 WHERE id = %s
                """,
                (
                    status, message,
                    ex.text[:200_000] if ex else "",
                    _jsonb(readings_by_attachment.get(att_id, [])),
                    att_id,
                ),
            )

    return {
        "contentId": content_id,
        "status": "read",
        "checkRunId": check_run_id,
        "visionFindings": vision_findings,
        "modelCalls": budget.used,
    }


def _jsonb(value: Any) -> Any:
    from psycopg.types.json import Jsonb

    return Jsonb(value)
