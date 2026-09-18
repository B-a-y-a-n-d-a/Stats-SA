# Implements specs/005-media-query-draft/spec.md — branch feature/005-media-query-draft.
#
# Shared by the media path (specs/005) and 004's low-confidence branch: both
# produce the same {headline, key_figures, citations, suggested_tone} structure
# so the Review Console (specs/006) only ever renders one draft shape.
import re

# Whatever the retrieval layer returned, a draft never invents a figure: key
# figures are lifted verbatim out of the citation quotes that survived 003's
# structural citation enforcement.
_FIGURE = re.compile(r"[^.;\n]*?\d[\d ,.]*\s*(?:%|percent|million|billion|thousand)[^.;\n]*", re.IGNORECASE)

GAP_TONE = "cautious — lead with the information gap, do not fill it"
UNVERIFIED_TONE = "cautious — source coverage is thin, verify before release"
FACTUAL_TONE = "factual and neutral, cite the source for every figure"


def _headline(query_text: str) -> str:
    condensed = " ".join(query_text.split())
    return condensed if len(condensed) <= 120 else condensed[:117].rstrip() + "..."


def _key_figures(citations: list[dict]) -> list[dict]:
    figures = []
    seen = set()
    for citation in citations:
        for match in _FIGURE.findall(citation.get("quote", "")):
            figure = " ".join(match.split())
            if figure and figure.lower() not in seen:
                seen.add(figure.lower())
                figures.append({"figure": figure, "chunk_id": citation["chunk_id"], "source": citation.get("title")})
    return figures


def _gap_body(query_text: str) -> str:
    return (
        "The approved source registry does not currently contain enough material to answer "
        f'"{_headline(query_text)}". Do not draft a figure from memory — either point the '
        "enquirer at the relevant release once published, or ask a curator-admin to ingest the "
        "source this question depends on."
    )


def build_draft(query_text: str, retrieval_result: dict) -> dict:
    """Turn a 003 retrieval result into the structured draft a reviewer edits.

    `above_threshold` is advisory here: a media draft is produced either way
    (specs/005), and a result with no grounded answer becomes an explicit
    statement of the information gap rather than generated content.
    """
    citations = retrieval_result.get("citations") or []
    answer = retrieval_result.get("answer_text")
    grounded = bool(answer and citations)
    above_threshold = bool(retrieval_result.get("above_threshold"))

    if not grounded:
        tone = GAP_TONE
    elif above_threshold:
        tone = FACTUAL_TONE
    else:
        tone = UNVERIFIED_TONE

    return {
        "headline": _headline(query_text),
        "body": answer if grounded else _gap_body(query_text),
        "key_figures": _key_figures(citations) if grounded else [],
        "citations": citations,
        "suggested_tone": tone,
        "information_gap": not grounded,
        "confidence_score": retrieval_result.get("confidence_score", 0.0),
    }
