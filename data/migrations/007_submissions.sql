-- Phase 2: submissions (scripts, marketing ideas, product designs, images) and their attachments.
-- Plan sections 3.2, 4.1, 4.2 and 9. Idempotent: safe to run more than once.
-- Apply to an existing database with:
--   psql "$DATABASE_URL" -f data/migrations/007_submissions.sql
-- Depends on migration 005 (the channels table).
--
-- Not appended to data/schema.sql yet: that waits for the intake_fields decision.

BEGIN;

-- 1. Submission kind. Existing rows become 'post', so nothing changes for them.
ALTER TABLE content ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'post';
ALTER TABLE content DROP CONSTRAINT IF EXISTS content_kind_check;
ALTER TABLE content ADD CONSTRAINT content_kind_check
  CHECK (kind IN ('post', 'script', 'marketing_idea', 'design', 'image'));

-- 2. The General channel, used by scripts and marketing ideas.
--    The channel check is re-created (name confirmed in the database: content_channel_check).
INSERT INTO channels (id, sort_order) VALUES ('General', 5) ON CONFLICT (id) DO NOTHING;
ALTER TABLE content DROP CONSTRAINT IF EXISTS content_channel_check;
ALTER TABLE content ADD CONSTRAINT content_channel_check
  CHECK (channel IN ('Website', 'Instagram', 'Email', 'Ad', 'General'));

-- Guidelines apply to General too, so the visual and text checks have guidelines to read.
UPDATE guidelines
   SET applies_to_channels = array_append(applies_to_channels, 'General')
 WHERE is_active
   AND NOT ('General' = ANY (applies_to_channels));

-- 3. Attachments: several files per submission (plan section 4.1).
CREATE SEQUENCE IF NOT EXISTS content_attachment_seq;

CREATE TABLE IF NOT EXISTS content_attachments (
  id TEXT PRIMARY KEY DEFAULT 'ATT-' || lpad(nextval('content_attachment_seq')::text, 4, '0'),
  content_id TEXT NOT NULL REFERENCES content(id) ON DELETE CASCADE,
  filename TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('image', 'pdf', 'docx', 'text')),
  size_bytes INTEGER NOT NULL CHECK (size_bytes > 0 AND size_bytes <= 10485760),
  sha256 TEXT NOT NULL,
  storage_path TEXT NOT NULL,
  page_count INTEGER NOT NULL DEFAULT 1 CHECK (page_count >= 1 AND page_count <= 20),
  extracted_text TEXT NOT NULL DEFAULT '',
  visual_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
  read_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (read_status IN ('pending', 'reading', 'ready', 'held', 'failed', 'partial')),
  read_message TEXT NOT NULL DEFAULT '',
  uploaded_by TEXT REFERENCES users(id) ON DELETE SET NULL,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_content_attachments_content ON content_attachments(content_id);

-- 4. Findings can come from one or more attachments. The findings table has no column for this,
--    so the link is kept here. A finding with no link is about the submission text.
CREATE TABLE IF NOT EXISTS finding_attachments (
  finding_id TEXT NOT NULL REFERENCES findings(id) ON DELETE CASCADE,
  attachment_id TEXT NOT NULL REFERENCES content_attachments(id) ON DELETE CASCADE,
  PRIMARY KEY (finding_id, attachment_id)
);

-- 5. Manager alert for a held submission (plan section 9, open item 3).
--    alerts had no column for a confidential review, so a nullable kind is added.
--    Existing alert rows keep kind NULL, which means a fact or guideline change.
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS kind TEXT;
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_kind_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_kind_check
  CHECK (kind IS NULL OR kind IN ('confidential_review'));

COMMIT;
