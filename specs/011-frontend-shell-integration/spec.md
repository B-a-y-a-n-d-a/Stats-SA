# 011 - Frontend Shell &amp; End-to-End Integration

Branch: `feature/011-frontend-shell-integration`
Depends on: all of 004-010 functionally complete (this is the last task before demo rehearsal)
Blocks: none
Docs reference: [docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md) Section 2 (Demo Script)

## Specification

This task does not add a new capability. It wires the individually-built views into one coherent app and runs the full demo script end to end.

1. `frontend/src/App.tsx` routing between: Public Widget (mock site), Media Intake, Review Console, Curator-Admin, Audit Log — gated by the logged-in demo role.
2. A role switcher for demo purposes (log in as any of the 4 seeded accounts).
3. Shared styling so the four views look like one product, not four prototypes stapled together.
4. Walk through all 6 demo script steps against the deployed `docker-compose` stack and fix any integration seams that only show up when real services talk to each other.
5. A `demo/run-demo.md` checklist teammates can follow live on demo day, mirroring [docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md) Section 2 exactly.

## Acceptance Criteria

- [x] All 6 demo script steps run successfully against `docker-compose up`, in order, without manual database edits between steps. Verified live, for real, against `infra/docker-compose.yml` (`docker compose up -d --build`, then `alembic upgrade head` / `python -m app.db.seed` / `python -m scripts.ingest_seed_set` inside the `backend` container, exactly as `demo/run-demo.md` documents) — drove the actual running app in a real browser through all 6 steps in order:
  1. Public query "What was the latest quarterly unemployment rate?" → answered, confidence 55%, cited the QLFS release.
  2. Media query "Why did the unemployment rate change and what does it mean for the economy?" → escalated, no direct answer.
  3. Logged in as Communications Official, opened the queued draft in Review, approved it.
  4. Media query "Why did the unemployment rate change this quarter?" → escalated, and its "Suggested reuse" section showed the step-3 response with a visible 75% match score.
  5. Logged in as Curator Admin, uploaded the GDP fact sheet live (via a synthetic `DataTransfer` file input in the browser session, not a manual click, but the same `POST /api/curator/sources` the UI form itself calls), then asked "How did GDP change in the manufacturing industry in Q2 2026?" as Public → answered, confidence 47%, cited the document just uploaded.
  6. Opened Audit Log → every action above appeared with a timestamp and actor identity (`source_ingested`, `review_decided`, `query_submitted`/`answer_generated` ×2).

  `LLM_PROVIDER=fake` was used for this run (see item 4 below) since no real `LLM_API_KEY` is available in this environment — the retrieval/confidence-gate/citation-enforcement/RBAC/audit pipeline this criterion actually exercises is identical either way; only the generated answer text's source (a real model vs. a templated quote of the same retrieved passage) differs. Re-run with a real key before the actual judged demo.
- [x] Switching roles in the UI actually calls `/api/auth/login` and uses the returned JWT, not a hardcoded bypass. Confirmed via the live run above: each role switch produced a real `POST /api/auth/login` network request (visible in the browser's network log) and the resulting JWT is what let `/review`, `/curator` and `/audit` render instead of `RequireRole`'s "log in as..." prompt — the same JWT every other view's `apiFetch` call already used.
- [x] `demo/run-demo.md` exists and matches the docs' demo script step-for-step.

## Implementation Tasks

- [x] `frontend/src/App.tsx` — routing + role switcher
- [x] `frontend/src/styles/` — shared theme
- [x] `demo/run-demo.md`
- [x] `demo/seed-data-for-demo/` — the specific curated documents and 2 demo queries used in the script
- [x] Update this file's checkboxes as you go, then open a PR into `master`

## Implementation notes

- **Frontend**: `frontend/src/styles/theme.ts` + `shared.ts` hold the deduplicated design tokens/CSSProperties; every existing view (`PublicWidget`, `MediaIntake`, `ReviewConsole`, `AuditLog`, `CuratorAdmin`) now spreads `shared` instead of redefining the same button/box/badge/table styles locally — `MediaIntake.tsx` had no styling at all before this task and got a full visual pass to match the rest. New: `frontend/src/api/auth.ts`, `frontend/src/auth/AuthContext.tsx`, `frontend/src/components/RoleSwitcher.tsx`, `frontend/src/components/RequireRole.tsx`.
- **Docker/deploy fixes, all found live bringing up `docker-compose up` for the first time** (this task's whole point, item 4 above) — none of these were visible from code review, only from actually building and running the stack:
  1. `frontend`'s production image served static files with `serve`, which has no API proxy — every `/api/*` call would 404 (the vite dev-server proxy in `vite.config.ts` only exists under `npm run dev`). Switched to `nginx:alpine` (`frontend/Dockerfile`, `frontend/nginx.conf`) which both serves the SPA and proxies `/api/` to the `backend` container.
  2. `backend`'s image installed the default (CUDA) `torch` wheel via `sentence-transformers`'s dependency resolution — 1GB+ of unused GPU packages (`triton`, `nvidia-*`) in a container with no GPU, and the huge download intermittently failed pip's own hash verification. Fixed by installing the CPU-only `torch` wheel first (`backend/Dockerfile`).
  3. `backend/scripts/ingest_seed_set.py`'s demo entry needs `demo/seed-data-for-demo/`, which lives outside `backend/`'s own Docker build context. Changed the `backend` service's build context to the repo root (`infra/docker-compose.yml`, `backend/Dockerfile`) so `demo/` can be copied in alongside `backend/` itself. Added a root `.dockerignore` so this wider context doesn't ship `.venv`/`node_modules`/`.git` to the daemon.
- **Backend**: added `LLM_PROVIDER=fake` (`backend/app/retrieval/llm_client.py`'s new `FakeLLMClient`) as a documented demo-resilience fallback — not scoped by the spec text above, but necessary to actually satisfy "all 6 demo script steps run successfully" in an environment (this one, and possibly the real venue on the day — see the Risk Register) with no working `LLM_API_KEY`. Selecting it doesn't change any of the retrieval/confidence/citation/RBAC/audit code paths the acceptance criteria care about — only which class answers the "what did the model say" question. Covered by `backend/tests/test_llm_client.py`.
- **Demo data**: `backend/scripts/seed_sources.yaml` now seeds the real QLFS Q2 2026 media release (downloaded from statssa.gov.za; see `demo/seed-data-for-demo/README.md`) instead of the GDP fact sheet — the GDP fact sheet is deliberately held back for the live upload in step 5.
- **A real test bug found only by actually running the live demo, then the test suite, back to back**: `tests/test_retrieval.py`'s fixture does `session.query(Source).delete()` against the real Postgres container to reset state before each run — after the live demo run above wrote real `audit_log` rows referencing a real `source_id` (specs/010's `audit_log.source_id` FK, which didn't exist when this fixture was written in specs/003), that delete started failing with a `ForeignKeyViolation` for the whole file. Fixed by also clearing `audit_log` in the same fixture. Nothing about specs/011's own code was wrong — this is a live-Postgres test assuming it's the only writer to a database that a manual demo run also legitimately writes to — but it's worth flagging for whoever next runs the demo and then the test suite (or vice versa).
