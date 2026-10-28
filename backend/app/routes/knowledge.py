from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta
from pathlib import PurePath
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from psycopg import Connection
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field, model_validator

from app.db import get_conn
from app.security import require_role

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

EDITOR_ROLES = ("manager", "admin")

FactStatus = Literal["Active", "Expiring soon", "Expired"]
FactSeverity = Literal["High", "Medium"]
FactType = Literal[
    "name",
    "price",
    "claim",
    "certification",
    "offer",
    "spec",
    "ingredient",
    "policy",
]

GuidelineCategory = Literal[
    "Terminology",
    "Claims & Legal",
    "Tone of Voice",
    "Formatting",
    "Accessibility",
    "Brand Assets",
    "Security",
]
GuidelineSeverity = Literal["critical", "warning", "info"]
Channel = Literal["Website", "Instagram", "Email", "Ad"]
ALLOWED_CHANNELS = ("Website", "Instagram", "Email", "Ad")

GlossaryKind = Literal["term", "product_name"]

# Facts expiring within this many days of today are marked "Expiring soon"
EXPIRING_SOON_DAYS = 90
MAX_UPLOAD_SIZE = 1 * 1024 * 1024  # 1 MB
MAX_GUIDELINE_TEXT_LENGTH = 20000


def generate_next_id(prefix: str, existing_ids: Iterable[str | dict | tuple]) -> str:
    """Generate the next ID in sequence for a given prefix (e.g. 'F-', 'G-', 'GL-').

    Finds the maximum existing numeric suffix, increments by 1, and zero-pads to 3 digits.
    Gaps are not reused.
    """
    clean_prefix = prefix if prefix.endswith("-") else f"{prefix}-"
    max_num = 0
    for item in existing_ids:
        if isinstance(item, dict):
            item = item.get("id", "")
        elif isinstance(item, (tuple, list)) and len(item) > 0:
            item = item[0]
        if isinstance(item, str) and item.startswith(clean_prefix):
            suffix = item[len(clean_prefix) :]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
    return f"{clean_prefix}{max_num + 1:03d}"


next_id = generate_next_id


def derive_fact_status(valid_until: date | None, today: date | None = None) -> FactStatus:
    """Derive fact status based on valid_until and reference date (defaults to today).

    - 'Expired' if valid_until < today
    - 'Expiring soon' if valid_until is within EXPIRING_SOON_DAYS of today
    - 'Active' if valid_until is further out or None
    """
    if today is None:
        today = date.today()
    if valid_until is None:
        return "Active"
    if valid_until < today:
        return "Expired"
    if valid_until <= today + timedelta(days=EXPIRING_SOON_DAYS):
        return "Expiring soon"
    return "Active"


class FactCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    statement: str = Field(..., min_length=1)
    fact_type: FactType
    product_id: str | None = None
    structured_value: dict = Field(default_factory=dict)
    match_keywords: list[str] = Field(default_factory=list)
    match_regex: str | None = None
    severity_on_change: FactSeverity = "Medium"
    category: str = "Brand"
    valid_from: date = Field(default_factory=date.today)
    valid_until: date | None = None
    owner_id: str | None = None
    status: FactStatus | None = None

    @model_validator(mode="after")
    def validate_dates_and_status(self) -> FactCreate:
        if self.valid_until is not None and self.valid_until < self.valid_from:
            raise ValueError("valid_until must be >= valid_from")
        expected_status = derive_fact_status(self.valid_until)
        if self.status is not None and self.status != expected_status:
            raise ValueError(
                f"Status '{self.status}' contradicts valid_until date (expected '{expected_status}')"
            )
        if self.status is None:
            self.status = expected_status
        return self


class FactUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    statement: str | None = Field(default=None, min_length=1)
    status: FactStatus | None = None
    valid_until: date | None = None
    severity_on_change: FactSeverity | None = None
    note: str | None = Field(default=None, max_length=500)


class GuidelineCreate(BaseModel):
    short_name: str = Field(..., min_length=1, max_length=60)
    title: str = Field(..., min_length=1, max_length=200)
    text: str = Field(..., min_length=1, max_length=MAX_GUIDELINE_TEXT_LENGTH)
    category: GuidelineCategory
    rule_type: str = "warning"
    severity: GuidelineSeverity = "warning"
    applies_to_channels: list[Channel] = Field(
        default_factory=lambda: ["Website", "Instagram", "Email", "Ad"],
        min_length=1,
    )
    required_text: str | None = None


class GuidelineUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    severity: GuidelineSeverity | None = None
    is_active: bool | None = None


class GlossaryCreate(BaseModel):
    approved_term: str = Field(..., min_length=1, max_length=120)
    avoid_terms: list[str] = Field(default_factory=list)
    kind: GlossaryKind
    explanation: str = Field(default="")


FACT_COLUMNS = """
    id, product_id, title, statement, fact_type, structured_value,
    match_keywords, severity_on_change, owner_id, version,
    valid_from, valid_until, status, category, updated_at
"""

GUIDELINE_COLUMNS = """
    id, short_name, title, text, category, rule_type, severity,
    applies_to_channels, required_text, version, owner_id, is_active, updated_at
"""


def to_fact(row: dict) -> dict:
    return {
        "id": row["id"],
        "productId": row["product_id"],
        "title": row["title"],
        "statement": row["statement"],
        "factType": row["fact_type"],
        "structuredValue": row["structured_value"],
        "matchKeywords": row["match_keywords"],
        "severityOnChange": row["severity_on_change"],
        "ownerId": row["owner_id"],
        "version": row["version"],
        "validFrom": row["valid_from"],
        "validUntil": row["valid_until"],
        "status": row["status"],
        "category": row["category"],
        "updatedAt": row["updated_at"],
    }


def to_guideline(row: dict) -> dict:
    return {
        "id": row["id"],
        "shortName": row["short_name"],
        "title": row["title"],
        "text": row["text"],
        "category": row["category"],
        "ruleType": row["rule_type"],
        "severity": row["severity"],
        "appliesToChannels": row["applies_to_channels"],
        "requiredText": row["required_text"],
        "version": row["version"],
        "ownerId": row["owner_id"],
        "isActive": row["is_active"],
        "updatedAt": row["updated_at"],
    }


def to_glossary(row: dict) -> dict:
    return {
        "id": row["id"],
        "approvedTerm": row["approved_term"],
        "avoidTerms": row["avoid_terms"],
        "kind": row["kind"],
        "explanation": row["explanation"],
        "isActive": row["is_active"],
    }


@router.get("/facts")
def list_facts(
    status: FactStatus | None = Query(default=None),
    conn: Connection = Depends(get_conn),
) -> list[dict]:
    if status is None:
        rows = conn.execute(f"SELECT {FACT_COLUMNS} FROM facts ORDER BY id").fetchall()
    else:
        rows = conn.execute(
            f"SELECT {FACT_COLUMNS} FROM facts WHERE status = %s ORDER BY id",
            (status,),
        ).fetchall()
    return [to_fact(r) for r in rows]


@router.post("/facts", status_code=status.HTTP_201_CREATED)
def create_fact(
    body: FactCreate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    if body.product_id is not None:
        prod = conn.execute(
            "SELECT 1 FROM products WHERE id = %s", (body.product_id,)
        ).fetchone()
        if prod is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{body.product_id}' not found",
            )

    owner_id = body.owner_id or user["id"]
    if body.owner_id is not None:
        u = conn.execute("SELECT 1 FROM users WHERE id = %s", (owner_id,)).fetchone()
        if u is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{owner_id}' not found",
            )

    with conn.transaction():
        conn.execute("LOCK TABLE facts IN EXCLUSIVE MODE")
        rows = conn.execute("SELECT id FROM facts").fetchall()
        fact_id = generate_next_id("F-", [r["id"] for r in rows])

        row = conn.execute(
            f"""
            INSERT INTO facts (
                id, product_id, title, statement, fact_type, structured_value,
                match_keywords, match_regex, severity_on_change, owner_id,
                version, valid_from, valid_until, status, category
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, %s, %s, %s)
            RETURNING {FACT_COLUMNS}
            """,
            (
                fact_id,
                body.product_id,
                body.title,
                body.statement,
                body.fact_type,
                Jsonb(body.structured_value or {}),
                body.match_keywords,
                body.match_regex,
                body.severity_on_change,
                owner_id,
                body.valid_from,
                body.valid_until,
                body.status,
                body.category,
            ),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO fact_versions
                (fact_id, version, statement, structured_value, note, owner,
                 changed_by, valid_from, valid_until)
            VALUES (%s, 1, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                row["id"],
                row["statement"],
                Jsonb(row["structured_value"] or {}),
                "Initial version",
                row["owner_id"] or "",
                user["id"],
                row["valid_from"],
                row["valid_until"],
            ),
        )

    return to_fact(row)


