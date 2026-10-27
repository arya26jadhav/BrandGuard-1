# BrandGuard backend

FastAPI + PostgreSQL. The AI claim check uses Google Gemini only.

## Setup (PowerShell, from `backend`)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # then fill in DATABASE_URL, JWT_SECRET, GEMINI_API_KEY
uvicorn app.main:app --reload --port 8000
```

Wait for `Application startup complete.` Keep real keys only in `backend\.env`. That file is git-ignored.

## Check pipeline (plan section 1 to 4)

1. **Rules** (`pipeline/rules.py`): phrase, regex, confidential-term and required-text rules from `rule_patterns`. No AI, exact offsets.
2. **Evidence** (`ai/evidence_stub.py`, to be replaced by Person 3's `get_evidence`).
3. **AI claim check** (`services/ai_check.py`, `ai/client.py`): one Gemini call per check, validated by Pydantic. Findings are kept only if the source ID is in the evidence, the quote appears exactly in the post, and the finding does not overlap a rule hit. Confidence below 0.60 is marked for human review. Invalid JSON gets one retry with the problem described. Results are cached by a hash of post text, channel, prompt version, model and evidence versions.
4. If the AI stage fails for any reason, the response has `aiStatus: "fallback"` and rules results only. Nothing crashes.

`ai_calls` records each model call (model, status, latency, tokens, error). It never stores the post text.

## Settings

| Name | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `JWT_SECRET` | signs demo login tokens |
| `GEMINI_API_KEY` | Gemini key. If blank, the AI stage is skipped |
| `BRANDGUARD_MODEL` | Gemini model name, default `gemini-flash-lite-latest` |
| `FRONTEND_ORIGINS` | comma-separated CORS origins |

## Tests

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m pytest -q
```

The AI tests mock the network, so they run without a key.

## Planted-mistake evaluation

Start the API first, then:

```powershell
python -m tests.run_eval
```

It exits with code 2 if any post did not get an AI result (`success` or `cached`). A rules-only run is never reported as an AI result. Results are written to `data/eval_results.json`.

## Prompt changes

Edit `ai/prompt.py` and bump `PROMPT_VERSION`. The version is part of the cache key, so old answers are not reused.
