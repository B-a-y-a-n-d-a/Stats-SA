# Implements specs/007-communication-memory/spec.md's matching algorithm — branch
# feature/007-communication-memory.
#
# Keyword overlap, not embeddings: specs/000/007 explicitly defer semantic/vector
# matching against `communication_memory` to a later phase ("keyword search is
# enough for MVP" — specs/007 spec.md, docs/05-mvp-scope-and-roadmap.md). This is
# the one scoring implementation shared by GET /api/review/queue's reuse_match
# (app/api/review.py) and GET /api/memory/search (app/api/memory.py).
#
# Scoring: score = |tokens(query) & tokens(candidate.query_text)| / |tokens(query)|
# — i.e. what fraction of the NEW query's own words are found in the candidate's
# stored query_text. Deliberately asymmetric: a candidate is not penalized for
# having extra words the new query doesn't mention (a longer, more detailed prior
# question can still be a good match for a short new one).
#
# Both find_best_match and search take a plain Python list of CommunicationMemory
# candidates rather than a Session/query — the caller fetches rows via SQLAlchemy
# (e.g. db.query(CommunicationMemory).all()) and passes them in. That keeps this
# module free of any DB-specific code, so it's trivially unit-testable with plain
# in-memory objects and behaves identically against SQLite (tests) and Postgres
# (real).
import re

from app.db.models import CommunicationMemory

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or "").lower()))


def _score(query_tokens: set[str], candidate_text: str) -> float:
    if not query_tokens:
        return 0.0
    candidate_tokens = _tokenize(candidate_text)
    if not candidate_tokens:
        return 0.0
    overlap = query_tokens & candidate_tokens
    return len(overlap) / len(query_tokens)


def find_best_match(query_text: str, candidates: list) -> tuple | None:
    """Returns (candidate, score) for the single highest-scoring candidate with
    score > 0, or None if no candidate scores above 0 (including an empty
    candidate list)."""
    query_tokens = _tokenize(query_text)
    best = None
    best_score = 0.0
    for candidate in candidates:
        score = _score(query_tokens, candidate.query_text)
        if score > best_score:
            best = candidate
            best_score = score
    if best is None:
        return None
    return best, best_score


def search(query_text: str, candidates: list, top_k: int = 10) -> list:
    """Returns every candidate with score > 0, sorted by score descending,
    capped at top_k."""
    query_tokens = _tokenize(query_text)
    scored = []
    for candidate in candidates:
        score = _score(query_tokens, candidate.query_text)
        if score > 0:
            scored.append((candidate, score))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]


def serialize_match(memory: CommunicationMemory, score: float) -> dict:
    """The one reuse_match shape both GET /api/review/queue (app/api/review.py)
    and GET /api/memory/search (app/api/memory.py) return."""
    return {
        "memory_id": str(memory.memory_id),
        "query_text": memory.query_text,
        "final_answer": memory.final_answer,
        "citations": memory.citations,
        "approved_by": str(memory.approved_by),
        "approved_at": memory.approved_at.isoformat(),
        "score": round(score, 3),
    }
