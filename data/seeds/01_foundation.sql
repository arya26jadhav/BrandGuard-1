-- BrandGuard foundation seed data; PostgreSQL 16; safe to rerun.
-- Demo users and IDs match mocks/users.ts. Team mapping: Maya=Marketing,
-- Jordan=Brand, Priya=Sales, Alex=Legal. Product facts use Jordan where no Product
-- team user exists. P-002 is the sunscreen product referenced by F-005.
BEGIN;

INSERT INTO users (id,name,email,role,initials,title,avatar_color,team,is_demo_login,persona_description,demo_route) VALUES
('user-creator','Maya Chen',NULL,'creator','MC','Content Creator','#6A8F72','Marketing',TRUE,'Creates marketing and social content for GreenGlow.','/content'),
('user-manager','Jordan Lee',NULL,'manager','JL','Brand Manager','#315B45','Brand',TRUE,'Owns brand governance, approved facts, and brand assets.','/brand'),
('user-reviewer','Priya Shah',NULL,'reviewer','PS','Brand Reviewer','#8B6F9E','Sales',TRUE,'Reviews promotional content and offer accuracy.','/review'),
('user-admin','Alex Morgan',NULL,'admin','AM','Workspace Admin','#607D8B','Legal',TRUE,'Administers the workspace and supports compliance review.','/dashboard'),
('user-creator-test','Test Creator',NULL,'creator','TC','Test Creator','#9E9E9E','Sales',FALSE,'Test-only second creator for the cross-owner 403 check. Not shown in the role switcher.','/content')
ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,email=EXCLUDED.email,role=EXCLUDED.role,initials=EXCLUDED.initials,title=EXCLUDED.title,avatar_color=EXCLUDED.avatar_color,team=EXCLUDED.team,is_demo_login=EXCLUDED.is_demo_login,persona_description=EXCLUDED.persona_description,demo_route=EXCLUDED.demo_route,updated_at=now();

INSERT INTO products (id,name,approved_name,category,is_released) VALUES
('P-001','GreenGlow Tea Tree Face Wash','GreenGlow Tea Tree Face Wash','skincare',TRUE),
('P-002','GreenGlow Sunscreen SPF 50','GreenGlow Sunscreen SPF 50','skincare',TRUE)
ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name,approved_name=EXCLUDED.approved_name,category=EXCLUDED.category,is_released=EXCLUDED.is_released;

INSERT INTO facts (id,product_id,title,statement,fact_type,structured_value,match_keywords,severity_on_change,owner_id,version,valid_from,valid_until,status,category) VALUES
('F-001','P-001','Approved product name','The product name is exactly "GreenGlow Tea Tree Face Wash". Use the full approved name; never abbreviate it.','name','{"approved_name":"GreenGlow Tea Tree Face Wash"}',ARRAY['GreenGlow','Tea Tree Face Wash','product name'],'High','user-manager',1,'2026-01-01',NULL,'Active','Brand'),
('F-002','P-001','Ingredients and exclusions','Contains tea tree and neem extract; paraben-free and sulphate-free.','ingredient','{"ingredients":["tea tree","neem extract"],"free_from":["parabens","sulphates"]}',ARRAY['tea tree','neem extract','paraben-free','sulphate-free'],'Medium','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-003','P-001','Dermatologically tested','The product is dermatologically tested; the test report is dated 2026.','claim','{"claim":"dermatologically tested","report_year":2026}',ARRAY['dermatologically tested'],'High','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-004','P-001','Face wash price','GreenGlow Tea Tree Face Wash costs Rs 349 for 100 ml.','price','{"price":349,"currency":"INR","size_ml":100}',ARRAY['Rs 349','349','100 ml','price'],'High','user-reviewer',1,'2026-01-01',NULL,'Active','Sales'),
('F-005','P-002','Sunscreen SPF specification','GreenGlow Sunscreen SPF 50 is rated SPF 50, PA+++. Do not claim 100% protection from sun damage.','spec','{"spf":50,"pa_rating":"+++","prohibited_claim":"100% protection"}',ARRAY['SPF 50','PA+++','sunscreen','sun damage'],'High','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-006','P-001','Cruelty-free certification validity','The cruelty-free certification is valid until 2026-12-31.','certification','{"certification":"cruelty-free","valid_until":"2026-12-31"}',ARRAY['cruelty-free','certification'],'High','user-manager',1,'2026-01-01','2026-12-31','Expiring soon','Brand'),
('F-007','P-001','Acne claim limitation','There is no approved evidence that the product removes acne. Allowed wording: "helps reduce the appearance of".','claim','{"approved_wording":"helps reduce the appearance of","unsupported_claim":"removes acne"}',ARRAY['acne','removes acne','helps reduce the appearance of'],'High','user-admin',1,'2026-01-01',NULL,'Active','Legal'),
('F-008',NULL,'Festive offer','The approved festive offer is 20% off and is valid until 2026-10-31.','offer','{"discount_percent":20,"valid_until":"2026-10-31"}',ARRAY['festive offer','20% off','30% off','discount'],'High','user-creator',1,'2026-01-01','2026-10-31','Expiring soon','Marketing'),
('F-009','P-001','Previous cruelty-free certificate','The previous cruelty-free certificate expired on 2025-09-30 and must not be presented as current.','certification','{"certification":"cruelty-free","expired_on":"2025-09-30"}',ARRAY['cruelty-free','certificate','certification'],'High','user-manager',1,'2024-01-01','2025-09-30','Expired','Brand')
ON CONFLICT (id) DO UPDATE SET product_id=EXCLUDED.product_id,title=EXCLUDED.title,statement=EXCLUDED.statement,fact_type=EXCLUDED.fact_type,structured_value=EXCLUDED.structured_value,match_keywords=EXCLUDED.match_keywords,severity_on_change=EXCLUDED.severity_on_change,owner_id=EXCLUDED.owner_id,version=EXCLUDED.version,valid_from=EXCLUDED.valid_from,valid_until=EXCLUDED.valid_until,status=EXCLUDED.status,category=EXCLUDED.category,updated_at=now();

