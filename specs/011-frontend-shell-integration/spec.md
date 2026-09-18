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

- [ ] All 6 demo script steps run successfully against `docker-compose up`, in order, without manual database edits between steps.
- [ ] Switching roles in the UI actually calls `/api/auth/login` and uses the returned JWT, not a hardcoded bypass.
- [ ] `demo/run-demo.md` exists and matches the docs' demo script step-for-step.

## Implementation Tasks

- [ ] `frontend/src/App.tsx` — routing + role switcher
- [ ] `frontend/src/styles/` — shared theme
- [ ] `demo/run-demo.md`
- [ ] `demo/seed-data-for-demo/` — the specific curated documents and 2 demo queries used in the script
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
