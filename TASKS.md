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
| 6 | Review console | [#6](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/6) | [specs/006](specs/006-review-console/spec.md) | 1, 5, 9 | Done | Claude |
| 7 | Communication memory &amp; reuse | [#7](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/7) | [specs/007](specs/007-communication-memory/spec.md) | 1, 3, 6 | Done | Claude |
| 8 | Curator-admin UI | [#8](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/8) | [specs/008](specs/008-curator-admin/spec.md) | 1, 2, 9 | Not started | Unclaimed |
| 9 | RBAC &amp; auth | [#9](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/9) | [specs/009](specs/009-rbac-auth/spec.md) | 1 | Done | Devin |
| 10 | Audit log | [#10](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/10) | [specs/010](specs/010-audit-log/spec.md) | 1 | Done | Claude |
| 11 | Frontend shell &amp; end-to-end integration | [#11](https://github.com/B-a-y-a-n-d-a/Stats-SA/issues/11) | [specs/011](specs/011-frontend-shell-integration/spec.md) | 4-10 | Not started | Unclaimed |

**Status:** Tasks 1-7, 9 and 10 are merged to `master` — only 8 and 11 remain. All fully live-verified against a real Postgres container; full backend suite is 82/82 passing on `master` right now. Task 8 is next; 11 needs it done first (it needs everything).

**Task 7 closed the loop `reuse_match` left open in Task 6:** the review queue's `reuse_match` field is real now — approving a draft writes a `communication_memory` row, and the next similar query surfaces it with a keyword-overlap score. Verified live by replaying demo script step 4 exactly. `GET /api/memory/search` also exists for direct lookup (comms_official/curator_admin only).

**Recurring lesson worth internalizing for Task 8 or 11:** twice now (Tasks 5+9, then independently again in Task 7's parallel build) two people/agents writing similar test files in parallel, without seeing each other's code, have duplicated logic that should have been shared — first the `app.dependency_overrides.clear()` bug, now a duplicated serializer function. Neither was harmful, both were caught and fixed, but if you're building something with a natural shared piece (a serializer, a helper), search the codebase for it first.

**Task 6 and 10 both went straight to the real `require_role(...)` dependency** rather than a temporary header — Task 9 had already merged by the time either was built. Same applies to 8.

**Real bugs caught by live testing, none visible from code review alone:**
- passlib/bcrypt incompatibility (PR #13)
- models.py enum-encoding mismatch (PR #15)
- default confidence threshold (0.75) was an untested guess that would have rejected every query — recalibrated to 0.4 (PR #16)
- stale fixture path in `seed_sources.yaml` left over from Task 2's own cleanup (PR #18)
- **a real cross-test-file bug, found twice:** `test_media_query.py` and (independently) `test_auth.py` each did `app.dependency_overrides.clear()` in their fixture teardown — since that dict is shared by the whole FastAPI app, it silently wiped `test_public_query.py`'s own override too, making its tests fall through to a real Postgres connection instead of their intended in-memory SQLite. Only surfaced by running the *full* suite together, not any file in isolation. Fixed in both places to save/restore only the key each fixture itself sets — worth remembering as the pattern for any future test file that overrides `get_db`.

Two agents were working in parallel without claiming issues first this session — "Devin" (an AI agent, per its commit author) had PRs open for Tasks 5 and 9 with neither issue self-assigned. Both are merged now; issues #5 and #9 auto-closed on merge.

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