@router.get("/facts/{fact_id}")
def get_fact(fact_id: str, conn: Connection = Depends(get_conn)) -> dict:
    row = conn.execute(
        f"SELECT {FACT_COLUMNS} FROM facts WHERE id = %s", (fact_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")
    return to_fact(row)


@router.patch("/facts/{fact_id}")
def update_fact(
    fact_id: str,
    body: FactUpdate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    """Update the fields sent, bump the version, and write a fact_versions row.

    Column names come only from the FactUpdate model, never from user input.
    """
    changes = body.model_dump(exclude_unset=True)
    note = changes.pop("note", None) or ""
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{column} = %s" for column in changes)
    params = [*changes.values(), fact_id]
    row = conn.execute(
        f"""
        UPDATE facts
        SET {set_clause}, version = version + 1, updated_at = now()
        WHERE id = %s
        RETURNING {FACT_COLUMNS}
        """,
        params,
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Fact not found")

    conn.execute(
        """
        INSERT INTO fact_versions
            (fact_id, version, statement, structured_value, note, owner,
             changed_by, valid_from, valid_until)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row["id"],
            row["version"],
            row["statement"],
            Jsonb(row["structured_value"] or {}),
            note,
            row["owner_id"] or "",
            user["id"],
            row["valid_from"],
            row["valid_until"],
        ),
    )
    return to_fact(row)


@router.get("/facts/{fact_id}/history")
def fact_history(fact_id: str, conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        """
        SELECT version, statement, note, owner, changed_by, changed_at, valid_from, valid_until
        FROM fact_versions WHERE fact_id = %s ORDER BY version DESC
        """,
        (fact_id,),
    ).fetchall()
    return [
        {
            "version": r["version"],
            "statement": r["statement"],
            "note": r["note"],
            "owner": r["owner"],
            "changedBy": r["changed_by"],
            "changedAt": r["changed_at"],
            "validFrom": r["valid_from"],
            "validUntil": r["valid_until"],
        }
        for r in rows
    ]


@router.get("/guidelines")
def list_guidelines(conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        f"SELECT {GUIDELINE_COLUMNS} FROM guidelines ORDER BY id"
    ).fetchall()
    return [to_guideline(r) for r in rows]


@router.post("/guidelines/upload", status_code=status.HTTP_201_CREATED)
async def upload_guideline(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    category: GuidelineCategory = Form(...),
    severity: GuidelineSeverity = Form(default="warning"),
    applies_to_channels: str | None = Form(default=None),
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    filename = file.filename or ""
    lower_ext = PurePath(filename).suffix.lower()
    if lower_ext not in (".txt", ".md"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type: only .txt and .md files are accepted",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds the 1 MB limit",
        )

    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be valid UTF-8 text",
        )

    text = raw_text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File text cannot be empty",
        )

    if len(text) > MAX_GUIDELINE_TEXT_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File text exceeds maximum length of {MAX_GUIDELINE_TEXT_LENGTH} characters",
        )

    if title is not None and title.strip():
        guideline_title = title.strip()
    else:
        guideline_title = PurePath(filename).stem or "Untitled"
    if len(guideline_title) > 200:
        guideline_title = guideline_title[:200]

    short_name = guideline_title[:60]

    if applies_to_channels is None or not applies_to_channels.strip():
        channels = list(ALLOWED_CHANNELS)
    else:
        channels = [c.strip() for c in applies_to_channels.split(",") if c.strip()]
        if not channels:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="applies_to_channels cannot be empty",
            )
        for c in channels:
            if c not in ALLOWED_CHANNELS:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid channel '{c}'. Allowed: {list(ALLOWED_CHANNELS)}",
                )

    with conn.transaction():
        conn.execute("LOCK TABLE guidelines IN EXCLUSIVE MODE")
        rows = conn.execute("SELECT id FROM guidelines").fetchall()
        guideline_id = generate_next_id("G-", [r["id"] for r in rows])

        row = conn.execute(
            f"""
            INSERT INTO guidelines (
                id, short_name, title, text, category, rule_type, severity,
                applies_to_channels, required_text, version, owner_id, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, TRUE)
            RETURNING {GUIDELINE_COLUMNS}
            """,
            (
                guideline_id,
                short_name,
                guideline_title,
                text,
                category,
                "warning",
                severity,
                channels,
                None,
                user["id"],
            ),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO guideline_versions
                (guideline_id, version, text, changed_by, change_note)
            VALUES (%s, 1, %s, %s, %s)
            """,
            (
                row["id"],
                row["text"],
                user["id"],
                "Uploaded file initial version",
            ),
        )

    return to_guideline(row)


@router.post("/guidelines", status_code=status.HTTP_201_CREATED)
def create_guideline(
    body: GuidelineCreate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    with conn.transaction():
        conn.execute("LOCK TABLE guidelines IN EXCLUSIVE MODE")
        rows = conn.execute("SELECT id FROM guidelines").fetchall()
        guideline_id = generate_next_id("G-", [r["id"] for r in rows])

        row = conn.execute(
            f"""
            INSERT INTO guidelines (
                id, short_name, title, text, category, rule_type, severity,
                applies_to_channels, required_text, version, owner_id, is_active
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1, %s, TRUE)
            RETURNING {GUIDELINE_COLUMNS}
            """,
            (
                guideline_id,
                body.short_name,
                body.title,
                body.text,
                body.category,
                body.rule_type,
                body.severity,
                body.applies_to_channels,
                body.required_text,
                user["id"],
            ),
        ).fetchone()

        conn.execute(
            """
            INSERT INTO guideline_versions
                (guideline_id, version, text, changed_by, change_note)
            VALUES (%s, 1, %s, %s, %s)
            """,
            (
                row["id"],
                row["text"],
                user["id"],
                "Initial version",
            ),
        )

    return to_guideline(row)


@router.get("/guidelines/{guideline_id}")
def get_guideline(guideline_id: str, conn: Connection = Depends(get_conn)) -> dict:
    row = conn.execute(
        f"SELECT {GUIDELINE_COLUMNS} FROM guidelines WHERE id = %s", (guideline_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Guideline not found")
    return to_guideline(row)


@router.patch("/guidelines/{guideline_id}")
def update_guideline(
    guideline_id: str,
    body: GuidelineUpdate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{column} = %s" for column in changes)
    params = [*changes.values(), guideline_id]
    row = conn.execute(
        f"""
        UPDATE guidelines
        SET {set_clause}, version = version + 1, updated_at = now()
        WHERE id = %s
        RETURNING {GUIDELINE_COLUMNS}
        """,
        params,
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Guideline not found")
    return to_guideline(row)


@router.get("/glossary")
def list_glossary(conn: Connection = Depends(get_conn)) -> list[dict]:
    rows = conn.execute(
        "SELECT id, approved_term, avoid_terms, kind, explanation, is_active "
        "FROM glossary ORDER BY id"
    ).fetchall()
    return [
        {
            "id": r["id"],
            "approvedTerm": r["approved_term"],
            "avoidTerms": r["avoid_terms"],
            "kind": r["kind"],
            "explanation": r["explanation"],
            "isActive": r["is_active"],
        }
        for r in rows
    ]


@router.post("/glossary", status_code=status.HTTP_201_CREATED)
def create_glossary_term(
    body: GlossaryCreate,
    user: dict = Depends(require_role(*EDITOR_ROLES)),
    conn: Connection = Depends(get_conn),
) -> dict:
    with conn.transaction():
        conn.execute("LOCK TABLE glossary IN EXCLUSIVE MODE")
        rows = conn.execute("SELECT id FROM glossary").fetchall()
        glossary_id = generate_next_id("GL-", [r["id"] for r in rows])

        row = conn.execute(
            """
            INSERT INTO glossary (id, approved_term, avoid_terms, kind, explanation, is_active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
            RETURNING id, approved_term, avoid_terms, kind, explanation, is_active
            """,
            (
                glossary_id,
                body.approved_term,
                body.avoid_terms,
                body.kind,
                body.explanation,
            ),
        ).fetchone()

    return to_glossary(row)


@router.get("/assets")
def list_assets(
    asset_type: str | None = Query(default=None),
    conn: Connection = Depends(get_conn),
) -> list[dict]:
    base = "SELECT id, label, asset_type, version, status, hex, usage_note, metadata FROM assets"
    if asset_type is None:
        rows = conn.execute(f"{base} ORDER BY id").fetchall()
    else:
        rows = conn.execute(f"{base} WHERE asset_type = %s ORDER BY id", (asset_type,)).fetchall()
    return [
        {
            "id": r["id"],
            "label": r["label"],
            "assetType": r["asset_type"],
            "version": r["version"],
            "status": r["status"],
            "hex": r["hex"],
            "usageNote": r["usage_note"],
            "metadata": r["metadata"],
        }
        for r in rows
    ]
