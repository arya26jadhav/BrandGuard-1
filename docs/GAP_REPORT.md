# Gap Report: End-to-End Real Data

Date: 2026-10-28
Branch: `feature/end-to-end-real-data`

## 1. Current API Routes (`/api`)

Generated from `backend/app/main.py`:

| Method | Path | Status / Handler |
|---|---|---|
| `POST` | `/api/auth/demo-login` | Implemented (`app.routes.auth`) |
| `GET` | `/api/auth/demo-users` | Implemented (`app.routes.auth`) |
| `GET` | `/api/auth/me` | Implemented (`app.routes.auth`) |
| `GET` | `/api/content` | Implemented (`app.routes.content`) |
| `POST` | `/api/content` | Implemented (`app.routes.content`) |
| `GET` | `/api/content/{content_id}` | Implemented (`app.routes.content`) |
| `PUT` | `/api/content/{content_id}` | Implemented (`app.routes.content`) |
| `POST` | `/api/content/{content_id}/approve` | Implemented (`app.routes.approval`) |
| `POST` | `/api/content/{content_id}/check` | Implemented (`app.routes.check`) |
| `GET` | `/api/content/{content_id}/comments` | Implemented (`app.routes.workflow`) |
| `POST` | `/api/content/{content_id}/comments` | Implemented (`app.routes.workflow`) |
| `GET` | `/api/content/{content_id}/findings` | Implemented (`app.routes.check`) |
| `POST` | `/api/content/{content_id}/publish` | Implemented (`app.routes.approval`) |
| `POST` | `/api/content/{content_id}/request-changes` | Implemented (`app.routes.approval`) |
| `GET` | `/api/content/{content_id}/revisions` | Implemented (`app.routes.content`) |
| `POST` | `/api/content/{content_id}/start-fixing` | Implemented (`app.routes.approval`) |
| `POST` | `/api/content/{content_id}/submit` | Implemented (`app.routes.approval`) |
| `GET` | `/api/content/{content_id}/versions` | Implemented (`app.routes.content`) |
| `PATCH` | `/api/findings/{finding_id}` | Implemented (`app.routes.findings`) |
| `GET` | `/api/health` | Implemented (`app.main`) |
| `GET` | `/api/knowledge/assets` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/facts` | Implemented (`app.routes.knowledge`) |
| `POST` | `/api/knowledge/facts` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/facts/{fact_id}` | Implemented (`app.routes.knowledge`) |
| `PATCH` | `/api/knowledge/facts/{fact_id}` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/facts/{fact_id}/history` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/glossary` | Implemented (`app.routes.knowledge`) |
| `POST` | `/api/knowledge/glossary` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/guidelines` | Implemented (`app.routes.knowledge`) |
| `POST` | `/api/knowledge/guidelines` | Implemented (`app.routes.knowledge`) |
| `POST` | `/api/knowledge/guidelines/upload` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/knowledge/guidelines/{guideline_id}` | Implemented (`app.routes.knowledge`) |
| `PATCH` | `/api/knowledge/guidelines/{guideline_id}` | Implemented (`app.routes.knowledge`) |
| `GET` | `/api/review/queue` | Implemented (`app.routes.review`) |
| `GET` | `/api/review/summary` | Implemented (`app.routes.review`) |
| `GET` | `/api/sources` | Implemented (`app.routes.sources`) |

### Missing API Endpoints Required:
1. `GET /api/knowledge/products` (Phase 2.1)
2. `GET /api/knowledge/guidelines/{guideline_id}/versions` (Phase 2.2)
3. `GET /api/alerts` and `PATCH /api/alerts/{id}` (Phase 2.3)
4. `GET /api/analytics/summary` (Phase 2.4)

---

## 2. Frontend Pages Audit (`frontend/src/pages/`)

| Page | Classification | Current API Calls / Data Source | Target State |
|---|---|---|---|
| `ComposePage.tsx` | **LIVE** | Calls `/api/content`, `/api/content/{id}`, `/api/content/{id}/check`, `/api/content/{id}/findings`, `/api/sources`, `/api/review`, `/api/findings/{id}` | Fully functional end-to-end. |
| `ContentPage.tsx` | **LIVE** | Calls `/api/content` | Fully functional; displays real content. |
| `LoginPage.tsx` | **LIVE** | Calls `/api/auth/demo-users`, `/api/auth/demo-login` | Fully functional. |
| `ReviewQueuePage.tsx` | **LIVE** | Calls `/api/auth/me`, `/api/sources`, `/api/review/queue`, `/api/content/{id}`, `/api/content/{id}/findings`, `/api/content/{id}/comments`, `/api/content/{id}/revisions`, `/api/content/{id}/approve`, `/api/content/{id}/request-changes`, `/api/content/{id}/publish` | Fully functional on real database items. |
| `ProductsFactsPage.tsx` | **MOCK** | Uses internal hardcoded `initialFacts` array; no `/api` calls | Wire to `GET /api/knowledge/products` and `GET /api/knowledge/facts`. |
| `BrandGuidelinesPage.tsx` | **MOCK** | Uses internal hardcoded `initialRules` / `initialTerms`; no `/api` calls | Wire to `GET /api/knowledge/guidelines`, `/api/knowledge/guidelines/{id}/versions`, `/api/knowledge/glossary`, `/api/knowledge/facts`, and wire upload to `POST /api/knowledge/guidelines/upload`. |
| `AlertsPage.tsx` | **MOCK** | Uses internal hardcoded `initialAlerts` array; no `/api` calls | Wire to `GET /api/alerts` and `PATCH /api/alerts/{id}`. |
| `AnalyticsPage.tsx` | **MOCK** | Uses local hardcoded state and mock toggles | Wire to `GET /api/analytics/summary`, remove mock toggles, hide empty cards. |
| `DemoLandingPage.tsx` | **STATIC** | Static persona selector | Informational landing; navigates to authenticated routes. |
| `RoutePlaceholder.tsx` | **MOCK** | Imports from `@/mocks/content`, `@/mocks/sources`, `@/mocks/alerts` | Placeholder for settings/unimplemented routes; clean up mock imports. |

