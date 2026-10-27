-- 04_living.sql (owner: P3)
-- Six published posts (LIV-) for the fact-change demo. Three share the face-wash price fact F-004.
BEGIN;

INSERT INTO content (id,title,channel,team,owner_id,status,body_text,body_html,thumbnail_art,published_at) VALUES
('LIV-01','Face wash launch (Instagram)','Instagram','Marketing','user-creator','Published',
 'Meet GreenGlow Tea Tree Face Wash, now Rs 349 for 100 ml.',
 '<p>Meet GreenGlow Tea Tree Face Wash, now Rs 349 for 100 ml.</p>','facewash',now()),
('LIV-02','Face wash price (Email)','Email','Sales','user-reviewer','Published',
 'Your favourite face wash is Rs 349 for 100 ml. Shop today.',
 '<p>Your favourite face wash is Rs 349 for 100 ml. Shop today.</p>','email',now()),
('LIV-03','Face wash price (Ad)','Ad','Brand','user-manager','Published',
 'GreenGlow Tea Tree Face Wash: Rs 349 for 100 ml.',
 '<p>GreenGlow Tea Tree Face Wash: Rs 349 for 100 ml.</p>','offer',now()),
('LIV-04','Product name (Website)','Website','Brand','user-manager','Published',
 'GreenGlow Tea Tree Face Wash is made with tea tree and neem extract.',
 '<p>GreenGlow Tea Tree Face Wash is made with tea tree and neem extract.</p>','facewash',now()),
('LIV-05','Ingredients (Email)','Email','Marketing','user-creator','Published',
 'Our face wash is paraben-free and sulphate-free.',
 '<p>Our face wash is paraben-free and sulphate-free.</p>','email',now()),
('LIV-06','Sunscreen rating (Instagram)','Instagram','Marketing','user-creator','Published',
 'GreenGlow Sunscreen SPF 50 is rated PA+++.',
 '<p>GreenGlow Sunscreen SPF 50 is rated PA+++.</p>','sunscreen',now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO fact_content_links (id,content_id,source_kind,fact_id,source_id,source_version,match_reason) VALUES
('FCL-01','LIV-01','fact','F-004','F-004',1,'Face wash price stated'),
('FCL-02','LIV-02','fact','F-004','F-004',1,'Face wash price stated'),
('FCL-03','LIV-03','fact','F-004','F-004',1,'Face wash price stated'),
('FCL-04','LIV-04','fact','F-001','F-001',1,'Approved product name'),
('FCL-05','LIV-05','fact','F-002','F-002',1,'Ingredients stated'),
('FCL-06','LIV-06','fact','F-005','F-005',1,'Sunscreen rating stated')
ON CONFLICT (id) DO NOTHING;

COMMIT;
