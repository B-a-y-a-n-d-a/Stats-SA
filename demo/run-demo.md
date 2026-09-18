# Demo Day Run Script

Mirrors [docs/05-mvp-scope-and-roadmap.md](../docs/05-mvp-scope-and-roadmap.md) Section 2 ("Demo Script") step-for-step — specs/011-frontend-shell-integration/spec.md's acceptance criterion is that this file matches that section exactly, so if the two ever disagree, docs/05 is the source of truth and this file is out of date.

Timed for a 5-8 minute judging slot. Rehearse this twice against a timer before the real session (Risk Register).

## Setup (do this before judges arrive, not during the slot)

1. Copy `.env.example` to `.env` in the repo root and fill in `LLM_API_KEY` with a real Anthropic key. If you don't have one (or the venue Wi-Fi is unreliable — see the Risk Register below), set `LLM_PROVIDER=fake` instead: the whole app still works end to end, generated answers just quote the retrieved source directly rather than through a real model call. Prefer a real key for the actual judged run.
2. From `infra/`: `docker compose up -d --build` — brings up Postgres (pgvector), the backend API, and the frontend, and reuses the same Postgres volume across restarts so re-running this is safe.
3. Run migrations, seed the 4 demo accounts, and ingest the pre-seeded demo document (all one-time, idempotent — safe to re-run if you reset the stack):
   ```bash
   cd backend
   alembic upgrade head
   python -m app.db.seed
   python -m scripts.ingest_seed_set
   ```
   The last command ingests exactly one document — the QLFS Q2 2026 media release (see [seed-data-for-demo/README.md](seed-data-for-demo/README.md)). The GDP fact sheet used in step 5 below is deliberately **not** ingested here — you upload it live, on stage, in that step.
4. Open `http://localhost:5173` in the browser you'll present from. Pre-stage a second tab or window if you want the Curator-Admin file picker ready to go for step 5 (Risk Register: "Pre-stage browser tabs and role logins").
5. Confirm the nav bar's role switcher shows "Not logged in" — the demo starts logged out, as the public.

## The script

### 1. Public query, direct answer

Stay on the **Public** tab (`/`, no login needed — this is the embedded-widget mock of the Stats SA page). Submit:

> What was the latest quarterly unemployment rate?

Expect: a direct, plain-language answer, a confidence-score badge, and a citation linking to the QLFS Q2 2026 release you seeded in setup.

### 2. Escalation on a sensitive query

Switch to the **Media** tab (`/`, still no login needed — same as Public, the channel is what changes). Submit as a media enquiry (fill in a name/organisation/email — anything plausible, e.g. "Jane Reporter" / "Daily News" / `jane@dailynews.example`):

> Why did the unemployment rate change and what does it mean for the economy?

Expect: a confirmation that the enquiry was received, *not* an answer — media queries always escalate to the Review Console regardless of confidence.

### 3. Official review and approval

Use the role switcher (top-right of the nav bar) to log in as **Communications Official**. Open the **Review** tab. Find the queued draft from step 2, expand it, show its citations and confidence score, edit one sentence of the body, then click **Edit then Approve** (or **Approve** if you'd rather not edit live) to submit it.

Expect: the item disappears from the queue (it's now approved) and its response is now in the communication-memory repository, ready for step 4.

### 4. Communication memory reuse

Still logged in as Communications Official is fine — switch back to **Media** (no login required either way) and submit a second, related media enquiry:

> Why did the unemployment rate change this quarter?

Then switch back to **Communications Official** → **Review**. Expect: the new item's "Suggested reuse" section shows the step 3 response as a match, with a visible similarity score.

### 5. Curator-admin live source addition

Use the role switcher to log in as **Curator Admin**. Open the **Curator Admin** tab. Upload a new source:

- File: `backend/tests/fixtures/P0441_factsheetA.pdf` (the GDP fact sheet — see [seed-data-for-demo/README.md](seed-data-for-demo/README.md) for why it's held back until now)
- Title: `GDP Fact Sheet A - Growth in value added and GDP, Q2 2026`
- URL: `https://www.statssa.gov.za/publications/P0441/Fact sheet A - Q2 2026.pdf`
- Category: `Press Statement`
- Published date: `2026-09-08`

Click **Upload source**. Expect it to appear in the sources table as "Current," version 1.

Then switch to **Public** and ask a question only that document can answer:

> How did GDP change in the manufacturing industry in Q2 2026?

Expect: a direct, cited answer pointing at the document you just uploaded — proof the registry re-indexed live, on stage.

### 6. Audit trail

Log in as **Communications Official** or **Curator Admin** (either can see the log) and open the **Audit Log** tab. Expect entries for every action just demoed — query submission, retrieval, generation, escalation, the edit/approval decision, and the source upload — each with a timestamp and an actor identity.

## If something goes wrong on the day

- **Venue Wi-Fi or the Anthropic API is down**: set `LLM_PROVIDER=fake` in `.env` and restart the backend (`docker compose restart backend`). Every step above still works — see step 1's setup note.
- **A judge asks to see a rejected/re-reviewed item**: `POST /api/review/{draft_id}/decide` with `decision: "reject"` puts it back in the queue with a reason attached, visible on a re-expand — not scripted above, but the Review Console supports it if asked.
- **Full outage**: fall back to the pre-recorded run-through (Risk Register) rather than debugging live in front of judges.