INSERT INTO facts (id,product_id,title,statement,fact_type,structured_value,match_keywords,severity_on_change,owner_id,version,valid_from,valid_until,status,category) VALUES
('F-010','P-001','Skin types','Suitable for oily and combination skin.','claim','{"skin_types":["oily","combination"]}',ARRAY['oily skin','combination skin','skin types'],'Medium','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-011','P-002','Sunscreen price','GreenGlow Sunscreen SPF 50 costs Rs 499 for 50 g.','price','{"price":499,"currency":"INR","size_g":50}',ARRAY['Rs 499','sunscreen price'],'High','user-reviewer',1,'2026-01-01',NULL,'Active','Sales'),
('F-012','P-001','Alcohol-free','Face wash is alcohol-free.','claim','{"free_from":["alcohol"]}',ARRAY['alcohol-free','alcohol free'],'Medium','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-013','P-001','Vegan status','Face wash is vegan, with no animal-derived ingredients.','claim','{"vegan":true}',ARRAY['vegan'],'Medium','user-manager',1,'2026-01-01',NULL,'Active','Product'),
('F-014','P-001','ISO 22716 certification','ISO 22716 cosmetics GMP certification is valid until 2027-06-30.','certification','{"certification":"ISO 22716","valid_until":"2027-06-30"}',ARRAY['ISO 22716','GMP','certification'],'High','user-admin',1,'2026-01-01','2027-06-30','Active','Legal'),
('F-015',NULL,'Free shipping','Free shipping on orders above Rs 499 until 2026-12-31.','offer','{"min_order_inr":499,"valid_until":"2026-12-31"}',ARRAY['free shipping','Rs 499'],'Medium','user-reviewer',1,'2026-01-01','2026-12-31','Expiring soon','Sales'),
('F-016',NULL,'Support email','Customer support email is help@greenglow.demo.','spec','{"email":"help@greenglow.demo"}',ARRAY['help@greenglow.demo','support email'],'Medium','user-admin',1,'2026-01-01',NULL,'Active','Brand'),
('F-017','P-001','Average rating','Average rating is 4.5 out of 5 from 1,200 verified reviews.','claim','{"rating":4.5,"max":5,"review_count":1200}',ARRAY['4.5 out of 5','1,200 reviews','rating'],'Medium','user-reviewer',1,'2026-01-01','2026-12-31','Expiring soon','Sales'),
('F-019',NULL,'Return window','Returns are accepted within 7 days of delivery.','spec','{"return_window_days":7}',ARRAY['returns','7 days'],'Medium','user-reviewer',1,'2026-01-01',NULL,'Active','Sales'),
('F-020','P-002','Sunscreen PA rating','Sunscreen rating is PA+++, SPF 50.','spec','{"spf":50,"pa_rating":"+++"}',ARRAY['PA+++','SPF 50'],'High','user-manager',1,'2026-01-01',NULL,'Active','Product')
ON CONFLICT (id) DO NOTHING;
INSERT INTO guidelines (id,short_name,title,text,category,rule_type,severity,applies_to_channels,required_text,version,owner_id,is_active) VALUES
('G-001','Absolute claims','Avoid absolute skincare claims','Do not use absolute claims such as "100%", "guaranteed", "completely", or "removes all". Use only claims supported by approved facts.','Claims & Legal','critical','critical',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-002','Unsupported superlatives','Avoid unsupported superlatives','Do not use "best", "fastest", or "#1" unless a cited approved fact supports the comparison.','Claims & Legal','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-003','Customer terminology','Use approved customer terminology','Use "customers"; do not call customers "clients" or "users" in consumer-facing copy.','Terminology','info','info',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-004','Skincare disclaimer','Include the skincare results disclaimer','Skincare advertising on Instagram, Ad, and Email must include the required results disclaimer.','Claims & Legal','warning','warning',ARRAY['Instagram','Ad','Email'],'Results may vary from person to person.',1,'user-admin',TRUE),
('G-005','Approved logo','Use only logo version 3','Use only logo version 3. Do not stretch, recolour, or crop the logo.','Brand Assets','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-006','Image alt text','Provide meaningful alt text','Every image needs meaningful alt text describing its relevant content.','Accessibility','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-007','Text contrast','Meet WCAG AA text contrast','Text contrast must meet WCAG AA: 4.5:1 for normal text and 3:1 for large text.','Accessibility','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-008','Friendly tone','Keep copy friendly and simple','Use a friendly, simple tone. Avoid hype and medical claims.','Tone of Voice','info','info',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-009','Confidential names','Do not reveal unreleased products or internal names','Do not mention unreleased products or internal names, including "Project Aurora".','Security','critical','critical',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-010','Current facts and naming','Keep prices, offers, and product names accurate','Prices and offers must match approved facts and be live; use the exact approved product name.','Claims & Legal','critical','critical',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE)
ON CONFLICT (id) DO UPDATE SET short_name=EXCLUDED.short_name,title=EXCLUDED.title,text=EXCLUDED.text,category=EXCLUDED.category,rule_type=EXCLUDED.rule_type,severity=EXCLUDED.severity,applies_to_channels=EXCLUDED.applies_to_channels,required_text=EXCLUDED.required_text,version=EXCLUDED.version,owner_id=EXCLUDED.owner_id,is_active=EXCLUDED.is_active,updated_at=now();
INSERT INTO guidelines (id,short_name,title,text,category,rule_type,severity,applies_to_channels,required_text,version,owner_id,is_active) VALUES
('G-011','Exact product name','Exact product name','Always write the product name exactly as in F-001.','Claims & Legal','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-012','No medical claims','No medical claims','Do not say cures, treats, heals or clinically proven unless a fact supports it.','Claims & Legal','critical','critical',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-013','No competitor names','No competitor names','Do not name competitor brands in marketing copy.','Claims & Legal','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-manager',TRUE),
('G-014','Testimonial consent','Testimonial consent','Testimonials need written consent and must be labelled as customer reviews.','Claims & Legal','warning','warning',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-admin',TRUE),
('G-015','Confidential launch names','Confidential launch names','Do not disclose unreleased product names or launch dates publicly.','Security','critical','critical',ARRAY['Website','Instagram','Email','Ad'],NULL,1,'user-admin',TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO glossary (id,approved_term,avoid_terms,kind,explanation,is_active) VALUES
('GL-001','customers',ARRAY['clients','users'],'term','Preferred term for people who buy or use GreenGlow products.',TRUE),
('GL-002','GreenGlow Tea Tree Face Wash',ARRAY['GreenGlow Face Wash','GreenGlow Tea Tree Wash','Tea Tree Face Wash'],'product_name','Use the full approved product name every time.',TRUE),
('GL-003','helps reduce the appearance of',ARRAY['removes','cures','eliminates'],'term','Approved cautious wording for appearance-related acne copy.',TRUE),
('GL-004','dermatologically tested',ARRAY['clinically proven'],'term','Use only the supported testing statement; do not replace it with a stronger claim.',TRUE)
ON CONFLICT (id) DO UPDATE SET approved_term=EXCLUDED.approved_term,avoid_terms=EXCLUDED.avoid_terms,kind=EXCLUDED.kind,explanation=EXCLUDED.explanation,is_active=EXCLUDED.is_active;

INSERT INTO rule_patterns (id,guideline_id,kind,pattern,replacement,case_sensitive,note,channel,is_active) VALUES
('RP-001','G-001','phrase','removes all acne overnight','helps reduce the appearance of acne with regular use',FALSE,'Flags an unsupported absolute acne-removal claim.',NULL,TRUE),
('RP-002','G-001','regex',E'\\b100%\\s+clear\\s+skin\\b','clearer-looking skin',FALSE,'Flags an absolute clear-skin guarantee.',NULL,TRUE),
('RP-003','G-001','phrase','guaranteed','designed to',FALSE,'Flags guarantee language.',NULL,TRUE),
('RP-004','G-001','regex',E'\\b100%\\s+(protection|secure|safe)\\b','helps protect',FALSE,'Flags absolute 100 percent safety or protection claims.',NULL,TRUE),
('RP-005','G-002','phrase','fastest','quick-acting',FALSE,'Flags an unsupported speed superlative.',NULL,TRUE),
('RP-006','G-002','phrase','best in india','loved by many customers',FALSE,'Flags an unsupported comparative superlative.',NULL,TRUE),
('RP-007','G-002','regex',E'\\b#1\\b','',FALSE,'Flags an unsupported number-one claim.',NULL,TRUE),
('RP-008','G-003','phrase','clients','customers',FALSE,'Replaces disallowed customer terminology.',NULL,TRUE),
('RP-009','G-003','phrase','users','customers',FALSE,'Replaces disallowed customer terminology.',NULL,TRUE),
('RP-010','G-010','name_variant','GreenGlow Face Wash','GreenGlow Tea Tree Face Wash',FALSE,'Replaces an abbreviated product name with the approved name.',NULL,TRUE),
('RP-011','G-004','required_text','Results may vary from person to person.','',FALSE,'Checks required skincare disclaimer on Instagram.','Instagram',TRUE),
('RP-012','G-004','required_text','Results may vary from person to person.','',FALSE,'Checks required skincare disclaimer in ads.','Ad',TRUE),
('RP-013','G-004','required_text','Results may vary from person to person.','',FALSE,'Checks required skincare disclaimer in email.','Email',TRUE),
('RP-014','G-009','confidential_term','Project Aurora','',FALSE,'Flags an internal unreleased project name.',NULL,TRUE),
('RP-015','G-009','confidential_term','unreleased','',FALSE,'Flags disclosure language about unreleased products.',NULL,TRUE),
('RP-016','G-008','phrase','cures eczema','may help soothe dry skin',FALSE,'Flags a medical treatment claim and suggests safer wording.',NULL,TRUE)
ON CONFLICT (id) DO UPDATE SET guideline_id=EXCLUDED.guideline_id,kind=EXCLUDED.kind,pattern=EXCLUDED.pattern,replacement=EXCLUDED.replacement,case_sensitive=EXCLUDED.case_sensitive,note=EXCLUDED.note,channel=EXCLUDED.channel,is_active=EXCLUDED.is_active;

INSERT INTO assets (id,label,asset_type,version,status,hex,usage_note,metadata) VALUES
('LOGO-V1','GreenGlow logo version 1','logo',1,'deprecated',NULL,'Deprecated. Do not use in new content.','{"version_label":"V1"}'),
('LOGO-V2','GreenGlow logo version 2','logo',2,'deprecated',NULL,'Deprecated. Do not use in new content.','{"version_label":"V2"}'),
('LOGO-V3','GreenGlow logo version 3','logo',3,'approved',NULL,'Use this logo only. Do not stretch, recolour or crop.','{"version_label":"V3"}'),
('COL-GREEN','GreenGlow brand green','colour',1,'approved','#2E7D4F','Approved brand colour.','{"hex":"#2E7D4F"}'),
('FONT-BRAND','GreenGlow Sans','font',1,'approved',NULL,'Approved brand font.','{"font_family":"GreenGlow Sans"}')
ON CONFLICT (id) DO UPDATE SET label=EXCLUDED.label,asset_type=EXCLUDED.asset_type,version=EXCLUDED.version,status=EXCLUDED.status,hex=EXCLUDED.hex,usage_note=EXCLUDED.usage_note,metadata=EXCLUDED.metadata,updated_at=now();

INSERT INTO sample_drafts (id,title,channel,body_text,image_url,alt_text,blurb) VALUES
('SD-01','Face wash launch caption','Instagram','Get naturally glowing skin with GreenGlow Tea Tree Face Wash! Removes all acne overnight and gives you 100% clear skin. Made with natural ingredients and dermatologically tested.',NULL,NULL,'Intentional test draft with absolute claims, abbreviated-name risk avoided in this sample, and missing disclaimer.'),
('SD-02','Festive offer email','Email','Hello clients, our festive offer is here: get 30% off GreenGlow products before the offer ends!',NULL,NULL,'Intentional test draft with incorrect discount, disallowed terminology, and missing disclaimer.'),
('SD-03','Face wash product description','Website','Meet GreenGlow Tea Tree Face Wash, made with tea tree and neem extract. It is paraben-free, sulphate-free, and dermatologically tested. It helps reduce the appearance of blemishes with regular use.',NULL,NULL,'Clean reference draft using approved name and supported claims.')
ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,channel=EXCLUDED.channel,body_text=EXCLUDED.body_text,image_url=EXCLUDED.image_url,alt_text=EXCLUDED.alt_text,blurb=EXCLUDED.blurb;

COMMIT;
