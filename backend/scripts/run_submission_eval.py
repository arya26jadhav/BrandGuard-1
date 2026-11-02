"""Runs the labelled submissions through the real reading pipeline (plan section 12.2, runbook 6).

    python scripts/run_submission_eval.py ..\\tests\\quality\\submissions\\manifest.json results.json

Requires, in the environment or backend/.env:
- DATABASE_URL: a DISPOSABLE database with schema.sql, migrations 002 to 007 and the guideline
  seeds loaded. Never use the brandguard database. The run deletes earlier evaluation rows.
- GEMINI_API_KEY and BRANDGUARD_VISION_MODEL (a model that accepts images; see check_vision_model.py).

Text items are checked as the body of a script or marketing idea. Image items are attached as
files. Each item goes through run_submission_pipeline, the same code the API uses.

results.json maps each manifest id to {"status", "findings"} in the format that
score_submissions.py reads. A held item has status "held".
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

EVAL_OWNER_ID = "u-eval-creator"
EVAL_PREFIX = "cnt_eval_"


def _connection_pool(database_url: str) -> ConnectionPool:
    if conninfo_to_dict(database_url).get("dbname") == "brandguard":
        raise SystemExit("Refusing to run the evaluation against the brandguard database. Use a disposable one.")
    return ConnectionPool(conninfo=database_url, kwargs={"row_factory": dict_row}, open=True)


def _ensure_owner(conn: Any) -> None:
    conn.execute(
        """INSERT INTO users (id, name, role, team)
           VALUES (%s, 'Evaluation creator', 'creator', 'Marketing')
           ON CONFLICT (id) DO NOTHING""",
        (EVAL_OWNER_ID,),
    )


def _clear_previous(conn: Any) -> None:
    conn.execute("DELETE FROM content WHERE owner_id = %s", (EVAL_OWNER_ID,))


def _insert_item(conn: Any, item: dict, files_dir: Path, storage_dir: Path) -> tuple[str, str]:
    """Create the content row and its attachment(s). Returns (content_id, attachment_id or '')."""
    from app.services.attachments import sha256_bytes, storage_path

    content_id = f"{EVAL_PREFIX}{item['id'].lower()}_{uuid4().hex[:6]}"
    data = (files_dir / item["file"]).read_bytes()  # manifest paths are relative to its folder
    text = data.decode("utf-8") if item["file"].endswith(".txt") else ""
    conn.execute(
        """INSERT INTO content (id, title, channel, team, owner_id, status, body_text, kind)
           VALUES (%s, %s, 'General', 'Marketing', %s, 'Draft', %s, %s)""",
        (content_id, f"Eval {item['id']}", EVAL_OWNER_ID, text, item["kind"]),
    )
    attachment_id = ""
    if item["file"].endswith(".png"):
        name = Path(item["file"]).name
        row = conn.execute(
            """INSERT INTO content_attachments (content_id, filename, mime_type, kind, size_bytes,
                                                sha256, storage_path, read_status)
               VALUES (%s, %s, 'image/png', 'image', %s, %s, '', 'reading') RETURNING id""",
            (content_id, name, len(data), sha256_bytes(data)),
        ).fetchone()
        attachment_id = row["id"]
        path = storage_path(storage_dir, content_id, attachment_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        conn.execute("UPDATE content_attachments SET storage_path = %s WHERE id = %s", (str(path), attachment_id))
    return content_id, attachment_id


def _read_outcome(conn: Any, content_id: str) -> dict:
    content = conn.execute("SELECT status FROM content WHERE id = %s", (content_id,)).fetchone()
    held = content is not None and content["status"] == "In Review"
    if held:
        return {"status": "held", "findings": []}
    rows = conn.execute(
        """SELECT f.guideline_id, f.title, f.reason, f.original_text, f.type
           FROM findings f
           WHERE f.content_id = %s AND f.type <> 'security'
             AND f.check_run_id = (SELECT id FROM check_runs WHERE content_id = %s
                                   ORDER BY started_at DESC LIMIT 1)""",
        (content_id, content_id),
    ).fetchall()
    findings = [
        {
            "guidelineId": r["guideline_id"],
            "title": r["title"],
            "reason": r["reason"],
            "originalText": r["original_text"] or "",
            "type": r["type"],
        }
        for r in rows
        if r["guideline_id"]
    ]
    return {"status": "ready", "findings": findings}


def run_evaluation(
    manifest: dict,
    files_dir: Path,
    pool: ConnectionPool,
    settings: Any,
    *,
    vision_call: Callable[..., dict] | None = None,
) -> dict:
    """Run every manifest item through the pipeline. Returns the results mapping."""
    from app.ai.vision_client import call_vision
    from app.services.submission_pipeline import run_submission_pipeline

    vision = vision_call or call_vision
    results: dict[str, dict] = {}
    with tempfile.TemporaryDirectory() as tmp:
        storage_dir = Path(tmp)
        with pool.connection() as conn, conn.transaction():
            _ensure_owner(conn)
            _clear_previous(conn)
        for item in manifest["submissions"]:
            with pool.connection() as conn, conn.transaction():
                content_id, _attachment = _insert_item(conn, item, files_dir, storage_dir)
            run_submission_pipeline(pool, content_id, settings, vision_call=vision)
            with pool.connection() as conn:
                results[item["id"]] = _read_outcome(conn, content_id)
    return results


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    from app.config import get_settings

    manifest_path = Path(argv[0])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    settings = get_settings()
    pool = _connection_pool(settings.database_url)
    try:
        results = run_evaluation(manifest, manifest_path.parent, pool, settings)
    finally:
        pool.close()
    Path(argv[1]).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(results)} results to {argv[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))