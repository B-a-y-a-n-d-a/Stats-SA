# 003 - Retrieval, Confidence Gate &amp; Citation Enforcement

Branch: `feature/003-retrieval-confidence-gate`
Depends on: 001, 002 (needs schema and at least a few ingested documents to test against)
Blocks: 004, 005, 007 (every query path calls this)
Docs reference: [docs/02-architecture.md](../../docs/02-architecture.md) Section 1.1, [docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 4

## Specification

This is the core RAG logic shared by both the public and media paths. It is a service, not an API endpoint — 004 and 005 call it.

1. **Retrieve**: given a query string, run a similarity search over `chunks.embedding` (pgvector) and return top-k candidates with scores.
2. **Confidence gate**: compute a single confidence score for the retrieval (top-1 cosine similarity). Threshold is a config value — **0.4, not the docs' original 0.75 guess**. Live-measured against `all-MiniLM-L6-v2` and a real Stats SA document: genuinely relevant queries scored 0.47-0.54, irrelevant ones 0.17-0.18. 0.75 would reject every query, including correct ones — see `app/core/config.py` for the full note. Re-calibrate as the real registry grows past one test document.
3. **Generate**: call the `LLMClient` ([specs/000](../000-mvp-technical-decisions.md)) with only the retrieved chunk text as context — never let the model answer from outside that context.
4. **Citation enforcement**: every sentence in the generated answer that states a fact must carry a `{source_id, chunk_id, title, url}` citation object. If the model produces an unsupported claim (no matching chunk), drop that claim rather than display it unsourced ([docs/01-requirements-traceability.md](../../docs/01-requirements-traceability.md) Mandatory Functional Capability 4).
5. Return a structured result: `{answer_text, citations: [...], confidence_score, above_threshold: bool}`.

This module does not decide whether to auto-answer or escalate — that branching lives in 004 (public) and 005 (media), which both call this same function.

## Acceptance Criteria

- [x] Given a query with strong matching content in the registry, returns an answer with confidence >= threshold (0.4, see above) and at least one citation. Verified live against a real ingested Stats SA document with a fake (deterministic) LLM client — no live LLM API key is available in this build environment, so the confidence-gate and citation-enforcement mechanism is what's tested, not a specific vendor call.
- [x] Given a query with no matching content, returns `above_threshold: false` and no fabricated answer. Verified two ways: (1) a genuinely unrelated query scores well below threshold, (2) an entirely empty registry short-circuits before ever calling the LLM.
- [x] Every citation in the response resolves to a real `chunk_id` that exists in the database (no invented citations). Verified live: a citation naming a chunk_id that was never retrieved is dropped; a citation whose quote doesn't actually appear in its named chunk is also dropped.
- [x] Unit tests cover: high-confidence case, low-confidence case, zero-match case, plus two citation-enforcement failure modes. All 5 pass live against the real Postgres container.

**The real find from live testing: the default confidence threshold was wrong.** 0.75 (this doc's original placeholder) was never checked against the actual embedding model — measuring it found relevant queries score 0.47-0.54 and irrelevant ones 0.17-0.18, so 0.75 would have silently broken the entire public auto-answer path (every query would escalate, none would ever auto-answer). Fixed to 0.4 in `app/core/config.py` and `.env.example`.

**Not tested here (needs a real API key, outside this build environment):** `AnthropicLLMClient` in `llm_client.py` is implemented per specs/000 but not exercised by a live call. Whoever sets `LLM_API_KEY` first should sanity-check it against a real query.

## Implementation Tasks

- [x] `backend/app/retrieval/search.py` — pgvector similarity search
- [x] `backend/app/retrieval/confidence.py` — scoring + threshold config
- [x] `backend/app/retrieval/llm_client.py` — `LLMClient` interface + one hosted-API implementation
- [x] `backend/app/retrieval/citation.py` — citation-checking/enforcement logic
- [x] `backend/app/retrieval/service.py` — ties the above into one `answer_query(text)` function
- [x] `backend/tests/test_retrieval.py`
- [x] Update this file's checkboxes as you go, then open a PR into `master`