---

## 3. Public Schema Database Tables Audit (PostgreSQL 16)

| Table | Backend Read | Backend Write | Usage Description |
|---|---|---|---|
| `users` | Yes | Yes (seeds) | Auth login, demo user list, user profile, creator/manager/reviewer checks. |
| `teams` | Yes | Yes (schema) | Validated team names for users and content. |
| `products` | Yes | Yes (seeds) | Referenced by facts; will be exposed via `GET /api/knowledge/products`. |
| `facts` | Yes | Yes | Product facts read by sources, evidence, impact; created and updated in knowledge routes. |
| `fact_versions` | Yes | Yes | Version history for fact modifications. |
| `guidelines` | Yes | Yes | Guidelines read by sources, checks, evidence; created/uploaded in knowledge routes. |
| `guideline_versions` | Yes (new) | Yes | Version history for guidelines; exposed via new endpoint. |
| `glossary` | Yes | Yes | Approved/avoid terms read by checks and knowledge routes. |
| `assets` | Yes | Yes (seeds) | Brand assets returned by `/api/knowledge/assets`. |
| `content` | Yes | Yes | Marketing/social drafts, revision status, approval moves, publishing. |
| `content_versions` | Yes | Yes | Snapshot versions of content body changes. |
| `check_runs` | Yes | Yes | Check execution history, rules and AI counts. |
| `findings` | Yes | Yes | Detected issues linked to check runs, sources, and content. |
| `decisions` | Yes (new) | Yes | Human accept/edit/reject actions on findings; read by analytics. |
| `revisions` | Yes | Yes | Audit log of workflow transitions and edits on content. |
| `comments` | Yes | Yes | Reviewer/creator discussion on drafts and specific findings. |
| `fact_content_links` | Yes | Yes | Links between published content and active facts for alert generation. |
| `alerts` | Yes (new) | Yes | Real-time notifications when facts change; updated via alert endpoints. |
| `ai_calls` | No | Yes | Telemetry logging of AI provider calls, tokens, latency. |
| `rule_patterns` | Yes | Yes (seeds) | Deterministic regex and phrase rules used by rule engine. |
| `sample_drafts` | No | Yes (seeds) | Pre-seeded draft templates. |
| `quality_metrics` | No | No | Benchmark quality precision/recall metrics (offline evaluation). |
| `notification_log` | No | Yes | Log of dispatched alerts/emails/slack messages. |
| `ai_cache` | Yes | Yes | LLM response caching keyed by input hash. |
| `embeddings` | No | No | Vector embeddings table for future semantic RAG retrieval. |

---

## 4. One-Line Plan Per Identified Gap

1. **Gap: Products endpoint missing** -> Implement `GET /api/knowledge/products` returning id, name, line, status from `products`.
2. **Gap: Guideline versions endpoint missing** -> Implement `GET /api/knowledge/guidelines/{guideline_id}/versions` returning newest first.
3. **Gap: Alerts list and status update missing** -> Implement `GET /api/alerts` (with optional status filter) and `PATCH /api/alerts/{id}` (recipient/admin guard).
4. **Gap: Analytics summary endpoint missing** -> Implement `GET /api/analytics/summary` computing KPIs, violation groupings, and review times from real rows.
5. **Gap: Missing comprehensive demo seeds** -> Add `data/seeds/02_demo_people_products.sql`, `data/seeds/03_demo_facts_guidelines.sql`, and `data/seeds/04b_demo_posts.sql`.
6. **Gap: Missing reproducible database reset scripts** -> Add `scripts/reset_demo_db.ps1` and `scripts/reset_demo_db.sh` that truncate and re-seed with counts printed.
7. **Gap: ProductsFactsPage uses mock data** -> Wire `ProductsFactsPage.tsx` to `/api/knowledge/products` and `/api/knowledge/facts` with empty states.
8. **Gap: BrandGuidelinesPage uses mock data and mock upload** -> Wire `BrandGuidelinesPage.tsx` to knowledge endpoints and real file upload, disabling out-of-scope edits.
9. **Gap: AlertsPage uses mock data** -> Wire `AlertsPage.tsx` to `/api/alerts` and PATCH updates; wire sidebar/header notification badges.
10. **Gap: AnalyticsPage uses mock data** -> Wire `AnalyticsPage.tsx` to `/api/analytics/summary`, remove mock toggles, hide cards below threshold.
11. **Gap: TopBar notification dropdown has hardcoded list** -> Populate TopBar notifications from `/api/alerts`.
12. **Gap: Mock modules in frontend** -> Remove imports from `frontend/src/mocks/` across pages and components.
13. **Gap: Automated End-to-End verification script missing** -> Create `scripts/e2e_check.py` testing the complete 11-step lifecycle against live API and DB.
