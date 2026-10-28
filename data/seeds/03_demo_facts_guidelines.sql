-- 03_demo_facts_guidelines.sql
-- Idempotent seed for GreenGlow guidelines, guideline versions, glossary, facts, and rule patterns.
BEGIN;

-- Guidelines and guideline versions
INSERT INTO guidelines (id, short_name, title, text, category, rule_type, severity, applies_to_channels, required_text, version, owner_id, is_active) VALUES
('G-001', 'Absolute claims', 'Avoid absolute skincare claims', 'Do not use absolute claims such as "100%", "guaranteed", "completely", or "removes all". Use only claims supported by approved facts.', 'Claims & Legal', 'critical', 'critical', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-002', 'Unsupported superlatives', 'Avoid unsupported superlatives', 'Do not use "best", "fastest", or "#1" unless a cited approved fact supports the comparison.', 'Claims & Legal', 'warning', 'warning', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-003', 'Customer terminology', 'Use approved customer terminology', 'Use "customers"; do not call customers "clients" or "users" in consumer-facing copy.', 'Terminology', 'info', 'info', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-004', 'Skincare disclaimer', 'Include the skincare results disclaimer', 'Skincare advertising on Instagram, Ad, and Email must include the required results disclaimer.', 'Claims & Legal', 'warning', 'warning', ARRAY['Instagram','Ad','Email']::TEXT[], 'Results may vary from person to person.', 1, 'user-admin', TRUE),
('G-005', 'Approved logo', 'Use only logo version 3', 'Use only logo version 3. Do not stretch, recolour, or crop the logo.', 'Brand Assets', 'warning', 'warning', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-006', 'Image alt text', 'Provide meaningful alt text', 'Every image needs meaningful alt text describing its relevant content.', 'Accessibility', 'warning', 'warning', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-007', 'Text contrast', 'Meet WCAG AA text contrast', 'Text contrast must meet WCAG AA: 4.5:1 for normal text and 3:1 for large text.', 'Accessibility', 'warning', 'warning', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-008', 'Friendly tone', 'Keep copy friendly and simple', 'Use a friendly, simple tone. Avoid hype and medical claims.', 'Tone of Voice', 'info', 'info', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-009', 'Confidential names', 'Do not reveal unreleased products or internal names', 'Do not mention unreleased products or internal names, including "Project Aurora".', 'Security', 'critical', 'critical', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE),
('G-010', 'Current facts and naming', 'Keep prices, offers, and product names accurate', 'Prices and offers must match approved facts and be live; use the exact approved product name.', 'Claims & Legal', 'critical', 'critical', ARRAY['Website','Instagram','Email','Ad']::TEXT[], NULL, 1, 'user-manager', TRUE)
ON CONFLICT (id) DO UPDATE SET
  short_name = EXCLUDED.short_name,
  title = EXCLUDED.title,
  text = EXCLUDED.text,
  category = EXCLUDED.category,
  rule_type = EXCLUDED.rule_type,
  severity = EXCLUDED.severity,
  applies_to_channels = EXCLUDED.applies_to_channels,
  required_text = EXCLUDED.required_text,
  version = EXCLUDED.version,
  owner_id = EXCLUDED.owner_id,
  is_active = EXCLUDED.is_active,
  updated_at = now();

INSERT INTO guideline_versions (guideline_id, version, text, changed_by, change_note, changed_at) VALUES
('G-001', 1, 'Do not use absolute claims such as "100%", "guaranteed", "completely", or "removes all". Use only claims supported by approved facts.', 'user-manager', 'Initial baseline policy', now() - INTERVAL '30 days'),
('G-002', 1, 'Do not use "best", "fastest", or "#1" unless a cited approved fact supports the comparison.', 'user-manager', 'Initial baseline policy', now() - INTERVAL '30 days'),
('G-003', 1, 'Use "customers"; do not call customers "clients" or "users" in consumer-facing copy.', 'user-manager', 'Standard customer terminology', now() - INTERVAL '20 days'),
('G-004', 1, 'Skincare advertising on Instagram, Ad, and Email must include the required results disclaimer.', 'user-admin', 'Mandatory regulatory disclaimer', now() - INTERVAL '15 days'),
('G-005', 1, 'Use only logo version 3. Do not stretch, recolour, or crop the logo.', 'user-manager', 'Logo version 3 guideline', now() - INTERVAL '10 days')
ON CONFLICT (guideline_id, version) DO NOTHING;

-- Glossary terms
INSERT INTO glossary (id, approved_term, avoid_terms, kind, explanation, is_active) VALUES
('GL-001', 'customers', ARRAY['clients','users']::TEXT[], 'term', 'Preferred term for people who buy or use GreenGlow products.', TRUE),
('GL-002', 'GreenGlow Tea Tree Face Wash', ARRAY['GreenGlow Face Wash','GreenGlow Tea Tree Wash','Tea Tree Face Wash']::TEXT[], 'product_name', 'Use the full approved product name every time.', TRUE),
('GL-003', 'helps reduce the appearance of', ARRAY['removes','cures','eliminates']::TEXT[], 'term', 'Approved cautious wording for appearance-related acne copy.', TRUE),
('GL-004', 'dermatologically tested', ARRAY['clinically proven']::TEXT[], 'term', 'Use only the supported testing statement; do not replace it with a stronger claim.', TRUE),
('GL-005', 'GreenGlow Cleansing Milk', ARRAY['Cleansing Milk','GG Cleanser']::TEXT[], 'product_name', 'Full approved product name for gentle cleansing milk.', TRUE),
('GL-006', 'GreenGlow Moisturizer Plus', ARRAY['Moisturizer Plus','GG Moisturizer']::TEXT[], 'product_name', 'Full approved product name for daily hydrating moisturizer.', TRUE)
ON CONFLICT (id) DO UPDATE SET
  approved_term = EXCLUDED.approved_term,
  avoid_terms = EXCLUDED.avoid_terms,
  kind = EXCLUDED.kind,
  explanation = EXCLUDED.explanation,
  is_active = EXCLUDED.is_active;

-- Facts (with categories, owners, valid_from, valid_until, and within-90-days expiry)
INSERT INTO facts (id, product_id, title, statement, fact_type, structured_value, match_keywords, severity_on_change, owner_id, version, valid_from, valid_until, status, category) VALUES
('F-001', 'P-001', 'Approved product name', 'The product name is exactly "GreenGlow Tea Tree Face Wash". Use the full approved name; never abbreviate it.', 'name', '{"approved_name":"GreenGlow Tea Tree Face Wash"}'::jsonb, ARRAY['GreenGlow','Tea Tree Face Wash','product name']::TEXT[], 'High', 'user-manager', 1, CURRENT_DATE - 60, NULL, 'Active', 'Brand'),
('F-002', 'P-001', 'Ingredients and exclusions', 'Contains tea tree and neem extract; paraben-free and sulphate-free.', 'ingredient', '{"ingredients":["tea tree","neem extract"],"free_from":["parabens","sulphates"]}'::jsonb, ARRAY['tea tree','neem extract','paraben-free','sulphate-free']::TEXT[], 'Medium', 'user-manager', 1, CURRENT_DATE - 60, NULL, 'Active', 'Product'),
('F-003', 'P-001', 'Dermatologically tested', 'The product is dermatologically tested; the test report is dated 2026.', 'claim', '{"claim":"dermatologically tested","report_year":2026}'::jsonb, ARRAY['dermatologically tested']::TEXT[], 'High', 'user-manager', 1, CURRENT_DATE - 60, NULL, 'Active', 'Product'),
('F-004', 'P-001', 'Face wash price', 'GreenGlow Tea Tree Face Wash costs Rs 349 for 100 ml.', 'price', '{"price":349,"currency":"INR","size_ml":100}'::jsonb, ARRAY['Rs 349','349','100 ml','price']::TEXT[], 'High', 'user-reviewer', 1, CURRENT_DATE - 60, NULL, 'Active', 'Sales'),
('F-005', 'P-002', 'Sunscreen SPF specification', 'GreenGlow Sunscreen SPF 50 is rated SPF 50, PA+++. Do not claim 100% protection from sun damage.', 'spec', '{"spf":50,"pa_rating":"+++","prohibited_claim":"100% protection"}'::jsonb, ARRAY['SPF 50','PA+++','sunscreen','sun damage']::TEXT[], 'High', 'user-manager', 1, CURRENT_DATE - 60, NULL, 'Active', 'Product'),
('F-006', 'P-001', 'Cruelty-free certification validity', 'The cruelty-free certification is valid until 2026-12-31.', 'certification', '{"certification":"cruelty-free","valid_until":"2026-12-31"}'::jsonb, ARRAY['cruelty-free','certification']::TEXT[], 'High', 'user-manager', 1, CURRENT_DATE - 60, CURRENT_DATE + 60, 'Expiring soon', 'Brand'),
('F-007', 'P-001', 'Acne claim limitation', 'There is no approved evidence that the product removes acne. Allowed wording: "helps reduce the appearance of".', 'claim', '{"approved_wording":"helps reduce the appearance of","unsupported_claim":"removes acne"}'::jsonb, ARRAY['acne','removes acne','helps reduce the appearance of']::TEXT[], 'High', 'user-admin', 1, CURRENT_DATE - 60, NULL, 'Active', 'Legal'),
('F-008', NULL, 'Festive offer', 'The approved festive offer is 20% off and is valid for 45 more days.', 'offer', '{"discount_percent":20}'::jsonb, ARRAY['festive offer','20% off','discount']::TEXT[], 'High', 'user-creator', 1, CURRENT_DATE - 15, CURRENT_DATE + 45, 'Expiring soon', 'Marketing'),
('F-018', 'P-003', 'Cleansing Milk Price', 'GreenGlow Cleansing Milk costs Rs 299 for 150 ml.', 'price', '{"price":299,"currency":"INR","size_ml":150}'::jsonb, ARRAY['Rs 299','Cleansing Milk','price']::TEXT[], 'High', 'user-reviewer', 1, CURRENT_DATE - 30, NULL, 'Active', 'Sales'),
('F-021', 'P-004', 'Moisturizer Plus Daily Use', 'GreenGlow Moisturizer Plus provides 24-hour hydration and is suitable for daily use.', 'claim', '{"hydration_hours":24}'::jsonb, ARRAY['24-hour hydration','Moisturizer Plus','daily use']::TEXT[], 'Medium', 'user-manager', 1, CURRENT_DATE - 30, NULL, 'Active', 'Product')
ON CONFLICT (id) DO UPDATE SET
  product_id = EXCLUDED.product_id,
  title = EXCLUDED.title,
  statement = EXCLUDED.statement,
  fact_type = EXCLUDED.fact_type,
  structured_value = EXCLUDED.structured_value,
  match_keywords = EXCLUDED.match_keywords,
  severity_on_change = EXCLUDED.severity_on_change,
  owner_id = EXCLUDED.owner_id,
  version = EXCLUDED.version,
  valid_from = EXCLUDED.valid_from,
  valid_until = EXCLUDED.valid_until,
  status = EXCLUDED.status,
  category = EXCLUDED.category,
  updated_at = now();

-- Rule patterns
INSERT INTO rule_patterns (id, guideline_id, kind, pattern, replacement, case_sensitive, note, channel, is_active) VALUES
('RP-001', 'G-001', 'phrase', 'removes all acne overnight', 'helps reduce the appearance of acne with regular use', FALSE, 'Flags an unsupported absolute acne-removal claim.', NULL, TRUE),
('RP-002', 'G-001', 'regex', E'\\b100%\\s+clear\\s+skin\\b', 'clearer-looking skin', FALSE, 'Flags an absolute clear-skin guarantee.', NULL, TRUE),
('RP-003', 'G-001', 'phrase', 'guaranteed', 'designed to', FALSE, 'Flags guarantee language.', NULL, TRUE),
('RP-004', 'G-001', 'regex', E'\\b100%\\s+(protection|secure|safe)\\b', 'helps protect', FALSE, 'Flags absolute 100 percent safety or protection claims.', NULL, TRUE),
('RP-005', 'G-002', 'phrase', 'fastest', 'quick-acting', FALSE, 'Flags an unsupported speed superlative.', NULL, TRUE),
('RP-006', 'G-002', 'phrase', 'best in india', 'loved by many customers', FALSE, 'Flags an unsupported comparative superlative.', NULL, TRUE),
('RP-007', 'G-002', 'regex', E'\\b#1\\b', '', FALSE, 'Flags an unsupported number-one claim.', NULL, TRUE),
('RP-008', 'G-003', 'phrase', 'clients', 'customers', FALSE, 'Replaces disallowed customer terminology.', NULL, TRUE),
('RP-009', 'G-003', 'phrase', 'users', 'customers', FALSE, 'Replaces disallowed customer terminology.', NULL, TRUE),
('RP-010', 'G-010', 'name_variant', 'GreenGlow Face Wash', 'GreenGlow Tea Tree Face Wash', FALSE, 'Replaces an abbreviated product name with the approved name.', NULL, TRUE),
('RP-011', 'G-004', 'required_text', 'Results may vary from person to person.', '', FALSE, 'Checks required skincare disclaimer on Instagram.', 'Instagram', TRUE),
('RP-012', 'G-004', 'required_text', 'Results may vary from person to person.', '', FALSE, 'Checks required skincare disclaimer in ads.', 'Ad', TRUE),
('RP-013', 'G-004', 'required_text', 'Results may vary from person to person.', '', FALSE, 'Checks required skincare disclaimer in email.', 'Email', TRUE),
('RP-014', 'G-009', 'confidential_term', 'Project Aurora', '', FALSE, 'Flags an internal unreleased project name.', NULL, TRUE),
('RP-015', 'G-009', 'confidential_term', 'unreleased', '', FALSE, 'Flags disclosure language about unreleased products.', NULL, TRUE),
('RP-016', 'G-008', 'phrase', 'cures eczema', 'may help soothe dry skin', FALSE, 'Flags a medical treatment claim and suggests safer wording.', NULL, TRUE)
ON CONFLICT (id) DO UPDATE SET
  guideline_id = EXCLUDED.guideline_id,
  kind = EXCLUDED.kind,
  pattern = EXCLUDED.pattern,
  replacement = EXCLUDED.replacement,
  case_sensitive = EXCLUDED.case_sensitive,
  note = EXCLUDED.note,
  channel = EXCLUDED.channel,
  is_active = EXCLUDED.is_active;

COMMIT;
