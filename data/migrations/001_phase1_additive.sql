-- BrandGuard Phase 1 — additive migration
-- Safe to run against an existing database (idempotent: CREATE IF NOT EXISTS, ADD COLUMN IF NOT EXISTS).
-- guideline_categories uses the shared design (keyed by category_key). See 005.
-- Run order: this file first, then 005, then 006, then 007.

BEGIN;

-- ────────────────────────────────────────────────────────────
-- 1. content.asset_type column (existing rows → 'social_post')
-- ────────────────────────────────────────────────────────────
ALTER TABLE content
    ADD COLUMN IF NOT EXISTS asset_type TEXT NOT NULL DEFAULT 'social_post';

-- ────────────────────────────────────────────────────────────
-- 2. guideline_categories (shared design, keyed by category_key)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS guideline_categories (
    category_key TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    applies_to   JSONB NOT NULL,
    checker      TEXT NOT NULL,
    source_file  TEXT NOT NULL,
    sort_order   INTEGER NOT NULL,
    CONSTRAINT guideline_categories_applies_to_check
        CHECK (jsonb_typeof(applies_to) = 'array'),
    CONSTRAINT guideline_categories_sort_order_check
        CHECK (sort_order > 0)
);

-- ────────────────────────────────────────────────────────────
-- 3. asset_types
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS asset_types (
    key   TEXT PRIMARY KEY,
    label TEXT NOT NULL
);

-- ────────────────────────────────────────────────────────────
-- 4. brand_documents
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brand_documents (
    id                TEXT PRIMARY KEY,
    filename          TEXT NOT NULL,
    mime              TEXT NOT NULL,
    sha256            TEXT NOT NULL,
    size_bytes        BIGINT NOT NULL,
    page_count        INTEGER,
    uploaded_by       TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    extraction_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (extraction_status IN ('pending','processing','done','needs_ocr','error')),
    storage_path      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_brand_documents_sha256 ON brand_documents(sha256);

-- ────────────────────────────────────────────────────────────
-- 5. brand_rules
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brand_rules (
    id                  TEXT PRIMARY KEY,
    category_key        TEXT NOT NULL REFERENCES guideline_categories(category_key) ON DELETE RESTRICT,
    asset_type_keys     TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    channels            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    rule_type           TEXT NOT NULL,
    subject             TEXT NOT NULL,
    value               JSONB NOT NULL DEFAULT '{}'::JSONB,
    severity            TEXT NOT NULL DEFAULT 'warning'
        CHECK (severity IN ('critical','warning','info')),
    status              TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft','approved','retired')),
    source_document_id  TEXT REFERENCES brand_documents(id) ON DELETE RESTRICT,
    section_ref         TEXT,
    page_ref            INTEGER,
    source_quote        TEXT,
    extraction_method   TEXT NOT NULL DEFAULT 'parser'
        CHECK (extraction_method IN ('llm','parser','manual')),
    created_by          TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    approved_by         TEXT REFERENCES users(id) ON DELETE SET NULL,
    approved_at         TIMESTAMPTZ,
    version             INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brand_rules_status_category ON brand_rules(status, category_key);
CREATE INDEX IF NOT EXISTS idx_brand_rules_asset_type_keys ON brand_rules USING GIN(asset_type_keys);

-- ────────────────────────────────────────────────────────────
-- 6. brand_rule_history  (D4 audit log)
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS brand_rule_history (
    id          TEXT PRIMARY KEY,
    rule_id     TEXT NOT NULL,
    action      TEXT NOT NULL CHECK (action IN ('create','edit','approve','retire')),
    changed_by  TEXT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    before      JSONB,
    after       JSONB
);

CREATE INDEX IF NOT EXISTS idx_brand_rule_history_rule_id ON brand_rule_history(rule_id);

-- ────────────────────────────────────────────────────────────
-- 7. intake_fields
-- ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS intake_fields (
    category_key     TEXT NOT NULL REFERENCES guideline_categories(category_key) ON DELETE CASCADE,
    field_key        TEXT NOT NULL,
    label            TEXT NOT NULL,
    field_type       TEXT NOT NULL,
    required         BOOLEAN NOT NULL DEFAULT TRUE,
    check_type       TEXT NOT NULL DEFAULT 'rule',
    status           TEXT NOT NULL DEFAULT 'not_entered'
        CHECK (status IN ('entered','not_entered','not_applicable','do_not_have')),
    note             TEXT,
    linked_rule_ids  TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    sort_order       INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (category_key, field_key)
);

COMMIT;