# Implements specs/003-retrieval-confidence-gate/spec.md.
#
# Citation enforcement is structural, not semantic: a citation is only valid
# if its chunk_id is one of the chunks actually retrieved for this query AND
# its quote is an exact (case-insensitive) substring of that chunk's real
# text. Anything else is dropped rather than shown — docs/02-architecture.md
# Section 1.1 ("every citation must resolve to a real chunk_id ... or the
# claim is dropped and marked unsourced").
import json
import re

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_llm_json(raw: str) -> dict:
    cleaned = _JSON_FENCE.sub("", raw or "").strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return {"answer": None, "citations": []}
    if not isinstance(parsed, dict):
        return {"answer": None, "citations": []}
    return {"answer": parsed.get("answer"), "citations": parsed.get("citations") or []}


def enforce_citations(citations: list[dict], results: list[dict]) -> list[dict]:
    by_id = {str(r["chunk_id"]): r for r in results}
    valid = []
    for c in citations:
        if not isinstance(c, dict):
            continue
        chunk_id = str(c.get("chunk_id", ""))
        quote = (c.get("quote") or "").strip()
        chunk = by_id.get(chunk_id)
        if not chunk or not quote:
            continue
        if quote.lower() not in chunk["text"].lower():
            continue
        valid.append(
            {
                "chunk_id": chunk_id,
                "source_id": str(chunk["source_id"]),
                "title": chunk["title"],
                "url": chunk["url"],
                "quote": quote,
            }
        )
    return valid
