-- 02_demo_people_products.sql
-- Idempotent seed for demo users, teams, and the GreenGlow product line.
BEGIN;

INSERT INTO teams (name, description) VALUES
('Marketing', 'Campaigns, brand communications, and social content'),
('Sales', 'Sales enablement, promotional offers, and customer pricing'),
('Brand', 'Brand governance and approved facts'),
('Legal', 'Claims review and compliance')
ON CONFLICT (name) DO NOTHING;

INSERT INTO users (id, name, email, role, initials, title, avatar_color, team, is_demo_login, persona_description, demo_route) VALUES
('user-creator', 'Maya Chen', 'maya@greenglow.demo', 'creator', 'MC', 'Content Creator', '#6A8F72', 'Marketing', TRUE, 'Creates marketing and social content for GreenGlow.', '/content'),
('user-manager', 'Jordan Lee', 'jordan@greenglow.demo', 'manager', 'JL', 'Brand Manager', '#315B45', 'Marketing', TRUE, 'Owns brand governance, approved facts, and brand assets.', '/brand'),
('user-reviewer', 'Priya Shah', 'priya@greenglow.demo', 'reviewer', 'PS', 'Brand Reviewer', '#8B6F9E', 'Sales', TRUE, 'Reviews promotional content and offer accuracy.', '/review'),
('user-admin', 'Alex Morgan', 'alex@greenglow.demo', 'admin', 'AM', 'Workspace Admin', '#607D8B', 'Sales', TRUE, 'Administers the workspace and supports compliance review.', '/dashboard')
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  email = EXCLUDED.email,
  role = EXCLUDED.role,
  initials = EXCLUDED.initials,
  title = EXCLUDED.title,
  avatar_color = EXCLUDED.avatar_color,
  team = EXCLUDED.team,
  is_demo_login = EXCLUDED.is_demo_login,
  persona_description = EXCLUDED.persona_description,
  demo_route = EXCLUDED.demo_route,
  updated_at = now();

INSERT INTO products (id, name, approved_name, category, is_released) VALUES
('P-001', 'GreenGlow Tea Tree Face Wash', 'GreenGlow Tea Tree Face Wash', 'skincare', TRUE),
('P-002', 'GreenGlow Sunscreen SPF 50', 'GreenGlow Sunscreen SPF 50', 'skincare', TRUE),
('P-003', 'GreenGlow Cleansing Milk', 'GreenGlow Cleansing Milk', 'skincare', TRUE),
('P-004', 'GreenGlow Moisturizer Plus', 'GreenGlow Moisturizer Plus', 'skincare', TRUE)
ON CONFLICT (id) DO UPDATE SET
  name = EXCLUDED.name,
  approved_name = EXCLUDED.approved_name,
  category = EXCLUDED.category,
  is_released = EXCLUDED.is_released;

COMMIT;
