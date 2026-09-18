# 003 - Retrieval, Confidence Gate &amp; Citation Enforcement

Branch: `feature/003-retrieval-confidence-gate`
Depends on: 001, 002 (needs schema and at least a few ingested documents to test against)
Blocks: 004, 005, 007 (every query path calls this)
Docs reference: [docs/02-architecture.md](../../docs/02-architecture.md) Section 1.1, [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 4

## Specification

This is the core RAG logic shared by both the public and media paths. It is a service, not an API endpoint — 004 and 005 call it.

1. **Retrieve**: given a query string, run a similarity search over `chunks.embedding` (pgvector) and return top-k candidates with scores.
2. **Confidence gate**: compute a single confidence score for the retrieval (e.g. top-1 cosine similarity, or an average of top-k). Threshold is a config value, default `0.75` ([docs/05-mvp-scope-and-roadmap.md](../../docs/05-mvp-scope-and-roadmap.md)).
3. **Generate**: call the `LLMClient` ([specs/000](../000-mvp-technical-decisions.md)) with only the retrieved chunk text as context — never let the model answer from outside that context.
4. **Citation enforcement**: every sentence in the generated answer that states a fact must carry a `{source_id, chunk_id, title, url}` citation object. If the model produces an unsupported claim (no matching chunk), drop that claim rather than display it unsourced ([docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 4).
5. Return a structured result: `{answer_text, citations: [...], confidence_score, above_threshold: bool}`.

This module does not decide whether to auto-answer or escalate — that branching lives in 004 (public) and 005 (media), which both call this same function.

## Acceptance Criteria

- [ ] Given a query with strong matching content in the registry, returns an answer with confidence >= 0.75 and at least one citation.
- [ ] Given a query with no matching content, returns `above_threshold: false` and no fabricated answer.
- [ ] Every citation in the response resolves to a real `chunk_id` that exists in the database (no invented citations).
- [ ] Unit tests cover: high-confidence case, low-confidence case, zero-match case.

## Implementation Tasks

- [ ] `backend/app/retrieval/search.py` — pgvector similarity search
- [ ] `backend/app/retrieval/confidence.py` — scoring + threshold config
- [ ] `backend/app/retrieval/llm_client.py` — `LLMClient` interface + one hosted-API implementation
- [ ] `backend/app/retrieval/citation.py` — citation-checking/enforcement logic
- [ ] `backend/app/retrieval/service.py` — ties the above into one `answer_query(text)` function
- [ ] `backend/tests/test_retrieval.py`
- [ ] Update this file's checkboxes as you go, then open a PR into `master`
