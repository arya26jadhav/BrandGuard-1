-- 04b_demo_posts.sql
-- Optional reference sample drafts for user compose tests.
-- Does NOT pre-seed findings, decisions, or revisions: those come from live use.
BEGIN;

INSERT INTO sample_drafts (id, title, channel, body_text, image_url, alt_text, blurb) VALUES
('SD-04', 'Daily Moisturizer Caption', 'Instagram', 'Hydrate your skin with GreenGlow Moisturizer Plus! Our nourishing formula provides 24-hour hydration. Dermatologically tested for daily use.', NULL, 'GreenGlow Moisturizer Plus bottle on green background', 'Reference draft for moisturizer launch.'),
('SD-05', 'Cleansing Milk Introduction', 'Website', 'Experience gentle skincare with GreenGlow Cleansing Milk. Removes dirt and impurities while keeping skin soft. Now available for Rs 299 for 150 ml.', NULL, 'GreenGlow Cleansing Milk bottle display', 'Reference draft for cleansing milk product page.')
ON CONFLICT (id) DO UPDATE SET
  title = EXCLUDED.title,
  channel = EXCLUDED.channel,
  body_text = EXCLUDED.body_text,
  image_url = EXCLUDED.image_url,
  alt_text = EXCLUDED.alt_text,
  blurb = EXCLUDED.blurb;

COMMIT;
