-- Migration 005: categories, channels, and the logo flag.
--
-- The shared database is the canonical schema for these tables.
-- An earlier version of this file assumed guideline_categories had
-- (id, is_active). The shared table is keyed by category_key, so that
-- version failed. This file matches the shared design.
--
-- guidelines.category is NOT given a foreign key here: existing rows hold
-- labels such as "Claims & Legal", not category_key values such as
-- "claims_legal". Linking them is a separate change.
--
-- Idempotent and transactional: safe to run on a database that already has
-- these changes, and a failure rolls back the whole file.

BEGIN;

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

INSERT INTO guideline_categories
  (category_key, label, applies_to, checker, source_file, sort_order) VALUES
  ('text_copy',       'Written copy',                  '["social_post", "caption", "email", "web_copy", "ad_copy"]', 'rules_and_ai_text',      'guideline_categories.json', 1),
  ('creator_brief',   'Content creator guidelines',    '["creator_script", "creator_brief"]',                        'ai_text',               'guideline_categories.json', 2),
  ('video',           'Video and reels',               '["video_script", "video_asset"]',                            'ai_text_and_transcript', 'guideline_categories.json', 3),
  ('product_design',  'Product design',                '["product_image", "product_label"]',                         'image_rules',           'guideline_categories.json', 4),
  ('packaging',       'Packaging',                     '["packaging_design", "packaging_copy"]',                     'image_rules_and_text',  'guideline_categories.json', 5),
  ('marketing_ideas', 'Marketing ideas and campaigns', '["campaign_idea", "promo"]',                                 'ai_text',               'guideline_categories.json', 6),
  ('visual_identity', 'Visual identity',               '["any_visual"]',                                             'image_rules',           'guideline_categories.json', 7),
  ('claims_legal',    'Claims and legal',              '["any"]',                                                    'rules_and_ai_text',     'guideline_categories.json', 8),
  ('custom',          'Other (custom)',                '["any"]',                                                    'manual_review',         'guideline_categories.json', 9)
ON CONFLICT (category_key) DO NOTHING;

CREATE TABLE IF NOT EXISTS channels (
  id         TEXT PRIMARY KEY,
  sort_order INTEGER NOT NULL DEFAULT 0,
  is_active  BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO channels (id, sort_order) VALUES
  ('Website', 1), ('Instagram', 2), ('Email', 3), ('Ad', 4)
ON CONFLICT (id) DO NOTHING;

ALTER TABLE content ADD COLUMN IF NOT EXISTS image_is_logo BOOLEAN NOT NULL DEFAULT FALSE;

COMMIT;