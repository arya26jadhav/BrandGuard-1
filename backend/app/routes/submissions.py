"""Submission endpoints (phase 2, plan section 6, contract phase2_contract.md).

A submission is a content row with a kind. Its files are attachments. Reading happens in the
background (services/submission_pipeline.py). Findings are read with the existing endpoint
GET /api/content/{id}/findings.

Who can do what (plan section 10):
- creators see and change only their own submissions;
- reviewers see every submission but change none;
- managers and admins see and change every submission.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from psycopg import Connection
from psycopg.types.json import Jsonb
from pypdf import PdfReader

from app.config import get_settings
from app.db import get_conn
from app.security import current_user
from app.services import attachments as att_rules
from app.services.checks import BLOCKED_STATUSES
from app.services.confidential_routing import HOLD_MESSAGE
from app.services.submission_pipeline import run_submission_pipeline

router = APIRouter(prefix="/api/submissions", tags=["submissions"])

KINDS = ("post", "script", "marketing_idea", "design", "image")
CHANNELS = ("Website", "Instagram", "Email", "Ad", "General")
TEAMS = ("Marketing", "Sales", "Brand", "Legal", "Product", "Design", "HR", "Support")
MIME_BY_KIND = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}
WRITE_ROLES = ("creator", "manager", "admin")
VIEW_ROLES = ("creator", "reviewer", "manager", "admin")


class SubmissionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    kind: Literal["post", "script", "marketing_idea", "design", "image"]
    team: Literal["Marketing", "Sales", "Brand", "Legal", "Product", "Design", "HR", "Support"]
    channel: Literal["Website", "Instagram", "Email", "Ad", "General"]
    bodyText: str = Field(default="", max_length=50_000)


# ---------------------------------------------------------------- access

def _load_content(conn: Connection, content_id: str) -> dict:
    row = conn.execute(
        """
        SELECT id, owner_id, status, kind, channel, team, title, body_text,
               created_at, updated_at
        FROM content WHERE id = %s
        """,
        (content_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return row


def _can_view(user: dict, owner_id: str) -> bool:
    return user["role"] != "creator" or owner_id == user["id"]


def _can_change(user: dict, owner_id: str) -> bool:
    if user["role"] in ("manager", "admin"):
        return True
    return user["role"] == "creator" and owner_id == user["id"]


def _require_view(user: dict, owner_id: str) -> None:
    if user["role"] not in VIEW_ROLES or not _can_view(user, owner_id):
        raise HTTPException(status_code=403, detail="You can only access your own submissions")


def _require_change(user: dict, owner_id: str) -> None:
    if user["role"] not in WRITE_ROLES or not _can_change(user, owner_id):
        raise HTTPException(status_code=403, detail="You can only change your own submissions")


# ---------------------------------------------------------------- serialising

def _attachment_out(row: dict) -> dict:
    return {
        "id": row["id"],
        "contentId": row["content_id"],
        "filename": row["filename"],
        "mimeType": row["mime_type"],
        "kind": row["kind"],
        "sizeBytes": row["size_bytes"],
        "sha256": row["sha256"],
        "pageCount": row["page_count"],
        "readStatus": row["read_status"],
        "readMessage": row["read_message"],
        "uploadedBy": row["uploaded_by_name"] or "",
        "uploadedAt": row["uploaded_at"].isoformat(),
    }


def _attachments(conn: Connection, content_id: str) -> list[dict]:
    return conn.execute(
        """
        SELECT a.id, a.content_id, a.filename, a.mime_type, a.kind, a.size_bytes, a.sha256,
               a.page_count, a.read_status, a.read_message, a.uploaded_at,
               u.name AS uploaded_by_name
        FROM content_attachments a
        LEFT JOIN users u ON u.id = a.uploaded_by
        WHERE a.content_id = %s AND a.deleted_at IS NULL
        ORDER BY a.id
        """,
        (content_id,),
    ).fetchall()


def _submission_out(conn: Connection, row: dict) -> dict:
    attachments = _attachments(conn, row["id"])
    summary = {"attachments": len(attachments), "pending": 0, "reading": 0, "ready": 0,
               "held": 0, "failed": 0, "partial": 0}
    for a in attachments:
        summary[a["read_status"]] += 1
    held = summary["held"] > 0
    owner = conn.execute("SELECT name FROM users WHERE id = %s", (row["owner_id"],)).fetchone()
    return {
        "id": row["id"],
        "title": row["title"],
        "kind": row["kind"],
        "channel": row["channel"],
        "team": row["team"],
        "status": row["status"],
        "bodyText": row["body_text"],
        "ownerId": row["owner_id"],
        "ownerName": owner["name"] if owner else "",
        "readSummary": summary,
        "hold": (
            {"reason": "confidential_term", "routedTo": "manager", "message": HOLD_MESSAGE}
            if held else None
        ),
        "createdAt": row["created_at"].isoformat(),
        "updatedAt": row["updated_at"].isoformat(),
    }


# ---------------------------------------------------------------- submissions

@router.get("")
def list_submissions(
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> list[dict]:
    if user["role"] not in VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Not allowed")
    if user["role"] == "creator":
        rows = conn.execute(
            "SELECT * FROM content WHERE kind <> 'post' AND owner_id = %s ORDER BY created_at DESC",
            (user["id"],),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM content WHERE kind <> 'post' ORDER BY created_at DESC"
        ).fetchall()
    return [_submission_out(conn, r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    if user["role"] not in WRITE_ROLES:
        raise HTTPException(status_code=403, detail="Not allowed to create a submission")

    content_id = "cnt_" + uuid4().hex[:12]
    version_id = "ver_" + uuid4().hex[:12]
    body = payload.bodyText.strip()
    with conn.transaction():
        conn.execute(
            """
            INSERT INTO content (id, title, channel, team, owner_id, status, body_text, kind)
            VALUES (%s, %s, %s, %s, %s, 'Draft', %s, %s)
            """,
            (content_id, payload.title.strip(), payload.channel, payload.team, user["id"],
             body, payload.kind),
        )
        conn.execute(
            """
            INSERT INTO content_versions
                (id, content_id, version, body_text, change_type, actor_id, actor_label, note)
            VALUES (%s, %s, 1, %s, 'initial', %s, %s, 'Submission created')
            """,
            (version_id, content_id, body, user["id"], user["name"]),
        )
        conn.execute(
            """
            INSERT INTO revisions (id, content_id, actor_id, actor_label, kind, action, detail)
            VALUES (%s, %s, %s, %s, 'person', 'Submission created', %s)
            """,
            ("rev_" + uuid4().hex[:12], content_id, user["id"], user["name"], payload.kind),
        )
    row = _load_content(conn, content_id)
    return _submission_out(conn, row)


@router.get("/{submission_id}")
def get_submission(
    submission_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    row = _load_content(conn, submission_id)
    _require_view(user, row["owner_id"])
    return _submission_out(conn, row)


# ---------------------------------------------------------------- attachments

@router.get("/{submission_id}/attachments")
def list_attachments(
    submission_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> list[dict]:
    row = _load_content(conn, submission_id)
    _require_view(user, row["owner_id"])
    return [_attachment_out(a) for a in _attachments(conn, submission_id)]


@router.post("/{submission_id}/attachments", status_code=status.HTTP_201_CREATED, response_model=None)
async def upload_attachment(
    submission_id: str,
    file: UploadFile = File(...),
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> Response:
    settings = get_settings()
    row = _load_content(conn, submission_id)
    _require_change(user, row["owner_id"])
    if row["status"] in BLOCKED_STATUSES:
        raise HTTPException(status_code=409, detail=f"Files cannot change while the submission is {row['status']}")

    max_bytes = settings.submission_max_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    filename = att_rules.safe_filename(file.filename or "")
    existing = _attachments(conn, submission_id)

    try:
        kind = att_rules.validate_upload(
            filename, len(data), len(existing),
            max_bytes=max_bytes, max_files=settings.submission_max_files,
        )
    except att_rules.UploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    digest = att_rules.sha256_bytes(data)
    existing_digests = {}
    for a in existing:
        existing_digests[a["id"]] = a["sha256"]
    duplicate = att_rules.find_duplicate(existing_digests, digest)
    if duplicate is not None:
        existing_row = next(a for a in existing if a["id"] == duplicate)
        return JSONResponse(status_code=200, content=_attachment_out(existing_row))

    page_count = 1
    if kind == "pdf":
        try:
            page_count = len(PdfReader(io.BytesIO(data)).pages)
        except Exception:
            raise HTTPException(status_code=422, detail="The PDF could not be read")
        try:
            att_rules.validate_pdf_pages(page_count, max_pages=settings.submission_max_pdf_pages)
        except att_rules.UploadError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    extension = att_rules.extension_of(filename)
    with conn.transaction():
        inserted = conn.execute(
            """
            INSERT INTO content_attachments
                (content_id, filename, mime_type, kind, size_bytes, sha256, storage_path,
                 page_count, uploaded_by)
            VALUES (%s, %s, %s, %s, %s, %s, '', %s, %s)
            RETURNING id
            """,
            (submission_id, filename, MIME_BY_KIND[extension], kind, len(data), digest,
             page_count, user["id"]),
        ).fetchone()
        attachment_id = inserted["id"]
        path = att_rules.storage_path(settings.image_storage_dir, submission_id, attachment_id, filename)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        conn.execute(
            "UPDATE content_attachments SET storage_path = %s WHERE id = %s",
            (str(path), attachment_id),
        )
    created = conn.execute(
        """
        SELECT a.id, a.content_id, a.filename, a.mime_type, a.kind, a.size_bytes, a.sha256,
               a.page_count, a.read_status, a.read_message, a.uploaded_at,
               u.name AS uploaded_by_name
        FROM content_attachments a LEFT JOIN users u ON u.id = a.uploaded_by
        WHERE a.id = %s
        """,
        (attachment_id,),
    ).fetchone()
    return JSONResponse(status_code=201, content=_attachment_out(created))


@router.get("/{submission_id}/attachments/{attachment_id}/file")
def get_attachment_file(
    submission_id: str,
    attachment_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> FileResponse:
    row = _load_content(conn, submission_id)
    _require_view(user, row["owner_id"])
    att = conn.execute(
        """SELECT storage_path, mime_type, filename, read_status FROM content_attachments
           WHERE id = %s AND content_id = %s AND deleted_at IS NULL""",
        (attachment_id, submission_id),
    ).fetchone()
    if att is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    # A creator never gets a held file. Managers and admins can open it for review.
    if user["role"] == "creator" and att["read_status"] == "held":
        raise HTTPException(status_code=404, detail="Attachment not found")
    path = Path(att["storage_path"]).resolve()
    base = Path(get_settings().image_storage_dir).resolve()
    if base not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Attachment not found")
    return FileResponse(path, media_type=att["mime_type"], filename=att["filename"])


@router.delete("/{submission_id}/attachments/{attachment_id}", status_code=204)
def delete_attachment(
    submission_id: str,
    attachment_id: str,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> Response:
    row = _load_content(conn, submission_id)
    _require_change(user, row["owner_id"])
    if row["status"] in BLOCKED_STATUSES:
        raise HTTPException(status_code=409, detail=f"Files cannot change while the submission is {row['status']}")
    with conn.transaction():
        result = conn.execute(
            """
            UPDATE content_attachments SET deleted_at = now()
             WHERE id = %s AND content_id = %s AND deleted_at IS NULL
            """,
            (attachment_id, submission_id),
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Attachment not found")
    return Response(status_code=204)


# ---------------------------------------------------------------- submit

@router.post("/{submission_id}/submit", status_code=202)
def submit_for_checking(
    submission_id: str,
    request: Request,
    background: BackgroundTasks,
    conn: Connection = Depends(get_conn),
    user: dict = Depends(current_user),
) -> dict:
    row = _load_content(conn, submission_id)
    _require_change(user, row["owner_id"])
    if row["status"] in BLOCKED_STATUSES:
        raise HTTPException(status_code=409, detail=f"Cannot check a submission in status {row['status']}")

    attachments = _attachments(conn, submission_id)
    if any(a["read_status"] == "reading" for a in attachments):
        raise HTTPException(status_code=409, detail="This submission is already being checked")
    if not attachments and not (row["body_text"] or "").strip():
        raise HTTPException(status_code=409, detail="Add some text or a file before checking")

    queued_ids = [a["id"] for a in attachments if a["read_status"] != "held"]
    check_run_id = "chk_" + uuid4().hex[:12]
    with conn.transaction():
        # A queued check run, so the response can name it. The pipeline writes its findings to
        # the check run it creates itself, which is newer, so the findings endpoint reads those.
        conn.execute(
            """
            INSERT INTO check_runs (id, content_id, rules_count, ai_count, rules_only_fallback, metadata)
            VALUES (%s, %s, 0, 0, FALSE, %s)
            """,
            (check_run_id, submission_id, Jsonb({"aiStatus": "queued"})),
        )
        conn.execute(
            """
            UPDATE content_attachments
               SET read_status = 'reading', read_message = ''
             WHERE content_id = %s AND deleted_at IS NULL AND read_status <> 'held'
            """,
            (submission_id,),
        )
    settings = get_settings()
    background.add_task(run_submission_pipeline, request.app.state.db_pool, submission_id, settings)
    return {"submissionId": submission_id, "checkRunId": check_run_id, "queued": len(queued_ids)}
