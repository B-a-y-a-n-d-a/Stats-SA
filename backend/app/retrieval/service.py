# Implements specs/003-retrieval-confidence-gate/spec.md.
#
# Shared by both the public path (specs/004) and media path (specs/005) — this
# module does not decide auto-answer vs. escalate, it only ever returns a
# grounded result or an explicit "not enough evidence" result. The caller
# decides what to do with `above_threshold`.
from sqlalchemy.orm import Session

from app.retrieval.citation import enforce_citations, parse_llm_json
from app.retrieval.confidence import clears_threshold, compute_confidence
from app.retrieval.llm_client import LLMClient, get_llm_client
from app.retrieval.search import search_chunks

SYSTEM_PROMPT = (
    "You are a Stats SA information assistant. Answer ONLY using the source "
    "excerpts provided below. Every factual claim must be backed by a citation "
    "to one of the given chunk_ids, and each citation's quote must be an exact "
    "short excerpt copied verbatim from that chunk's text. If the excerpts do "
    "not contain enough information to answer, set \"answer\" to null and "
    "return an empty citations list rather than guessing. Respond with ONLY a "
    'JSON object of the form: {"answer": "..." or null, "citations": '
    '[{"chunk_id": "...", "quote": "..."}]}. No other text.'
)


def _build_user_prompt(query_text: str, results: list[dict]) -> str:
    excerpts = "\n\n".join(
        f'chunk_id: {r["chunk_id"]}\nsource: {r["title"]}\ntext: """{r["text"]}"""' for r in results
    )
    return f"Question: {query_text}\n\nSource excerpts:\n{excerpts}"


def _empty_result(confidence: float = 0.0) -> dict:
    return {"answer_text": None, "citations": [], "confidence_score": confidence, "above_threshold": False}


def answer_query(db: Session, query_text: str, llm_client: LLMClient | None = None, top_k: int = 5) -> dict:
    results = search_chunks(db, query_text, top_k=top_k)
    if not results:
        return _empty_result()

    confidence = compute_confidence(results)
    above = clears_threshold(confidence)

    llm_client = llm_client or get_llm_client()
    raw = llm_client.generate(SYSTEM_PROMPT, _build_user_prompt(query_text, results))
    parsed = parse_llm_json(raw)
    valid_citations = enforce_citations(parsed["citations"], results)

    if not parsed["answer"] or not valid_citations:
        return _empty_result(confidence)

    return {
        "answer_text": parsed["answer"],
        "citations": valid_citations,
        "confidence_score": confidence,
        "above_threshold": above,
    }
