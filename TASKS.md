# Task Board

This file is the at-a-glance snapshot. **The source of truth for claiming a task is the GitHub Issue**, not this table — see [CONTRIBUTING.md](CONTRIBUTING.md) for why and how. Update this table's Status/Owner columns whenever an issue's state changes, in the same PR that changes the state, so this file never drifts far from GitHub.

## How to avoid two people working on the same thing

1. Before you start anything, open the [Issues board](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues) and find the task.
2. **Assign yourself to the issue** and move it to "In Progress" on the [Project board](https://github.com/B-a-y-a-n-d-a/Stats-SA/projects). An unassigned issue is up for grabs; an assigned one is not — ask before touching someone else's.
3. Create your branch from the latest `master` using the exact branch name in the spec (e.g. `feature/004-public-query-widget`).
4. Work only inside the files your spec lists under "Implementation Tasks." If you need to touch a file another task owns, comment on their issue first.
5. Open a PR into `master` when done, tick the spec's checkboxes in the PR description, and link the issue (`Closes #<n>`) so it auto-closes and the board updates itself.
6. Do not start your next task until your current PR is merged — this keeps `master` always in a working state for whoever pulls next.

## Task Table

| # | Task | Issue | Spec | Depends on | Status | Owner |
|---|---|---|---|---|---|---|
| 0 | MVP technical decisions (ADR, reference only, no branch) | — | [specs/000](specs/000-mvp-technical-decisions.md) | — | Done | Claude |
| 1 | Data model &amp; Approved Sources Registry | [#1](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/1) | [specs/001](specs/001-data-model-registry/spec.md) | none | Done | Claude |
| 2 | Ingestion pipeline | [#2](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/2) | [specs/002](specs/002-ingestion-pipeline/spec.md) | 1 | Done | Claude |
| 3 | Retrieval, confidence gate &amp; citation enforcement | [#3](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/3) | [specs/003](specs/003-retrieval-confidence-gate/spec.md) | 1, 2 | Done | Claude |
| 4 | Public query API &amp; widget | [#4](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/4) | [specs/004](specs/004-public-query-widget/spec.md) | 1, 3 | Done | Claude |
| 5 | Media query intake &amp; draft generation | [#5](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/5) | [specs/005](specs/005-media-query-draft/spec.md) | 1, 3 | Done | Devin |
| 6 | Review console | [#6](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/6) | [specs/006](specs/006-review-console/spec.md) | 1, 5, 9 | Not started | Unclaimed |
| 7 | Communication memory &amp; reuse | [#7](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/7) | [specs/007](specs/007-communication-memory/spec.md) | 1, 3, 6 | Not started | Unclaimed |
| 8 | Curator-admin UI | [#8](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/8) | [specs/008](specs/008-curator-admin/spec.md) | 1, 2, 9 | Not started | Unclaimed |
| 9 | RBAC &amp; auth | [#9](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/9) | [specs/009](specs/009-rbac-auth/spec.md) | 1 | Done | Devin |
| 10 | Audit log | [#10](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/10) | [specs/010](specs/010-audit-log/spec.md) | 1 | In Progress | Claude |
| 11 | Frontend shell &amp; end-to-end integration | [#11](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/11) | [specs/011](specs/011-frontend-shell-integration/spec.md) | 4-10 | Not started | Unclaimed |

**Status:** Tasks 1-5 and 9 are merged to `master`, all fully live-verified against a real Postgres container. Task 10 is in progress now (real Postgres/browser testing, same standard as every other task). Tasks 6, 7 and 8 are open to claim — 6 and 8 now depend on the *real* `require_role` dependency (`app.core.security`, Task 9 merged), not a temporary header.

**Real bugs caught by live testing, none visible from code review alone:**
- passlib/bcrypt incompatibility (PR #13)
- models.py enum-encoding mismatch (PR #15)
- default confidence threshold (0.75) was an untested guess that would have rejected every query — recalibrated to 0.4 (PR #16)
- stale fixture path in `seed_sources.yaml` left over from Task 2's own cleanup (PR #18)
- **a real cross-test-file bug, found twice:** `test_media_query.py` and (independently) `test_auth.py` each did `app.dependency_overrides.clear()` in their fixture teardown — since that dict is shared by the whole FastAPI app, it silently wiped `test_public_query.py`'s own override too, making its tests fall through to a real Postgres connection instead of their intended in-memory SQLite. Only surfaced by running the *full* suite together, not any file in isolation. Fixed in both places to save/restore only the key each fixture itself sets — worth remembering as the pattern for any future test file that overrides `get_db`.

**Task 5's coordination note, resolved:** `public_query.py`'s inline Draft-creation (Task 4) still hasn't been refactored to use the shared `draft_builder.build_draft` (Task 5, now merged) — left as-is since it's out of scope for both tasks' original PRs; worth a small follow-up.

Two agents were working in parallel without claiming issues first this session — "Devin" (an AI agent, per its commit author) had PRs open for Tasks 5 and 9 with neither issue self-assigned. Both are merged now; issues #5 and #9 should still be marked closed/assigned for the record.

## Suggested parallel lanes

Once **1** is merged, these can run at the same time without touching each other's files:

- **Lane A (backend core):** 2 -> 3
- **Lane B (auth/logging, small and independent):** 9, 10 — good tasks to pick up early since almost nothing else can finish without them
- **Lane C (public path):** 4 (needs 3 merged first)
- **Lane D (media path):** 5 -> 6 -> 7 (needs 3 merged first)
- **Lane E (admin):** 8 (needs 2 merged first)

**11** is last — it is integration, not new capability, and needs everything else in.

## Status legend

`Not started` -> `In Progress` -> `In Review` (PR open) -> `Done` (merged to master)
