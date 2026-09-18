# Demo seed data

specs/011-frontend-shell-integration/spec.md's curated set for the judged demo — deliberately small (2 real documents), not the full 15-30 document registry docs/05-mvp-scope-and-roadmap.md scopes for later.

## Pre-seeded before the demo starts

- **`P0211_QLFS_Q2_2026_media_release.pdf`** — the real Stats SA Quarterly Labour Force Survey (QLFS) Q2 2026 media release, downloaded from `statssa.gov.za/publications/P0211/`. Listed in [`backend/scripts/seed_sources.yaml`](../../backend/scripts/seed_sources.yaml) and ingested by `python -m scripts.ingest_seed_set` (from `backend/`) — see [run-demo.md](../run-demo.md)'s setup step.
- This is the *only* document in the registry when the demo starts. It answers demo script steps 1, 2 and 4 (all about the unemployment rate).

## Deliberately held back — uploaded live during step 5

- **The GDP fact sheet**, already committed at [`backend/tests/fixtures/P0441_factsheetA.pdf`](../../backend/tests/fixtures/P0441_factsheetA.pdf) (reused from specs/002's own test fixture — not duplicated here). It is intentionally **not** listed in `seed_sources.yaml`, so the registry has no GDP content until the Curator-Admin uploads it live in step 5.
- If you ever add it to `seed_sources.yaml` for some other reason, update run-demo.md and this file to pick a different step 5 document — the whole point of that step is asking a question the registry could not have answered a moment earlier.

## The exact demo queries

Kept here as the single source of truth; [run-demo.md](../run-demo.md) quotes these verbatim so the two files can't drift apart.

| Step | Channel | Query text |
|---|---|---|
| 1 | Public | `What was the latest quarterly unemployment rate?` |
| 2 | Media | `Why did the unemployment rate change and what does it mean for the economy?` |
| 4 | Media | `Why did the unemployment rate change this quarter?` |
| 5 | Public | `How did GDP change in the manufacturing industry in Q2 2026?` |

Step 4's wording is deliberately close to step 2's (`why did the unemployment rate change`) — specs/007's reuse matching is keyword-overlap, not semantic, so the words need to actually overlap for the reuse match to show up with a clear score.

Step 5's wording is the exact question already live-verified against this same GDP fact sheet fixture during specs/003 and specs/008 (real cosine similarity 0.47-0.54, comfortably above the 0.4 confidence threshold) — don't change it without re-verifying live.
