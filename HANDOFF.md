# BrandGuard Frontend Handoff & Architecture

## Stack
- Vite, React, TypeScript, Tailwind CSS.
- Note: Zustand and axios from the original plan are not used; state is managed via React hooks/state and standard native `fetch` wrappers.

## Backend Route Mappings
- **Approval routes**: live in `backend\app\routes\approval.py`.
- **Comments and revisions**: use `backend\app\routes\workflow.py`.
- **Review summary and queue**: use `backend\app\routes\review.py`.

## Pages Not Yet Wired to the API
- **Analytics**: Needs an agreed endpoint.
- **Alerts**: Needs owner confirmation.
- **Guideline file upload**: Backend processing endpoint not yet finalized.
- **Guideline version history**: No backend endpoint available yet.

## Configuration & Environment
- **Demo role switcher**: Hidden unless `VITE_SHOW_DEMO_SWITCHER=true` is set in `frontend\.env.local`.

