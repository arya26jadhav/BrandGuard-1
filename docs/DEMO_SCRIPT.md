# BrandGuard Demo Script (Member 3 section: image checks and fact alerts)

## Setup (before the demo)
1. Start Postgres and load `data/schema.sql`, then `data/seeds/01_foundation.sql` and `data/seeds/04_living.sql`.
2. Start the backend from `backend/`: `uvicorn app.main:app --port 8000`.
3. Start the frontend: `npm run dev` in `frontend/`.
4. Sign in as `user-creator` (Maya Chen) in one window, and as `user-reviewer` in another.

## Part A: Image checks (about 1 minute)
1. Show `test_data/images/low_contrast_ad.png`. Say: "This ad uses light grey text on white."
2. Run `python -m scripts.measure_contrast`. Point out the result: 1.50:1, which fails WCAG AA (4.5:1).
3. Show `approved_logo_v3.2.png`. Say: "The logo check compares against this approved version."

## Part B: Fact change alerts (about 2 minutes)
1. As `user-reviewer`, open the Products and Facts page. Find `F-004`, "Face wash price" (Rs 349, 100 ml).
2. Change the price to Rs 399 and save. This calls `PATCH /api/knowledge/facts/F-004`.
3. Say: "Three live posts used this price. The system finds them through the fact links."
4. As `user-creator` (Maya Chen), open Alerts. Show the alert for `LIV-01`, priority High, with the old and new price.
5. Click Dismiss. Confirm the alert status changes.
6. Say: "Only Maya, who owns LIV-01, gets this alert. Other teams don't see it."

## Part C: Optional Slack (if configured)
1. Set `SLACK_BOT_TOKEN` and `SLACK_CHANNEL_ID` in `backend/.env`.
2. Repeat Part B step 2 and show the message in the channel.
3. If Slack isn't set up, skip this part. The demo works without it.

## Known limits to mention
- Only posts that were checked get alerts. Planned fix: scan published posts for the fact text.
- Logo matching uses pHash, which can't reliably catch distorted logos. OpenCLIP is the planned upgrade.