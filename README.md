# BrandGuard

AI-powered pre-publication brand governance platform for GreenGlow (fictional skincare company).

BrandGuard inspects brand marketing content prior to publication against approved guidelines, verified facts, and terminology glossaries, enforcing safety gates, approval hierarchies, and live impact tracking.

---

## Architecture Overview

- **Backend**: FastAPI + psycopg3 (raw SQL with PostgreSQL 16 + pgvector) running on port `8000`.
- **Database**: PostgreSQL 16 with pgvector on host port `5433` (container port `5432`).
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide icons, TipTap rich text editor running on port `5173`.
- **AI Engine**: Google Gemini integration with deterministic rule engine fallback.

---

## Quick Start & Run Instructions

### 1. Start Backend Stack with Docker Compose

Ensure Docker Desktop is running, then build and start the database and API containers:

```bash
docker compose up -d --build
```

Verify service health:
```bash
curl.exe http://localhost:8000/api/health
# Response: {"status":"ok","database":"ok"}
```

---

### 2. Reset and Seed Database with Real Data

Reset the database to clean demo seeds (creates personas, GreenGlow product lines, approved facts, guidelines, and demo drafts):

**Windows (PowerShell):**
```powershell
.\scripts\reset_demo_db.ps1
```

**Linux / macOS (Bash):**
```bash
chmod +x ./scripts/reset_demo_db.sh
./scripts/reset_demo_db.sh
```

---

### 3. Start the Frontend Application

In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at [http://localhost:5173](http://localhost:5173).

---

### 4. Run the Automated End-to-End Verification Check

Run the 11-step end-to-end workflow verification script against the live API and database:

**Windows (PowerShell / Command Prompt):**
```powershell
python scripts\e2e_check.py
```

**Linux / macOS:**
```bash
python scripts/e2e_check.py
```

The script runs the complete lifecycle:
1. Admin guideline upload (`.md`)
2. Admin fact creation with evidence
3. Creator draft creation & rule check run
4. Creator accept/reject decision loop
5. Creator submission for review
6. Reviewer critical findings gate check (HTTP 409 verification)
7. Reviewer approval & audit revision history logging
8. Manager publishing & timestamp verification
9. Admin fact update & revalidation alert dispatch
10. Reviewer alert status update
11. Analytics metrics aggregation from real rows

All 11 steps exit with `PASS`. Full run reports are logged in [docs/E2E_RESULTS.md](docs/E2E_RESULTS.md).

---

### 5. Running the Backend Test Suite

To run all backend unit and API integration tests without Docker:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
$env:DATABASE_URL = "postgresql://brandguard:brandguard_dev_password@localhost:5433/brandguard"
python -m pytest -q
```

All 238 tests pass.

---

## Demo Personas & Roles

Use the Demo Login screen at `/demo-login` or the API endpoint `POST /api/auth/demo-login` with `{"userId": "<id>"}`:

| Persona | Name | Role | Team | Focus |
| :--- | :--- | :--- | :--- | :--- |
| `user-creator` | Maya Chen | Creator | Marketing | Authoring posts, running compliance checks, resolving findings. |
| `user-reviewer` | Priya Shah | Reviewer | Legal | Review queue, approving content, verifying critical policy gates. |
| `user-manager` | Jordan Lee | Manager | Marketing | Publishing approved content, reviewing team analytics. |
| `user-admin` | Alex Morgan | Admin | Brand | Managing guidelines, approving knowledge facts, uploading policies. |
