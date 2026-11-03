"""Phase 2 integration tests: submission API, holds, reading pipeline and budget.

Runs against DATABASE_URL, in a throwaway database built from data/schema.sql and the
migrations. Skipped when DATABASE_URL is unset. The model is never called: the vision and
text stages are replaced with fakes, and OCR is replaced with an empty result.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

# The app reads settings at import time, so provide placeholders before importing it.
os.environ.setdefault("JWT_SECRET", "test-secret-for-phase2")
os.environ.setdefault("DATABASE_URL", "postgresql://unused@localhost/unused")

import psycopg  # noqa: E402
from psycopg import sql  # noqa: E402
from psycopg.conninfo import conninfo_to_dict, make_conninfo  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import ConnectionPool  # noqa: E402

from app.ai.vision_client import VisionError  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.security import create_access_token  # noqa: E402
from app.services import submission_pipeline as pipeline  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SECRET_TERM = "Project Nightingale"

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URL", "").endswith("/unused"),
    reason="DATABASE_URL is unset",
)

def _with_database(url: str, dbname: str) -> str:
    params = conninfo_to_dict(url)
    params["dbname"] = dbname
    return make_conninfo(**params)



def _png(color: tuple[int, int, int]) -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), color).save(buffer, "PNG")
    return buffer.getvalue()


def _with_database(url: str, dbname: str) -> str:
    """The same server as url, pointed at another database. Works with postgresql:// URLs."""
    params = conninfo_to_dict(url)
    params["dbname"] = dbname
    return make_conninfo(**params)


@pytest.fixture
def dsn():
    """A throwaway database with schema.sql and migrations 002 to 007 applied."""
    base = os.environ["DATABASE_URL"]
    name = f"bg_p2_{uuid4().hex[:10]}"
    with psycopg.connect(_with_database(base, "postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    test_url = _with_database(base, name)
    try:
        with psycopg.connect(test_url, autocommit=True) as conn:
            conn.execute((REPO_ROOT / "data" / "schema.sql").read_text(encoding="utf-8-sig"))
            for path in sorted((REPO_ROOT / "data" / "migrations").glob("*.sql")):
                if path.name.startswith("001"):
                    continue  # phase 1 file, not part of the phase 2 chain
                conn.execute(path.read_text(encoding="utf-8-sig"))
            conn.execute(
                "INSERT INTO rule_patterns (id, kind, pattern) VALUES ('RP-TEST', 'confidential_term', %s)",
                (SECRET_TERM,),
            )
        yield test_url
    finally:
        with psycopg.connect(_with_database(base, "postgres"), autocommit=True) as admin:
            admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name)))


@pytest.fixture
def users(dsn):
    ids = {"creator": "u-creator", "other": "u-other", "manager": "u-manager",
           "reviewer": "u-reviewer", "admin": "u-admin"}
    roles = {"creator": "creator", "other": "creator", "manager": "manager",
             "reviewer": "reviewer", "admin": "admin"}
    with psycopg.connect(dsn, autocommit=True) as conn:
        for key, uid in ids.items():
            conn.execute(
                "INSERT INTO users (id, name, role, team) VALUES (%s, %s, %s, 'Marketing')",
                (uid, key.title(), roles[key]),
            )
        conn.execute(
            """INSERT INTO guidelines (id, short_name, title, text, category, severity,
                                       applies_to_channels, version, is_active)
               VALUES ('G-TEST', 'Logo size', 'Logo size',
                       'The logo must be at least 40 pixels high.', 'Brand Assets', 'warning',
                       ARRAY['General'], 1, TRUE)"""
        )
    return {key: {"id": uid, "role": roles[key], "team": "Marketing", "name": key.title()}
            for key, uid in ids.items()}


@pytest.fixture
def settings_for(tmp_path):
    def make(budget: int = 10) -> SimpleNamespace:
        return SimpleNamespace(
            vision_model="gemini-flash-latest",
            gemini_api_key="test-key",
            vision_max_calls_per_submission=budget,
            submission_max_pdf_pages=20,
            image_storage_dir=str(tmp_path / "files"),
        )
    return make


@pytest.fixture
def pool(dsn):
    p = ConnectionPool(conninfo=dsn, kwargs={"row_factory": dict_row}, open=True)
    yield p
    p.close()


