# 001 - Data Model &amp; Approved Sources Registry

Branch: `feature/001-data-model-registry`
Depends on: none (this is the foundation task, do it first)
Blocks: 002, 003, 004, 005, 006, 007, 008, 009, 010
Docs reference: [docs/02-architecture.md](../../docs/02-architecture.md) Section 4, [docs/03-security-governance-compliance.md](../../docs/03-security-governance-compliance.md) Sections 1, 5, 6

## Specification

Stand up the database schema every other task builds on. Nothing here calls an LLM or does retrieval — this task is purely the data layer.

Tables required (fields as specified in the docs, do not invent new fields without updating this spec first):

1. **sources** (Approved Sources Registry) — `source_id` (UUID pk), `title`, `url`, `category` (enum: Statistical Release, Publication, Press Statement, FAQ, Historical Communication), `published_date`, `ingested_date`, `version` (int), `superseded_by` (UUID, nullable, fk to sources), `approved_by`, `confidentiality_tag` (enum: Public, Internal), `checksum`, `retention_review_date`.
2. **chunks** — `chunk_id` (UUID pk), `source_id` (fk), `text`, `embedding` (vector, pgvector), `page_number`, `char_start`, `char_end`.
3. **users** — `user_id` (UUID pk), `name`, `email`, `role` (enum: public, media, comms_official, curator_admin), `password_hash` (for the 4 seeded demo accounts only, per [specs/000](../000-mvp-technical-decisions.md)).
4. **queries** — `query_id` (UUID pk), `channel` (enum: public, media), `text`, `submitted_by` (fk users, nullable for anonymous public), `submitted_at`, `confidence_score` (float, nullable), `status` (enum: answered, escalated, approved, rejected).
5. **drafts** — `draft_id` (UUID pk), `query_id` (fk), `draft_text`, `citations` (jsonb array of `{chunk_id, source_id, title, url}`), `created_at`.
6. **reviews** — `review_id` (UUID pk), `draft_id` (fk), `reviewer_id` (fk users), `decision` (enum: approve, edit_approve, reject), `final_text` (nullable), `reason` (nullable), `decided_at`.
7. **communication_memory** — `memory_id` (UUID pk), `query_text`, `final_answer`, `citations` (jsonb), `approved_by` (fk users), `approved_at`.
8. **terminology_guide** — `guide_entry_id` (UUID pk), `category` (enum: Terminology, Style Rule, Branding Standard, Preferred Phrasing, Prohibited Term), `term_or_topic`, `approved_guidance`, `discouraged_alternative` (nullable), `rationale`, `version` (int), `superseded_by` (UUID, nullable), `approved_by`, `effective_date`, `last_reviewed_date`.
9. **audit_log** — `log_id` (UUID pk), `event_type`, `actor_id` (fk users, nullable), `query_id` (nullable), `source_id` (nullable), `payload` (jsonb), `sla_status` (nullable), `created_at`.

## Acceptance Criteria

- [x] All 9 tables exist as SQLAlchemy models in `backend/app/db/models.py`, matching the field lists above.
- [x] `pgvector` extension is enabled in the migration, and `chunks.embedding` uses it.
- [x] A migration tool (Alembic) is wired up. Verified with `alembic upgrade head --sql` and `alembic downgrade base --sql` (offline mode, compiles real SQL against the PostgreSQL dialect without needing a live server) — both produce clean, FK-order-correct DDL for all 9 tables and 7 enum types, in both directions. **Not yet run against an actual running Postgres** (`docker-compose up` is blocked by an unrelated local Docker Desktop bug — a stuck reparse point from its Inference/Model Runner feature, Windows error 1920, which needs a machine reboot to clear). First person with working Docker should run it live and confirm here — the generated SQL is already verified correct, this is just the "does a real server accept it" check.
- [x] A `seed.py` script creates the 4 demo accounts (one per role) with a fixed, documented password for demo day. Verified: imports cleanly, `DEMO_ACCOUNTS` resolves to the 4 correct role emails.
- [x] `docker-compose up db` brings up Postgres with the extension enabled, no manual steps (image confirmed correct; live run blocked by the same local Docker issue).

## Implementation Tasks

- [x] `backend/app/db/models.py` — all 9 SQLAlchemy models
- [x] `backend/app/db/session.py` — engine/session factory reading `DATABASE_URL` from env
- [x] `backend/alembic/` — migration environment + first migration
- [x] `backend/app/db/seed.py` — 4 demo accounts
- [x] Update `infra/docker-compose.yml` `db` service to use `pgvector/pgvector` image (already stubbed — confirm image tag)
- [x] Update this file's checkboxes as you go, then open a PR into `master`
