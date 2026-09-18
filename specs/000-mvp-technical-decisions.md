# 000 - MVP Technical Decisions (ADR)

Status: Accepted for hackathon build. Reference: [docs/05-mvp-scope-and-roadmap.md](../docs/05-mvp-scope-and-roadmap.md), [docs/02-architecture.md](../docs/02-architecture.md).

The comprehensive docs describe the full target architecture (hybrid Qdrant + OpenSearch retrieval, Keycloak identity, self-hosted vLLM). Standing all of that up inside a hackathon build window is not realistic and is the single biggest risk to the "Technical Feasibility and Functionality" judging criterion (20%, see [docs/04-judging-criteria-alignment.md](../docs/04-judging-criteria-alignment.md)). This ADR fixes a simplified MVP stack. Anything simplified here is already flagged in the docs as a roadmap item, not a new gap.

## Decisions

| Area | Full target (docs) | MVP decision | Why |
|---|---|---|---|
| Vector + keyword search | Qdrant (dense) + OpenSearch (BM25), hybrid fusion | Single PostgreSQL database with the `pgvector` extension for embeddings; keyword fallback via Postgres full-text search | One service to run and back up during the hackathon. Swappable later without changing the API contract. |
| LLM inference | Self-hosted vLLM serving an open-weight model | A pluggable `LLMClient` interface, defaulting to a hosted API for the demo | Removes GPU/ops risk from demo day. Self-hosting stays the documented Pilot/Rollout target for digital sovereignty ([docs/02-architecture.md](../docs/02-architecture.md) Section 5). |
| Identity / RBAC | Keycloak | Lightweight JWT auth with 4 pre-seeded demo accounts (Public, Media, Communications Official, Curator-Admin) | This is not a downgrade of scope — it is the exact mitigation the Risk Register already specifies for RBAC misconfiguration ([docs/05-mvp-scope-and-roadmap.md](../docs/05-mvp-scope-and-roadmap.md) Section 3). |
| Embeddings | Unspecified model choice | `sentence-transformers/all-MiniLM-L6-v2` (CPU-friendly, small) | Fast local ingestion without a GPU. |
| Deployment | Kubernetes | `docker-compose` (postgres, backend, frontend) | Matches a hackathon laptop/demo-box environment. Containers are unchanged, so the path to Kubernetes later is just orchestration, not a rewrite. |

## Non-negotiable, unchanged from the docs

- Every answer traces to an Approved Sources Registry record (no open-web retrieval).
- Media queries never auto-send; they always route to the Review Console.
- Every AI-generated claim carries a citation or is dropped.
- All four roles are enforced server-side, not just hidden in the UI.

## Consequence

Any teammate proposing a stack change opens a PR against this file first, so the whole team sees the change before it lands in a feature branch.