@pytest.fixture
def client(dsn, tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import app

    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setenv("JWT_SECRET", "test-secret-for-phase2")
    monkeypatch.setenv("IMAGE_STORAGE_DIR", str(tmp_path / "files"))
    get_settings.cache_clear()
    with TestClient(app) as c:
        yield c
    get_settings.cache_clear()


def _auth(user: dict) -> dict:
    token = create_access_token(user["id"], user["role"], user["team"])
    return {"Authorization": f"Bearer {token}"}


def _create_submission(client, user, *, kind="script", channel="General", body="Hook: protect your skin."):
    response = client.post(
        "/api/submissions",
        json={"title": "Summer script", "kind": kind, "team": "Marketing",
              "channel": channel, "bodyText": body},
        headers=_auth(user),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _upload(client, user, submission_id, name: str, data: bytes):
    return client.post(
        f"/api/submissions/{submission_id}/attachments",
        files={"file": (name, data, "image/png")},
        headers=_auth(user),
    )


def _add_image(dsn, settings, submission_id: str, data: bytes, name: str = "banner.png") -> str:
    """Insert a ready-to-read image attachment directly (faster than the upload route)."""
    from app.services.attachments import sha256_bytes, storage_path

    with psycopg.connect(dsn, autocommit=True) as conn:
        att_id = conn.execute(
            """INSERT INTO content_attachments (content_id, filename, mime_type, kind, size_bytes,
                                                sha256, storage_path, read_status)
               VALUES (%s, %s, 'image/png', 'image', %s, %s, '', 'reading') RETURNING id""",
            (submission_id, name, len(data), sha256_bytes(data)),
        ).fetchone()[0]
        path = storage_path(settings.image_storage_dir, submission_id, att_id, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        conn.execute("UPDATE content_attachments SET storage_path = %s WHERE id = %s", (str(path), att_id))
    return att_id


def _fake_rule_check(dsn, calls: list):
    def fake(conn, content_id, actor):
        calls.append(content_id)
        check_id = f"chk_{uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO check_runs (id, content_id, rules_count, ai_count, rules_only_fallback, metadata)
               VALUES (%s, %s, 0, 0, FALSE, '{}')""",
            (check_id, content_id),
        )
        return {"checkRunId": check_id}
    return fake


def _vision_reply(attachment_guideline: str = "G-TEST"):
    def fake(model, api_key, system, user_text, images):
        return {
            "facts": [{"id": "F1", "kind": "logo", "value": "logo present",
                       "bbox": [0.1, 0.1, 0.2, 0.2], "confidence": 0.9}],
            "findings": [{"factIds": ["F1"], "type": "visual", "severity": "warning",
                          "title": "Logo too small", "reason": "The logo is below the minimum.",
                          "guidelineId": attachment_guideline, "suggestedFix": "Enlarge the logo.",
                          "confidence": 0.8}],
            "notFound": [],
        }
    return fake


# ---------------------------------------------------------------- API rules

def test_create_and_read_submission_respects_ownership(client, users):
    created = _create_submission(client, users["creator"])
    assert created["kind"] == "script" and created["channel"] == "General"
    assert created["ownerId"] == users["creator"]["id"]

    assert client.get(f"/api/submissions/{created['id']}", headers=_auth(users["creator"])).status_code == 200
    assert client.get(f"/api/submissions/{created['id']}", headers=_auth(users["other"])).status_code == 403
    assert client.get(f"/api/submissions/{created['id']}", headers=_auth(users["manager"])).status_code == 200
    assert client.get(f"/api/submissions/{created['id']}", headers=_auth(users["reviewer"])).status_code == 200


def test_upload_rules_and_duplicate_detection(client, users):
    sub = _create_submission(client, users["creator"])
    first = _upload(client, users["creator"], sub["id"], "a.png", _png((200, 30, 30)))
    assert first.status_code == 201, first.text
    assert first.json()["readStatus"] == "pending"

    same = _upload(client, users["creator"], sub["id"], "copy.png", _png((200, 30, 30)))
    assert same.status_code == 200 and same.json()["id"] == first.json()["id"]

    assert _upload(client, users["creator"], sub["id"], "x.exe", b"abc").status_code == 415
    assert _upload(client, users["creator"], sub["id"], "empty.png", b"").status_code == 422

    listed = client.get(f"/api/submissions/{sub['id']}/attachments", headers=_auth(users["creator"]))
    assert len(listed.json()) == 1


def test_held_submission_is_hidden_from_creator(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], body=f"Launch copy about {SECRET_TERM}.")
    _add_image(dsn, settings_for(), sub["id"], _png((10, 10, 10)))

    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    rule_calls, vision_calls = [], []
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, rule_calls))

    summary = pipeline.run_submission_pipeline(
        pool, sub["id"], settings_for(), vision_call=lambda *a, **k: vision_calls.append(1) or {}
    )
    assert summary["status"] == "held"
    assert rule_calls == [] and vision_calls == [], "a held submission must make no model call"

    creator_view = client.get(f"/api/submissions/{sub['id']}", headers=_auth(users["creator"])).json()
    assert creator_view["hold"]["routedTo"] == "manager"
    # The creator's own body text is echoed back as they typed it. The system must not add the
    # term anywhere else: not in the hold notice, the read summary, or the findings.
    assert SECRET_TERM not in str(creator_view["hold"])
    assert SECRET_TERM not in str(creator_view["readSummary"])

    findings = client.get(f"/api/content/{sub['id']}/findings", headers=_auth(users["creator"])).json()
    assert findings == [], "creators must not see findings for a held submission"
    assert SECRET_TERM not in str(findings)

    manager_findings = client.get(f"/api/content/{sub['id']}/findings", headers=_auth(users["manager"])).json()
    assert any(f["type"] == "security" for f in manager_findings)
    assert SECRET_TERM not in str(manager_findings)

    with psycopg.connect(dsn, autocommit=True) as conn:
        status = conn.execute("SELECT status, assigned_reviewer_id FROM content WHERE id = %s", (sub["id"],)).fetchone()
        alert = conn.execute("SELECT kind, priority FROM alerts WHERE content_id = %s", (sub["id"],)).fetchone()
    assert status == ("In Review", users["manager"]["id"])
    assert alert == ("confidential_review", "High")


def test_image_read_saves_visual_findings_and_facts(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], kind="image", channel="General", body="")
    att_id = _add_image(dsn, settings_for(), sub["id"], _png((30, 120, 40)))

    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))
    calls = []

    def vision(model, api_key, system, user_text, images):
        calls.append(len(images))
        return _vision_reply()(model, api_key, system, user_text, images)

    summary = pipeline.run_submission_pipeline(pool, sub["id"], settings_for(), vision_call=vision)
    assert summary["status"] == "read"
    assert calls == [1]

    with psycopg.connect(dsn, autocommit=True, row_factory=dict_row) as conn:
        att = conn.execute("SELECT read_status, visual_facts FROM content_attachments WHERE id = %s", (att_id,)).fetchone()
        finding = conn.execute(
            """SELECT f.type, f.bbox, f.needs_human_review, f.suggestion_kind, f.guideline_id
               FROM findings f JOIN finding_attachments fa ON fa.finding_id = f.id
               WHERE fa.attachment_id = %s""",
            (att_id,),
        ).fetchone()
    assert att["read_status"] == "ready"
    assert att["visual_facts"][0]["id"] == "F1"
    assert finding["type"] == "image"
    assert finding["bbox"] is not None and len(finding["bbox"]) == 4
    assert finding["needs_human_review"] is True
    assert finding["suggestion_kind"] == "Visual suggestion"
    assert finding["guideline_id"] == "G-TEST"


def test_budget_exhaustion_marks_attachments_partial(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], kind="image", body="")
    ids = [_add_image(dsn, settings_for(), sub["id"], _png((i * 20, 40, 40)), f"b{i}.png") for i in range(5)]
    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))
    calls = []

    def vision(model, api_key, system, user_text, images):
        calls.append(len(images))
        return {"facts": [], "findings": [], "notFound": []}

    # 5 images make 2 batches of up to 4. A budget of 1 covers the first batch only.
    pipeline.run_submission_pipeline(pool, sub["id"], settings_for(budget=1), vision_call=vision)
    assert calls == [4]
    with psycopg.connect(dsn, autocommit=True) as conn:
        statuses = dict(conn.execute(
            "SELECT id, read_status FROM content_attachments WHERE content_id = %s", (sub["id"],)
        ).fetchall())
    assert [statuses[i] for i in ids[:4]] == ["ready"] * 4
    assert statuses[ids[4]] == "partial"


def test_model_failure_marks_attachment_failed(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], kind="image", body="")
    att_id = _add_image(dsn, settings_for(), sub["id"], _png((90, 90, 90)))
    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))

    def vision(*args, **kwargs):
        raise VisionError("model call failed: Timeout")

    pipeline.run_submission_pipeline(pool, sub["id"], settings_for(), vision_call=vision)
    with psycopg.connect(dsn, autocommit=True) as conn:
        row = conn.execute("SELECT read_status, read_message FROM content_attachments WHERE id = %s", (att_id,)).fetchone()
    assert row[0] == "failed"
    assert "Timeout" not in row[1], "error details from the model must not reach the creator"


def test_text_submission_runs_the_text_check_without_vision(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], body="A short script about sunscreen.")
    rule_calls, vision_calls = [], []
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, rule_calls))

    summary = pipeline.run_submission_pipeline(
        pool, sub["id"], settings_for(), vision_call=lambda *a, **k: vision_calls.append(1) or {}
    )
    assert summary["status"] == "read"
    assert rule_calls == [sub["id"]]
    assert vision_calls == []


def test_submit_response_matches_contract_and_empty_submission_is_refused(client, users, dsn, monkeypatch):
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))

    empty = _create_submission(client, users["creator"], body="")
    refused = client.post(f"/api/submissions/{empty['id']}/submit", headers=_auth(users["creator"]))
    assert refused.status_code == 409

    sub = _create_submission(client, users["creator"], body="A short script about sunscreen.")
    accepted = client.post(f"/api/submissions/{sub['id']}/submit", headers=_auth(users["creator"]))
    assert accepted.status_code == 202, accepted.text
    body = accepted.json()
    assert set(body) == {"submissionId", "checkRunId", "queued"}
    assert body["submissionId"] == sub["id"] and body["queued"] == 0
    assert body["checkRunId"].startswith("chk_")

    # Another user cannot submit someone else's submission.
    assert client.post(f"/api/submissions/{sub['id']}/submit", headers=_auth(users["other"])).status_code == 403


def test_attachment_file_and_finding_links(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], kind="image", body="")
    settings = settings_for()
    att_id = _add_image(dsn, settings, sub["id"], _png((50, 90, 160)))
    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))
    pipeline.run_submission_pipeline(pool, sub["id"], settings, vision_call=lambda m, k, s, u, i: _vision_reply()(m, k, s, u, i))

    # The creator (owner) and the manager can open the file, and it is a PNG.
    own = client.get(f"/api/submissions/{sub['id']}/attachments/{att_id}/file", headers=_auth(users["creator"]))
    assert own.status_code == 200 and own.headers["content-type"].startswith("image/png")
    assert client.get(f"/api/submissions/{sub['id']}/attachments/{att_id}/file", headers=_auth(users["other"])).status_code == 403

    # Each finding names the attachment it came from, for the visual overlay.
    findings = client.get(f"/api/content/{sub['id']}/findings", headers=_auth(users["creator"])).json()
    visual = [f for f in findings if f["type"] == "image"]
    assert visual and visual[0]["attachmentIds"] == [att_id]


def test_creator_cannot_open_a_held_file_but_manager_can(client, users, dsn, pool, settings_for, monkeypatch):
    sub = _create_submission(client, users["creator"], body=f"Notes: {SECRET_TERM}")
    settings = settings_for()
    att_id = _add_image(dsn, settings, sub["id"], _png((120, 20, 20)))
    monkeypatch.setattr(pipeline, "read_image_lines", lambda path, **kw: [])
    monkeypatch.setattr(pipeline, "run_rule_check", _fake_rule_check(dsn, []))
    pipeline.run_submission_pipeline(pool, sub["id"], settings, vision_call=lambda *a, **k: {})

    url = f"/api/submissions/{sub['id']}/attachments/{att_id}/file"
    assert client.get(url, headers=_auth(users["creator"])).status_code == 404
    assert client.get(url, headers=_auth(users["manager"])).status_code == 200
