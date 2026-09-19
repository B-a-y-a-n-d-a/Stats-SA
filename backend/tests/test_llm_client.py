"""Unit tests for app/retrieval/llm_client.py.

FakeLLMClient (the LLM_PROVIDER=fake demo-resilience fallback, specs/011) is
pure logic, no DB/network needed — it only parses the prompt string
service.py builds. AnthropicLLMClient and GeminiLLMClient both need a real
API key and network access to actually call generate(), so — matching the
precedent already set for AnthropicLLMClient — this file doesn't try to
construct or call either; it only tests get_llm_client()'s own dispatch
logic (which provider string maps to which class), mocking the classes
themselves rather than letting either SDK's real constructor run.
"""
import json

import pytest

from app.retrieval import llm_client
from app.retrieval.llm_client import FakeLLMClient

PROMPT = (
    'Question: How did GDP change?\n\n'
    'Source excerpts:\n'
    'chunk_id: abc-123\n'
    'source: GDP Fact Sheet\n'
    'text: """GDP fell 0.2% in the second quarter of 2026.\nManufacturing led the decline."""'
)

# A real Stats SA media release's chunk 1 opens with a postal address, not
# the finding — this is the exact shape that surfaced the letterhead-skip
# fix live-testing specs/011's demo seed data (QLFS Q2 2026).
LETTERHEAD_PROMPT = (
    'Question: What was the unemployment rate?\n\n'
    'Source excerpts:\n'
    'chunk_id: def-456\n'
    'source: QLFS Media Release\n'
    'text: """Private Bag X44, Pretoria, 0001, South Africa\n'
    'MEDIA RELEASE\n'
    'The official unemployment rate was 33,6% in the second quarter of 2026"""'
)


def test_generate_cites_the_first_excerpt_with_a_verbatim_quote():
    result = json.loads(FakeLLMClient().generate("system", PROMPT))

    assert result["answer"]
    assert len(result["citations"]) == 1
    citation = result["citations"][0]
    assert citation["chunk_id"] == "abc-123"
    # The quote must be verbatim from the excerpt's own text, so the real
    # citation-enforcement pipeline (app/retrieval/citation.py) accepts it.
    assert citation["quote"] in PROMPT


def test_generate_skips_a_short_letterhead_line_for_the_real_finding():
    result = json.loads(FakeLLMClient().generate("system", LETTERHEAD_PROMPT))

    citation = result["citations"][0]
    assert "unemployment rate" in citation["quote"]
    assert "Private Bag" not in citation["quote"]
    assert citation["quote"] in LETTERHEAD_PROMPT


def test_generate_with_no_excerpts_returns_no_answer():
    result = json.loads(FakeLLMClient().generate("system", "Question: anything\n\nSource excerpts:\n"))

    assert result["answer"] is None
    assert result["citations"] == []


@pytest.mark.parametrize(
    "provider,class_name",
    [("anthropic", "AnthropicLLMClient"), ("gemini", "GeminiLLMClient"), ("fake", "FakeLLMClient")],
)
def test_get_llm_client_dispatches_by_provider(monkeypatch, provider, class_name):
    sentinel = object()
    monkeypatch.setattr(llm_client.settings, "llm_provider", provider)
    monkeypatch.setattr(llm_client, class_name, lambda: sentinel)

    assert llm_client.get_llm_client() is sentinel


def test_get_llm_client_raises_for_unsupported_provider(monkeypatch):
    monkeypatch.setattr(llm_client.settings, "llm_provider", "made-up-provider")

    with pytest.raises(ValueError, match="made-up-provider"):
        llm_client.get_llm_client()
