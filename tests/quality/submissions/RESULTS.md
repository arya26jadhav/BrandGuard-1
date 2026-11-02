# Labelled evaluation results (phase 2)

Status: **not run yet.** The runner and scorer are ready, but the run needs a Gemini key and a disposable database with the guideline seeds loaded.

## How to run

From `backend`, with `DATABASE_URL` pointing at a disposable database (never `brandguard`), `GEMINI_API_KEY` set, and `BRANDGUARD_VISION_MODEL` set:

```powershell
python scripts/run_submission_eval.py ..\tests\quality\submissions\manifest.json results.json
python scripts/score_submissions.py ..\tests\quality\submissions\manifest.json results.json
```

## Record each run here

| Date | Model | Recall (critical) | Findings rejected | Holds correct | Notes |
|---|---|---|---|---|---|
| _not yet run_ | | | | | |

Targets (proposals until the first run): recall at least 70% on critical problems, at most 30% of findings rejected.